#!/usr/bin/env python3
"""Download the Regulator of Social Housing's Tenant Satisfaction Measures data and convert it to tidy CSVs.

What it does
  1. Finds each year's "Tenant Satisfaction Measures 20YY/YY" statistics page on GOV.UK using the Content API
     (through the TSM collection and each year's usual address), and picks its "Full Dataset" attachments
     (Excel, or a zip of Excel/CSV files).
  2. Reads every sheet, finds the headline result column for each of the 22 measures (TP01-TP12, CH01-CH02,
     NM01, RP01-RP02, BS01-BS05) and skips the supporting columns (respondent counts, results by survey
     method, numerators and denominators).
  3. Writes, per year:
       data/tsm/<year>.csv            the results: one row per landlord, tenure and measure (and part, such as
                                      stage one complaints), with the value as published and its unit
       data/tsm/<year>-landlords.csv  landlord type, size band, region, supported housing, publication link,
                                      repair target timescales and any notes from the regulator
       data/tsm/<year>-surveys.csv    how each landlord ran its tenant survey, per tenure
  4. Writes data/tsm/sources.json (where each file came from, with a checksum) and data/tsm/STRUCTURE.md
     (each sheet's headers and a few sample rows), so a person can check the conversion and improve it
     if the regulator changes its layout.

It doesn't change the model or the site. A GitHub Action runs it and opens a pull request for review.

Usage
  python scripts/fetch_tsm.py                 download and convert
  python scripts/fetch_tsm.py --fixtures DIR  read files from DIR instead of the internet (testing)
  python scripts/fetch_tsm.py --file X.xlsx   convert a full dataset you've downloaded yourself

Data: Regulator of Social Housing, Tenant Satisfaction Measures, under the Open Government Licence v3.0.
"""
import argparse
import csv
import hashlib
import io
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "tsm"
COLLECTION = "/government/collections/transparency-influence-and-accountability-including-tenant-satisfaction-measures"
STATS_PAGE = "/government/statistics/tenant-satisfaction-measures-"
UA = "open-housing-operating-model tsm-fetch (+https://github.com/RichardSage/open-housing-operating-model)"
CODE_RE = re.compile(r"\b(TP(?:0[1-9]|1[0-2])|CH0[12]|NM01|RP0[12]|BS0[1-5])\b", re.I)
ID_HINTS = [("provider_code", re.compile(r"(registration|provider code|rp code|org(anisation)? code|landlord code|\bcode\b|\bid\b|lad|ons)", re.I)),
            ("provider_name", re.compile(r"(provider|landlord|organisation|organization|name)", re.I))]


class Fetcher:
    def __init__(self, fixtures=None):
        self.fixtures = Path(fixtures) if fixtures else None
        self.local = {}

    def get(self, url):
        if url in self.local:
            return self.local[url]
        if self.fixtures:
            p = self.fixtures / re.sub(r"[^A-Za-z0-9]+", "_", url.split("://", 1)[-1]).strip("_")[:180]
            if not p.exists():
                raise FileNotFoundError(f"no fixture for {url}")
            return p.read_bytes()
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        for attempt in range(3):
            try:
                with urllib.request.urlopen(req, timeout=60) as r:
                    return r.read()
            except urllib.error.HTTPError as e:
                if e.code in (404, 410) or attempt == 2:
                    raise  # no such page: don't retry
                time.sleep(5 * (attempt + 1))
            except Exception:  # noqa: BLE001
                if attempt == 2:
                    raise
                time.sleep(5 * (attempt + 1))


def year_of(text):
    """'Tenant Satisfaction Measures 2025/26' or '...-202526' or '2024-25' -> '2025-26'."""
    m = re.search(r"(20\d\d)\s*(?:to|-|/|_)?\s*(?:20)?(\d\d)(?!\d)", text or "")
    return f"{m.group(1)}-{m.group(2)}" if m and int(m.group(2)) == (int(m.group(1)) + 1) % 100 else None


def year_in(name, blob):
    """The reporting year stated inside a dataset ('1 April 2025 to 31 March 2026' -> '2025-26')."""
    try:
        for _, rows in tables_from(name, blob):
            for r in rows[:30]:
                m = re.search(r"1 April (20\d\d) to 31 March 20(\d\d)", " ".join(norm(c) for c in r))
                if m:
                    return f"{m.group(1)}-{m.group(2)}"
    except Exception:  # noqa: BLE001
        pass
    return year_of(name)


