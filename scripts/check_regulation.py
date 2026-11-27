#!/usr/bin/env python3
"""Regulation watcher for the Open Housing Operating Model.

Checks the regulation layer's register against official sources and reports what may need a human look:

  1. Source updated   a watched GOV.UK page has a major update, or legislation.gov.uk has recorded
                      new changes (effects) to a watched Act or SI, since the entry's last_checked date
  2. Date passed      a dated change in the register is now in the past, so its status or summary
                      probably needs updating
  3. Stale            nobody has checked the entry against its source for a while
  4. New publications new items from the Regulator of Social Housing, MHCLG and others on GOV.UK,
                      and new housing-related legislation, published in the last few days

It never edits the register. With a GitHub token it opens one issue per finding (labelled
`regulation-watch`) and one digest issue per run for new publications, and skips anything it has
already raised. Without a token, or with --dry-run, it prints a report instead.

Usage:
  python scripts/check_regulation.py --dry-run
  GITHUB_TOKEN=... GITHUB_REPOSITORY=owner/repo python scripts/check_regulation.py
  python scripts/check_regulation.py --dry-run --fixtures tests/fixtures/regwatch   (offline test)

Sources: GOV.UK Content API and Search API, and the legislation.gov.uk API (Open Government Licence).
"""
import argparse
import calendar
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date, timedelta
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
REG_DIR = ROOT / "layers" / "regulation"
LABEL = "regulation-watch"
UA = "open-housing-operating-model regulation-watch (+https://github.com/RichardSage/open-housing-operating-model)"
ATOM = "{http://www.w3.org/2005/Atom}"
UKM = "{http://www.legislation.gov.uk/namespaces/metadata}"
LEG_TYPES = {"ukpga", "uksi", "asp", "anaw", "asc", "wsi", "nisr", "nia", "ukla"}

TODAY = date.today()


# ---------------------------------------------------------------- fetching

class Fetcher:
    """HTTP GET with a polite delay per host. With fixtures, reads files instead (for offline tests)."""

    def __init__(self, fixtures=None):
        self.fixtures = Path(fixtures) if fixtures else None
        self.last = {}

    def get(self, url):
        if self.fixtures:
            name = re.sub(r"[^A-Za-z0-9]+", "_", url.split("://", 1)[-1]).strip("_")[:180]
            p = self.fixtures / name
            if not p.exists():
                raise FileNotFoundError(f"no fixture {name}")
            return p.read_bytes()
        host = urllib.parse.urlsplit(url).hostname
        wait = 1.0 - (time.time() - self.last.get(host, 0))
        if wait > 0:
            time.sleep(wait)  # legislation.gov.uk fair use: stay well under its rate limit
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
        try:
            for attempt in range(3):
                try:
                    with urllib.request.urlopen(req, timeout=30) as r:
                        return r.read()
                except urllib.error.HTTPError as e:
                    if e.code in (429, 502, 503, 504) and attempt < 2:
                        time.sleep(5 * (attempt + 1))
                        continue
                    raise
        finally:
            self.last[host] = time.time()


def parse_day(v):
    """Any ISO-ish timestamp or YYYY / YYYY-MM / YYYY-MM-DD -> date (start of the period)."""
    m = re.match(r"(\d{4})(?:-(\d{2}))?(?:-(\d{2}))?", str(v or ""))
    if not m:
        return None
    return date(int(m.group(1)), int(m.group(2) or 1), int(m.group(3) or 1))


def end_of(v):
    """YYYY -> 31 Dec, YYYY-MM -> last day of month, YYYY-MM-DD -> that day. So a change is only 'passed' once its whole period is over."""
    m = re.fullmatch(r"(\d{4})(?:-(\d{2}))?(?:-(\d{2}))?", str(v or ""))
    if not m:
        return None
    y = int(m.group(1))
    if m.group(3):
        return date(y, int(m.group(2)), int(m.group(3)))
    if m.group(2):
        mo = int(m.group(2))
        return date(y, mo, calendar.monthrange(y, mo)[1])
    return date(y, 12, 31)


# ---------------------------------------------------------------- source checks

def source_kind(url):
    p = urllib.parse.urlsplit(url or "")
    if p.hostname in ("www.gov.uk", "gov.uk"):
        if p.path.startswith("/government/organisations/"):
            return None  # organisation home pages change for unrelated reasons; watch specific pages instead
        return "govuk"
    if p.hostname in ("www.legislation.gov.uk", "legislation.gov.uk"):
        parts = p.path.strip("/").split("/")
        if len(parts) >= 3 and parts[0] in LEG_TYPES and parts[1].isdigit():
            return "legislation"
    return None