def find_editions(f):
    """Each yearly 'Tenant Satisfaction Measures 20YY/YY' page on GOV.UK with a full dataset attached.

    Pages are found two ways, so a change to one doesn't stop the fetch: the documents in the TSM collection,
    and the usual address of each year's statistics page (/government/statistics/tenant-satisfaction-measures-202526).
    """
    paths = []
    try:
        coll = json.loads(f.get("https://www.gov.uk/api/content" + COLLECTION))
        for d in (coll.get("links") or {}).get("documents", []):
            p = d.get("base_path") or urllib.parse.urlsplit(d.get("web_url", "")).path
            if p:
                paths.append((p, d.get("title", "")))
    except Exception as e:  # noqa: BLE001
        print(f"! couldn't read the collection {COLLECTION}: {e}")
    for y in range(2023, time.gmtime().tm_year + 1):  # first TSM year was 2023/24
        paths.append((f"{STATS_PAGE}{y}{(y + 1) % 100:02d}", f"{y}/{(y + 1) % 100:02d}"))
    out, seen = [], set()
    for path, title in paths:
        if path in seen:
            continue
        seen.add(path)
        try:
            doc = json.loads(f.get("https://www.gov.uk/api/content" + path))
        except Exception:  # noqa: BLE001  (a year that isn't published yet)
            continue
        atts = [a for a in (doc.get("details") or {}).get("attachments", [])
                if re.search(r"full[\s_-]*data", a.get("title", "") + " " + a.get("url", ""), re.I)
                and re.search(r"\.(xlsx|zip|csv|ods)$", a.get("url", ""), re.I)]
        readable = [a for a in atts if not a["url"].lower().endswith(".ods")]
        atts = readable or atts  # the same data is often published as Excel and OpenDocument: take Excel
        if not atts:
            continue
        yr = year_of(doc.get("title", "")) or year_of(title) or year_of(path)  # None: read it from the file
        if any(e["page"] == "https://www.gov.uk" + path for e in out):
            continue
        out.append({"year": yr, "title": doc.get("title"), "page": "https://www.gov.uk" + path,
                    "updated": doc.get("public_updated_at"), "files": [{"title": a.get("title"), "url": a["url"]} for a in atts]})
    return out


def tables_from(name, blob):
    """Yield (label, rows) for every sheet or CSV in a file, where rows is a list of lists of cell values."""
    low = name.lower()
    if low.endswith(".zip"):
        with zipfile.ZipFile(io.BytesIO(blob)) as z:
            for inner in z.namelist():
                if re.search(r"\.(xlsx|csv)$", inner, re.I) and not inner.startswith("__MACOSX"):
                    yield from tables_from(inner, z.read(inner))
    elif low.endswith(".xlsx"):
        wb = openpyxl.load_workbook(io.BytesIO(blob), read_only=True, data_only=True)
        for ws in wb.worksheets:
            yield f"{Path(name).name} › {ws.title}", [list(r) for r in ws.iter_rows(values_only=True)]
    elif low.endswith(".csv"):
        text = blob.decode("utf-8-sig", errors="replace")
        yield Path(name).name, [r for r in csv.reader(io.StringIO(text))]


def norm(v):
    return "" if v is None else str(v).strip()


SKIP_ID = re.compile(r"(tsm|measure|type|size|units|homes|region|method|stock|tenure|date|year|value|result|percentage)", re.I)


def id_columns(header):
    found = {}
    for j, h in enumerate(header):
        hs = norm(h)
        if not hs or CODE_RE.search(hs) or SKIP_ID.search(hs):
            continue
        for key, rx in ID_HINTS:
            if key not in found and rx.search(hs):
                found[key] = j
                break
    return found


def number(v):
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace(",", "").rstrip("%").strip()
    try:
        return float(s)
    except ValueError:
        return None


RATE_MEASURES = {"CH01", "NM01"}  # rates per 1,000 homes; every other measure is a percentage
PART_NAMES = {("CH01", "1"): "Stage one", ("CH01", "2"): "Stage two", ("CH02", "1"): "Stage one", ("CH02", "2"): "Stage two",
              ("RP02", "1"): "Non-emergency repairs", ("RP02", "2"): "Emergency repairs",
              ("NM01", "1"): "All ASB cases", ("NM01", "2"): "Cases involving hate incidents"}
MARKERS = {"[X]", "[Z]", "[U]", "[S]", "[E]"}
# A headline result column: "Proportion of ... (TP01)" or "... per 1,000 homes (CH01 1)", optionally prefixed by a tenure
RESULT_RE = re.compile(r"\((TP(?:0[1-9]|1[0-2])|CH0[12]|NM01|RP0[12]|BS0[1-5])(?:\s+(\d))?\)")
NOT_RESULT = re.compile(r"(survey method|unweighted|state that they|numerator|denominator|did you|what is your|number of respondents)", re.I)
TENURE_PREFIX = re.compile(r"^\s*(LCRA|LCHO|Combined)\s*-\s*", re.I)
LANDLORD_FIELDS = [  # output column, header pattern (first matching column in any sheet wins)
    ("provider_type", r"^landlord type"), ("group_size", r"group size"), ("region", r"predominant region"),
    ("supported_housing_over_30pc", r"above 30% supported"), ("publication_url", r"publication url"),
    ("rsh_notes", r"additional notes from rsh"),
    ("nonemergency_target_max", r"target timescale for non-emergency repairs used"),
    ("nonemergency_more_than_one_target", r"more than one target timescale for non-emergency repairs\?"),
    ("emergency_target_max", r"target timescale for emergency repairs used"),
    ("emergency_more_than_one_target", r"more than one target timescale for emergency"),
]
SURVEY_FIELDS = [
    ("population", r"relevant\s*tenant population"), ("required_sample", r"required minimum sample"),
    ("sample_achieved", r"total sample size achieved"), ("margin_of_error_pc", r"margin of error"),
    ("sample_or_census", r"^sample or census"), ("responses_telephone", r"by method - telephone"),
    ("responses_internet", r"by method - internet"), ("responses_face_to_face", r"by method - facetoface"),
    ("responses_postal", r"by method - postal"), ("responses_sms", r"by method - sms"), ("responses_other", r"by method - other"),
    ("external_contractor", r"external contractors been used"),
]


def tenure_of(label):
    m = re.search(r"(LCRA|LCHO|Combined)", label, re.I)
    return {"lcra": "LCRA", "lcho": "LCHO", "combined": "Combined"}[m.group(1).lower()] if m else "All"


def find_header(rows):
    """The landlord header row: a row starting 'Landlord name', or failing that one with 3+ measure codes."""
    for i, r in enumerate(rows[:40]):
        if r and norm(r[0]).lower() in ("landlord name", "provider name", "organisation name"):
            return i, "wide"
    for i, r in enumerate(rows[:40]):
        cells = [norm(c) for c in r]
        if any(len(c) > 80 for c in cells if c) and not any(CODE_RE.search(c) for c in cells):
            continue  # a paragraph of notes, not a header
        if sum(1 for c in cells if CODE_RE.search(c)) >= 3:
            return i, "wide"
        low = [c.lower() for c in cells]
        if any(re.search(r"\b(tsm|measure)\b", c) for c in low) and any(re.search(r"\b(value|result|score|percentage|figure)\b", c) for c in low):
            return i, "long"
    return None, None


def result_columns(header, sheet_tenure):
    """[(index, measure, part, tenure)] for the headline result columns only."""
    out = []
    for j, h in enumerate(header):
        m = RESULT_RE.search(h)
        if not m or NOT_RESULT.search(h):
            continue
        body = TENURE_PREFIX.sub("", h)
        if not (body.lower().startswith("proportion") or "per 1,000 homes" in body.lower()):
            continue
        t = TENURE_PREFIX.match(h)
        tenure = {"lcra": "LCRA", "lcho": "LCHO", "combined": "Combined"}[t.group(1).lower()] if t else sheet_tenure
        out.append((j, m.group(1).upper(), m.group(2) or "", tenure))
    return out