def check_govuk_page(f, url, since):
    path = urllib.parse.urlsplit(url).path
    data = json.loads(f.get("https://www.gov.uk/api/content" + path))
    updated = parse_day(data.get("public_updated_at"))
    if data.get("withdrawn_notice"):
        return {"kind": "withdrawn", "date": updated, "title": data.get("title"), "url": url,
                "note": "This page has been withdrawn on GOV.UK."}
    if not updated or updated <= since:
        return None
    notes = (data.get("details") or {}).get("change_history") or []
    notes = sorted(notes, key=lambda n: n.get("public_timestamp", ""), reverse=True)
    recent = [n.get("note", "").strip() for n in notes if (parse_day(n.get("public_timestamp")) or date.min) > since]
    return {"kind": "updated", "date": updated, "title": data.get("title"), "url": url,
            "notes": [n for n in recent if n][:5]}


IGNORE_EFFECTS = set()  # effect types to skip, from watch.yaml `ignore_effect_types`


def check_legislation(f, url, since):
    """New effects recorded against this item by legislation made since `since`'s year."""
    parts = urllib.parse.urlsplit(url).path.strip("/").split("/")
    ltype, year, num = parts[0], parts[1], parts[2]
    years = f"{since.year}-{TODAY.year}" if since.year < TODAY.year else str(TODAY.year)
    found = {}
    for affecting in ("ukpga", "uksi"):
        feed = (f"https://www.legislation.gov.uk/changes/affected/{ltype}/{year}/{num}"
                f"/affecting/{affecting}/{years}/data.feed?results-count=100")
        root = ET.fromstring(f.get(feed))
        for e in root.iter(f"{ATOM}entry"):
            upd = parse_day((e.findtext(f"{ATOM}updated") or ""))
            eff = e.find(f".//{UKM}Effect")
            if eff is None:
                continue
            mod = parse_day(eff.get("Modified")) or upd
            if mod and mod <= since:
                continue
            if (eff.get("Type") or "").strip().lower() in IGNORE_EFFECTS:
                continue  # such as a local order that applies the Act to one scheme
            key = eff.get("AffectingURI") or eff.get("AffectingTitle") or ""
            title = eff.findtext(f"{UKM}AffectingTitle") or key
            item = found.setdefault(key, {"title": title, "uri": eff.get("AffectingURI"), "effects": 0,
                                          "types": set(), "applied": True})
            item["effects"] += 1
            if eff.get("Type"):
                item["types"].add(eff.get("Type"))
            if str(eff.get("Applied", "")).lower() != "true":
                item["applied"] = False
    if not found:
        return None
    latest = sorted(found.values(), key=lambda x: x["title"])
    return {"kind": "amended", "date": TODAY, "title": None, "url": url,
            "changes_url": f"https://www.legislation.gov.uk/changes/affected/{ltype}/{year}/{num}",
            "affecting": latest}


def govuk_feed(f, feed, since):
    q = {"filter_organisations": feed["organisation"], "order": "-public_timestamp", "count": "50",
         "fields": "title,link,public_timestamp,description,content_store_document_type"}
    data = json.loads(f.get("https://www.gov.uk/api/search.json?" + urllib.parse.urlencode(q)))
    out = []
    for r in data.get("results") or []:
        d = parse_day(r.get("public_timestamp"))
        if not d or d <= since:
            continue
        title = r.get("title") or ""
        text = f"{title} {r.get('description') or ''}".lower()
        if any(re.search(p, title, re.I) for p in feed.get("exclude_titles") or []):
            continue
        if (r.get("content_store_document_type") or "") in (feed.get("exclude_types") or []):
            continue
        kws = feed.get("include_keywords")
        if kws and not any(k.lower() in text for k in kws):
            continue
        link = r.get("link") or ""
        out.append({"title": title, "url": link if link.startswith("http") else "https://www.gov.uk" + link,
                    "date": d, "type": (r.get("content_store_document_type") or "").replace("_", " ")})
    return out