def convert(label, rows, year, landlords, surveys):
    """Return (result records, note). Also fills the landlords and surveys dicts."""
    hi, kind = find_header(rows)
    if hi is None:
        return [], "no landlord or measure columns found"
    header = [norm(c) for c in rows[hi]]
    ids = id_columns(header)
    sheet_tenure = tenure_of(label)
    recs = []

    def ident(r):
        code = norm(r[ids["provider_code"]]) if "provider_code" in ids and ids["provider_code"] < len(r) else ""
        name = norm(r[ids["provider_name"]]) if "provider_name" in ids and ids["provider_name"] < len(r) else ""
        return code, name

    if kind == "wide":
        cols = result_columns(header, sheet_tenure)
        lf = {k: next((j for j, h in enumerate(header) if re.search(rx, h, re.I)), None) for k, rx in LANDLORD_FIELDS}
        sf = {k: next((j for j, h in enumerate(header) if re.search(rx, h, re.I)), None) for k, rx in SURVEY_FIELDS}
        for r in rows[hi + 1:]:
            code, name = ident(r)
            if not (code or name):
                continue
            cell = lambda j: norm(r[j]) if j is not None and j < len(r) else ""
            ll = landlords.setdefault(code or name, {"provider_code": code, "provider_name": name})
            for k, j in lf.items():
                if cell(j) and not ll.get(k):
                    ll[k] = cell(j)
            if sheet_tenure != "All" and sf.get("sample_achieved") is not None:
                surveys[(code or name, sheet_tenure)] = {"provider_code": code, "tenure": sheet_tenure,
                                                          **{k: cell(j) for k, j in sf.items()}}
            for j, mcode, part, tenure in cols:
                raw = r[j] if j < len(r) else None
                v = number(raw)
                status = norm(raw) if norm(raw) in MARKERS else ""
                if v is None and status in ("", "[U]"):
                    continue  # [U]: nothing to measure, such as no shared owners
                recs.append([year, tenure, code, name, mcode, part, PART_NAMES.get((mcode, part), ""),
                             "per 1,000 homes" if mcode in RATE_MEASURES else "%", "" if v is None else v, status])
        return recs, f"wide: header row {hi + 1}, {len(cols)} result columns, tenure {sheet_tenure}, ids {ids or 'not found'}"
    # Long layout: one row per landlord and measure
    low = [h.lower() for h in header]
    mcol = next(j for j, h in enumerate(low) if re.search(r"\b(tsm|measure)\b", h))
    vcol = next(j for j, h in enumerate(low) if re.search(r"\b(value|result|score|percentage|figure)\b", h))
    tcol = next((j for j, h in enumerate(low) if "tenure" in h), None)
    for r in rows[hi + 1:]:
        if mcol >= len(r) or not CODE_RE.search(norm(r[mcol])):
            continue
        m = RESULT_RE.search(f"({norm(r[mcol])})") or CODE_RE.search(norm(r[mcol]))
        mcode, part = m.group(1).upper(), (m.group(2) if m.re is RESULT_RE else "") or ""
        raw = r[vcol] if vcol < len(r) else None
        v, status = number(raw), (norm(raw) if norm(raw) in MARKERS else "")
        if v is None and not status:
            continue
        code, name = ident(r)
        tenure = tenure_of(norm(r[tcol])) if tcol is not None and tcol < len(r) else sheet_tenure
        recs.append([year, tenure, code, name, mcode, part, PART_NAMES.get((mcode, part), ""),
                     "per 1,000 homes" if mcode in RATE_MEASURES else "%", "" if v is None else v, status])
    return recs, f"long: header row {hi + 1}, measure column '{header[mcol]}', value column '{header[vcol]}', ids {ids or 'not found'}"


RESULT_HEAD = ["year", "tenure", "provider_code", "provider_name", "measure", "part", "part_name", "unit", "value", "status"]
LANDLORD_HEAD = ["year", "provider_code", "provider_name"] + [k for k, _ in LANDLORD_FIELDS]
SURVEY_HEAD = ["year", "provider_code", "tenure"] + [k for k, _ in SURVEY_FIELDS]