def legislation_feed(f, titles, since):
    q = " OR ".join(f'"{t}"' if " " in t else t for t in titles)
    out = {}
    for t in ("ukpga", "uksi"):
        url = (f"https://www.legislation.gov.uk/{t}/data.feed?"
               + urllib.parse.urlencode({"title": q, "sort": "published", "start-year": since.year,
                                         "results-count": "50"}))
        root = ET.fromstring(f.get(url))
        for e in root.iter(f"{ATOM}entry"):
            d = parse_day(e.findtext(f"{ATOM}published") or e.findtext(f"{ATOM}updated"))
            if not d or d <= since:
                continue
            link = next((l.get("href") for l in e.findall(f"{ATOM}link") if l.get("rel") in (None, "alternate")
                         and "data." not in (l.get("href") or "")), None) or e.findtext(f"{ATOM}id")
            out[link] = {"title": (e.findtext(f"{ATOM}title") or "").strip(), "url": link, "date": d,
                         "type": "Act" if t == "ukpga" else "Statutory instrument"}
    return list(out.values())


# ---------------------------------------------------------------- findings

def key_of(*parts):
    return hashlib.sha1("|".join(str(p) for p in parts).encode()).hexdigest()[:12]


HOWTO = """**What to do**
1. Read the source and decide whether the register needs to change.
2. If it does, edit `layers/regulation/register.yaml` (and `links.csv` if the change affects different activities): `status`, `summary`, `changes` and `last_checked`.
3. If it doesn't, still update `last_checked` for this entry so the watcher knows it has been looked at.
4. Run `python scripts/build.py --check`, open a pull request, and mention this issue so it closes when merged.

_Opened automatically by the regulation watcher. It is a prompt to check, not a finding of fact. Not legal advice._"""


def obligation_findings(f, reg, cfg, errors):
    findings = []
    stale_after = int(cfg.get("stale_after_days", 180))
    stale = []
    for o in reg:
        oid, name = o["id"], o.get("name", o["id"])
        checked = parse_day(o.get("last_checked")) or date(2000, 1, 1)
        head = f"**{name}** (`{oid}`), last checked {checked.isoformat()}"

        # 1. watched sources
        watch = o.get("watch") or ([o["url"]] if o.get("url") else [])
        for url in watch:
            kind = source_kind(url)
            if not kind:
                continue
            try:
                hit = check_govuk_page(f, url, checked) if kind == "govuk" else check_legislation(f, url, checked)
            except Exception as e:  # noqa: BLE001 - report and carry on
                errors.append(f"`{oid}`: {url} ({type(e).__name__}: {str(e)[:120]})")
                continue
            if not hit:
                continue
            if hit["kind"] == "amended":
                lines = []
                for a in hit["affecting"][:15]:
                    status = "" if a["applied"] else " (not yet applied to the text on legislation.gov.uk)"
                    types = ", ".join(sorted(a["types"]))[:80]
                    lines.append(f"- [{a['title']}]({a['uri'] or hit['changes_url']}): {a['effects']} change(s)"
                                 + (f": {types}" if types else "") + status)
                more = len(hit["affecting"]) - 15
                if more > 0:
                    lines.append(f"- and {more} more")
                ids = ",".join(sorted(a["uri"] or a["title"] for a in hit["affecting"]))
                findings.append({
                    "key": key_of("amended", oid, url, ids),
                    "title": f"Regulation watch: new changes recorded to {name}",
                    "body": f"{head}.\n\nlegislation.gov.uk has recorded changes to [{url}]({url}) made by legislation "
                            f"since then:\n\n" + "\n".join(lines)
                            + f"\n\nAll changes: {hit['changes_url']}\n\n{HOWTO}"})
            else:
                what = "was withdrawn" if hit["kind"] == "withdrawn" else f"was updated on {hit['date'].isoformat()}"
                notes = "".join(f"\n> {n}" for n in hit.get("notes") or [])
                findings.append({
                    "key": key_of(hit["kind"], oid, url, hit["date"]),
                    "title": f"Regulation watch: source for {name} {what}",
                    "body": f"{head}.\n\nThe GOV.UK page [{hit['title'] or url}]({url}) {what}."
                            + (f"\n\nChange note{'s' if len(hit['notes']) > 1 else ''} from GOV.UK:{notes}" if notes else "")
                            + f"\n\n{HOWTO}"})

        # 2. dated changes that have passed
        for c in o.get("changes") or []:
            end = end_of(c.get("date"))
            if end and end < TODAY:
                findings.append({
                    "key": key_of("passed", oid, c.get("date"), c.get("summary")),
                    "title": f"Regulation watch: {name}: the change due {c.get('date')} has passed",
                    "body": f"{head}.\n\nThe register lists this change as due **{c.get('date')}** "
                            f"({c.get('certainty')}):\n\n> {c.get('summary')}\n\nThat date has passed. Check whether it "
                            f"happened as planned. If it did, remove it from `changes` and update `status`, "
                            f"`summary` or `in_force_from`. If it slipped, update the date and certainty.\n\n{HOWTO}"})

        # 3. stale entries (collected, then raised as one checklist so they don't arrive as dozens of issues)
        if (TODAY - checked).days > stale_after:
            stale.append((checked, o))
    if stale:
        stale.sort(key=lambda x: (x[0], x[1]["id"]))
        lines = [f"- [ ] **{o.get('name', o['id'])}** (`{o['id']}`), last checked {d.isoformat()}: "
                 + (o.get("url") or "no source link yet, please add one") for d, o in stale]
        findings.append({
            "key": key_of("stale", *[f"{o['id']}@{d}" for d, o in stale]),
            "title": f"Regulation watch: {len(stale)} entr{'y' if len(stale) == 1 else 'ies'} due a re-check",
            "body": f"These entries haven't been checked against their sources for more than {stale_after} days. "
                    "Re-check each one, update anything that has changed, and set `last_checked` to today. "
                    "Several entries can go in one pull request.\n\n" + "\n".join(lines) + f"\n\n{HOWTO}"})
    return findings


def publication_digest(f, cfg, errors):
    since = TODAY - timedelta(days=int(cfg.get("window_days", 9)))
    items = []
    for feed in cfg.get("govuk_feeds") or []:
        try:
            for it in govuk_feed(f, feed, since):
                it["source"] = feed.get("name", feed["organisation"])
                items.append(it)
        except Exception as e:  # noqa: BLE001
            errors.append(f"GOV.UK feed `{feed['organisation']}` ({type(e).__name__}: {str(e)[:120]})")
    if cfg.get("legislation_titles"):
        try:
            for it in legislation_feed(f, cfg["legislation_titles"], since):
                it["source"] = "legislation.gov.uk"
                items.append(it)
        except Exception as e:  # noqa: BLE001
            errors.append(f"legislation.gov.uk new legislation feed ({type(e).__name__}: {str(e)[:120]})")
    seen, unique = set(), []
    for it in sorted(items, key=lambda x: (x["source"], x["date"]), reverse=False):
        if it["url"] not in seen:
            seen.add(it["url"])
            unique.append(it)
    return unique


def digest_body(items, already):
    rows, by_source = [], {}
    for it in items:
        by_source.setdefault(it["source"], []).append(it)
    for src, its in by_source.items():
        rows.append(f"\n### {src}\n")
        for it in sorted(its, key=lambda x: x["date"], reverse=True):
            mark = f"<!-- item:{key_of(it['url'])} -->"
            if mark in already:
                continue
            t = f" ({it['type']})" if it.get("type") else ""
            rows.append(f"- [ ] {it['date'].isoformat()}: [{it['title']}]({it['url']}){t} {mark}")
    if not any(r.startswith("- ") for r in rows):
        return None
    return ("New publications that might affect the regulation register. Most won't, so tick off the ones "
            "you've looked at and close the issue when you're done. If one does affect the register, "
            "update `layers/regulation/register.yaml` in a pull request that mentions this issue.\n"
            + "\n".join(rows)
            + "\n\n_Opened automatically by the regulation watcher. Filters are in `layers/regulation/watch.yaml`._")


# ---------------------------------------------------------------- GitHub