def write_csv(path, head, rows):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(head)
        w.writerows(rows)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--fixtures", help="read sources from this folder instead of the internet")
    ap.add_argument("--file", help="convert this downloaded full dataset instead of looking on GOV.UK")
    ap.add_argument("--year", help="the reporting year of --file, such as 2025-26 (read from the file if left out)")
    args = ap.parse_args()
    f = Fetcher(args.fixtures)
    OUT.mkdir(parents=True, exist_ok=True)
    if args.file:
        path = Path(args.file).resolve()
        blob = path.read_bytes()
        year = args.year or year_in(path.name, blob)
        if not year:
            print("Couldn't tell the reporting year from the file: pass --year, such as --year 2025-26.")
            return 1
        f.local["local:" + path.name] = blob  # record only the file name, not where it was on your computer
        editions = [{"year": year, "title": path.name, "page": "", "updated": "", "files": [{"title": path.name, "url": "local:" + path.name}]}]
    else:
        editions = find_editions(f)
    if not editions:
        print("No TSM editions with a full dataset were found on GOV.UK.")
        return 1
    sources, summary = [], []
    structure = ["# TSM data: structure of the source files", "",
                 "Written by `scripts/fetch_tsm.py`. Check this when the regulator changes its layout.", ""]
    for ed in editions:
        recs, notes, landlords, surveys = [], [], {}, {}
        for fl in ed["files"]:
            blob = f.get(fl["url"])
            if not ed["year"]:
                ed["year"] = year_in(fl["url"].rsplit("/", 1)[-1], blob)
            if not ed["year"]:
                print(f"! skipped {fl['url']}: couldn't tell which reporting year it covers")
                continue
            sources.append({"year": ed["year"], "page": ed["page"], "updated": ed["updated"], "file": fl["title"],
                            "url": fl["url"], "sha256": hashlib.sha256(blob).hexdigest(), "bytes": len(blob)})
            structure += [f"## {ed['year']}: {fl['title']}", "", f"Source: {fl['url']}", ""]
            for label, rows in tables_from(fl["url"].rsplit("/", 1)[-1], blob):
                r, note = convert(label, rows, ed["year"], landlords, surveys)
                recs += r
                notes.append(f"{label}: {note[:200]}, {len(r)} values")
                hi, _ = find_header(rows)
                structure += [f"### {label}", "", f"{len(rows)} rows. {note}. {len(r)} results.", ""]
                if hi is not None:
                    hdr = [norm(c) for c in rows[hi]]
                    cols = result_columns(hdr, tenure_of(label))
                    if cols:
                        structure += ["Result columns used:", ""] + [f"- {mc}{(' part ' + pt) if pt else ''} ({tn}): {hdr[j][:140]}" for j, mc, pt, tn in cols] + [""]
                    for sample in rows[hi + 1:hi + 3]:
                        structure += ["- Sample: " + " | ".join(norm(c) for c in sample[:8])]
                    structure.append("")
        # Drop duplicates (the same value in two files), then sort by landlord
        seen, out = set(), []
        for rec in recs:
            k = (rec[1], rec[2], rec[3], rec[4], rec[5])
            if k not in seen:
                seen.add(k)
                out.append(rec)
        out.sort(key=lambda x: (x[3].lower(), x[1], x[4], x[5]))
        write_csv(OUT / f"{ed['year']}.csv", RESULT_HEAD, out)
        write_csv(OUT / f"{ed['year']}-landlords.csv", LANDLORD_HEAD,
                  sorted(([ed["year"], v.get("provider_code", ""), v.get("provider_name", "")] + [v.get(k, "") for k, _ in LANDLORD_FIELDS]
                          for v in landlords.values()), key=lambda x: x[2].lower()))
        write_csv(OUT / f"{ed['year']}-surveys.csv", SURVEY_HEAD,
                  sorted(([ed["year"], v["provider_code"], v["tenure"]] + [v.get(k, "") for k, _ in SURVEY_FIELDS]
                          for v in surveys.values()), key=lambda x: (x[1], x[2])))
        vals = [x for x in out if x[8] != ""]
        meas = sorted({x[4] for x in vals})
        by_t = {t: len({x[2] for x in vals if x[1] == t}) for t in sorted({x[1] for x in vals})}
        line = (f"- {ed['year']}: {len(vals)} values for {len(landlords)} landlords and {len(meas)} measures"
                f" ({', '.join(f'{t}: {n} landlords' for t, n in by_t.items())})")
        missing = [m for m in ["TP%02d" % i for i in range(1, 13)] + ["CH01", "CH02", "NM01", "RP01", "RP02"] + ["BS%02d" % i for i in range(1, 6)] if m not in meas]
        if missing:
            line += f". Not found: {', '.join(missing)}"
        summary.append(line)
        print(line)
        for n in notes:
            print("   ", n)
    (OUT / "sources.json").write_text(json.dumps(sources, indent=1), encoding="utf-8")
    (OUT / "STRUCTURE.md").write_text("\n".join(structure) + "\n", encoding="utf-8")
    (OUT / "SUMMARY.md").write_text("# TSM data: what was converted\n\n" + "\n".join(summary) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