class GitHub:
    def __init__(self, repo, token):
        self.repo, self.token = repo, token

    def call(self, method, path, body=None):
        req = urllib.request.Request(
            f"https://api.github.com/repos/{self.repo}{path}", method=method,
            data=json.dumps(body).encode() if body is not None else None,
            headers={"Authorization": f"Bearer {self.token}", "Accept": "application/vnd.github+json",
                     "X-GitHub-Api-Version": "2022-11-28", "User-Agent": UA})
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read()
            return json.loads(raw) if raw else None

    def ensure_label(self):
        try:
            self.call("GET", f"/labels/{LABEL}")
        except urllib.error.HTTPError as e:
            if e.code != 404:
                raise
            self.call("POST", "/labels", {"name": LABEL, "color": "5319e7",
                                          "description": "Raised by the weekly regulation watcher"})

    def existing_text(self):
        """Bodies of all watcher issues, open and closed, so nothing is raised twice."""
        text, page = [], 1
        while page <= 20:
            batch = self.call("GET", f"/issues?labels={LABEL}&state=all&per_page=100&page={page}")
            if not batch:
                break
            text += [i.get("body") or "" for i in batch]
            page += 1
        return "\n".join(text)

    def open_issue(self, title, body):
        return self.call("POST", "/issues", {"title": title[:250], "body": body, "labels": [LABEL]})


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dry-run", action="store_true", help="print what would be raised; don't open issues")
    ap.add_argument("--fixtures", help="read sources from this folder instead of the internet (testing)")
    ap.add_argument("--today", help="pretend today is this date (YYYY-MM-DD), for testing")
    args = ap.parse_args()

    global TODAY
    if args.today:
        TODAY = date.fromisoformat(args.today)

    reg = (yaml.safe_load((REG_DIR / "register.yaml").read_text(encoding="utf-8")) or {}).get("obligations") or []
    cfg = yaml.safe_load((REG_DIR / "watch.yaml").read_text(encoding="utf-8")) or {}
    IGNORE_EFFECTS.update(t.strip().lower() for t in cfg.get("ignore_effect_types") or [])
    f = Fetcher(args.fixtures)
    errors = []

    findings = obligation_findings(f, reg, cfg, errors)
    items = publication_digest(f, cfg, errors)

    token, repo = os.environ.get("GITHUB_TOKEN"), os.environ.get("GITHUB_REPOSITORY")
    gh = GitHub(repo, token) if token and repo and not args.dry_run else None
    already = ""
    if gh:
        gh.ensure_label()
        already = gh.existing_text()

    raised, skipped = [], 0
    for fd in findings:
        mark = f"<!-- regwatch:{fd['key']} -->"
        if mark in already:
            skipped += 1
            continue
        body = fd["body"] + f"\n\n{mark}"
        if gh:
            issue = gh.open_issue(fd["title"], body)
            raised.append(f"[#{issue['number']}]({issue['html_url']}) {fd['title']}")
        else:
            raised.append(fd["title"])
            print(f"\n=== {fd['title']}\n{body}\n")

    digest = digest_body(items, already) if items else None
    if digest:
        title = f"Regulation watch: new publications to look at, week of {TODAY.isoformat()}"
        if gh:
            issue = gh.open_issue(title, digest)
            raised.append(f"[#{issue['number']}]({issue['html_url']}) {title}")
        else:
            raised.append(title)
            print(f"\n=== {title}\n{digest}\n")

    if errors:
        title = f"Regulation watch: {len(errors)} source(s) couldn't be checked"
        body = ("The watcher couldn't reach or read these sources. A link may have moved, or the site was down. "
                "If it happens again next week, update the link in `layers/regulation/register.yaml` "
                "(`url` or `watch`) or `watch.yaml`.\n\n" + "\n".join(f"- {e}" for e in errors))
        mark = f"<!-- regwatch:{key_of('errors', *sorted(errors))} -->"
        if gh and mark not in already:
            issue = gh.open_issue(title, body + f"\n\n{mark}")
            raised.append(f"[#{issue['number']}]({issue['html_url']}) {title}")
        elif not gh:
            print(f"\n=== {title}\n{body}\n")

    watched = sum(1 for o in reg for u in (o.get("watch") or ([o["url"]] if o.get("url") else [])) if source_kind(u))
    manual = [o["id"] for o in reg if not any(source_kind(u) for u in (o.get("watch") or ([o["url"]] if o.get("url") else [])))]
    summary = [f"## Regulation watch, {TODAY.isoformat()}", "",
               f"- {len(reg)} obligations; {watched} sources checked automatically",
               f"- {len(findings)} finding(s), of which {skipped} were already raised",
               f"- {len(items)} new publication(s) in the last {cfg.get('window_days', 9)} days",
               f"- {len(errors)} source(s) couldn't be checked", "",
               "**Raised this run**" if raised else "Nothing new to raise.", ""]
    summary += [f"- {r}" for r in raised]
    summary += ["", f"Checked by hand only (no GOV.UK or legislation.gov.uk link): {', '.join(manual) or 'none'}"]
    text = "\n".join(summary)
    print(text)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as s:
            s.write(text + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
