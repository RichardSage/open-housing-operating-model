#!/usr/bin/env python3
"""Validate the Open Housing Operating Model and build its outputs.

Usage:
  python scripts/build.py            # validate, then write dist/, site/ and refresh README numbers
  python scripts/build.py --check    # validate only (used on pull requests)

Needs Python 3.9+ and PyYAML (pip install pyyaml).

The model has two views of the same organisation:
  - Services (model/services.yaml): the outside-in view, as residents and colleagues see it.
    Service > Request (tagged with an interaction pattern).
  - Operating model (model/function-areas/*.yaml): the inside-out view of how the work is done.
    Domain > Function area > Function > Activity.
Requests link to the functions or activities they rely on through `uses`.
"""
import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
MODEL = ROOT / "model"
DIST = ROOT / "dist"
SITE = ROOT / "site"
SLUG = "open-housing-operating-model"

AREA_KEYS = {"code", "name", "domain", "description", "functions", "notes", "references"}
FUNCTION_KEYS = {"code", "name", "description", "activities", "notes", "references"}
ACTIVITY_KEYS = {"code", "name", "description", "notes", "references", "aliases"}
SERVICE_KEYS = {"code", "name", "group", "users", "goal", "description", "requests", "notes", "references"}
REQUEST_KEYS = {"code", "name", "pattern", "uses", "description", "notes", "aliases"}

errors, warnings = [], []


def err(where, msg):
    errors.append(f"{where}: {msg}")


def warn(where, msg):
    warnings.append(f"{where}: {msg}")


def load(path):
    try:
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except yaml.YAMLError as e:
        err(path.name, f"is not valid YAML ({e})")
        return {}


def check_name(where, name):
    if not isinstance(name, str) or not name.strip():
        err(where, "needs a name")
        return
    if name != name.strip() or "  " in name:
        err(where, f"name has extra spaces: '{name}'")
    if len(name) > 90:
        warn(where, f"name is long ({len(name)} characters); aim for under 90")
    if name.endswith("."):
        warn(where, "name should not end with a full stop")


def num_key(code):
    return [int(p) for p in re.findall(r"\d+", str(code))]


def load_operating_model(domain_ids, retired, seen):
    areas = []
    files = sorted((MODEL / "function-areas").glob("*.yaml"))
    if not files:
        err("model/function-areas", "no function area files found")
    for path in files:
        a = load(path)
        if not a:
            continue
        w = path.name
        if "services" in a and "functions" not in a:
            err(w, "the 'services' key is now called 'functions' (see CHANGELOG 0.2.0)")
        for k in set(a) - AREA_KEYS - {"services"}:
            err(w, f"unknown field '{k}' (allowed: {', '.join(sorted(AREA_KEYS))})")
        code = str(a.get("code", ""))
        if not re.fullmatch(r"\d{2}", code):
            err(w, f"function area code '{code}' must be two digits, e.g. \"07\"")
        if not path.name.startswith(code + "-"):
            err(w, f"file name should start with the area code '{code}-'")
        check_name(w, a.get("name"))
        if a.get("domain") not in domain_ids:
            err(w, f"domain '{a.get('domain')}' is not in domains.yaml ({', '.join(domain_ids)})")
        functions = a.get("functions") or []
        if not functions:
            err(w, "has no functions")
        names = set()
        for f in functions:
            fc = str(f.get("code", ""))
            fw = f"{w} › {fc or '?'}"
            for k in set(f) - FUNCTION_KEYS:
                err(fw, f"unknown field '{k}'")
            if not re.fullmatch(rf"{code}\.\d+", fc):
                err(fw, f"function code must look like {code}.N")
            check_name(fw, f.get("name"))
            if f.get("name") in names:
                err(fw, f"duplicate function name '{f.get('name')}' in this area")
            names.add(f.get("name"))
            acts = f.get("activities") or []
            if not acts:
                err(fw, "has no activities")
            anames = set()
            for x in acts:
                xc = str(x.get("code", ""))
                xw = f"{w} › {xc or '?'}"
                for k in set(x) - ACTIVITY_KEYS:
                    err(xw, f"unknown field '{k}'")
                if not re.fullmatch(rf"{re.escape(fc)}\.\d+", xc):
                    err(xw, f"activity code must look like {fc}.N")
                check_name(xw, x.get("name"))
                if x.get("name") in anames:
                    err(xw, f"duplicate activity name '{x.get('name')}' in this function")
                anames.add(x.get("name"))
        codes = [code] + [str(f.get("code")) for f in functions] + \
                [str(x.get("code")) for f in functions for x in (f.get("activities") or [])]
        for c in codes:
            if c in seen:
                err(w, f"code {c} is already used in {seen[c]}")
            seen[c] = w
            if c in retired:
                err(w, f"code {c} has been retired and must not be reused")
        areas.append(a)
    areas.sort(key=lambda a: num_key(a["code"]))
    for a in areas:
        a["functions"].sort(key=lambda f: num_key(f["code"]))
        for f in a["functions"]:
            f["activities"].sort(key=lambda x: num_key(x["code"]))
    return areas


def load_services(fn_index, act_index, retired, seen):
    doc = load(MODEL / "services.yaml")
    w = "services.yaml"
    patterns = doc.get("patterns") or []
    users = doc.get("users") or []
    groups = doc.get("groups") or []
    services = doc.get("services") or []
    pids, uids, gids = {p["id"] for p in patterns}, {u["id"] for u in users}, {g["id"] for g in groups}
    for s in services:
        sc = str(s.get("code", ""))
        sw = f"{w} › {sc or '?'}"
        for k in set(s) - SERVICE_KEYS:
            err(sw, f"unknown field '{k}'")
        if not re.fullmatch(r"S\d{2,3}", sc):
            err(sw, "service code must look like S01")
        check_name(sw, s.get("name"))
        if s.get("group") not in gids:
            err(sw, f"group '{s.get('group')}' is not listed under groups")
        for u in s.get("users") or []:
            if u not in uids:
                err(sw, f"user '{u}' is not listed under users")
        if not s.get("users"):
            err(sw, "needs at least one user")
        reqs = s.get("requests") or []
        if not reqs:
            err(sw, "has no requests")
        for r in reqs:
            rc = str(r.get("code", ""))
            rw = f"{w} › {rc or '?'}"
            for k in set(r) - REQUEST_KEYS:
                err(rw, f"unknown field '{k}'")
            if not re.fullmatch(rf"{re.escape(sc)}\.\d+", rc):
                err(rw, f"request code must look like {sc}.N")
            check_name(rw, r.get("name"))
            if r.get("pattern") not in pids:
                err(rw, f"pattern '{r.get('pattern')}' must be one of: {', '.join(sorted(pids))}")
            uses = [str(u) for u in (r.get("uses") or [])]
            if not uses:
                err(rw, "needs at least one function or activity code in 'uses'")
            for u in uses:
                if u not in fn_index and u not in act_index:
                    err(rw, f"uses '{u}', which is not a function or activity code")
            r["uses"] = uses
        for c in [sc] + [str(r.get("code")) for r in reqs]:
            if c in seen:
                err(w, f"code {c} is already used in {seen[c]}")
            seen[c] = w
            if c in retired:
                err(w, f"code {c} has been retired and must not be reused")
    services.sort(key=lambda s: num_key(s["code"]))
    return {"patterns": patterns, "users": users, "groups": groups, "services": services}


def replace_block(text, name, body):
    pat = re.compile(rf"(<!-- BEGIN:{name} -->).*?(<!-- END:{name} -->)", re.S)
    return pat.sub(lambda m: m.group(1) + "\n" + body + "\n" + m.group(2), text)


def main(check_only):
    meta = load(MODEL / "meta.yaml")
    domains = load(MODEL / "domains.yaml").get("domains", [])
    retired = {str(r.get("code")) for r in (load(MODEL / "retired.yaml").get("retired") or [])}
    domain_ids = [d["id"] for d in domains]
    if len(set(domain_ids)) != len(domain_ids):
        err("domains.yaml", "domain ids must be unique")

    seen = {}
    areas = load_operating_model(domain_ids, retired, seen)
    fn_index = {f["code"]: (a, f) for a in areas for f in a["functions"]}
    act_index = {x["code"]: (a, f, x) for a in areas for f in a["functions"] for x in f["activities"]}
    svc = load_services(fn_index, act_index, retired, seen)

    for m in warnings:
        print("warning:", m)
    if errors:
        print(f"\n{len(errors)} problem(s) found:")
        for m in errors:
            print("  -", m)
        sys.exit(1)

    # Which activities each request relies on
    used_by = defaultdict(set)
    for s in svc["services"]:
        for r in s["requests"]:
            acts = set()
            for u in r["uses"]:
                acts |= {x["code"] for x in fn_index[u][1]["activities"]} if u in fn_index else {u}
            r["_acts"] = sorted(acts, key=num_key)
            for c in acts:
                used_by[c].add(s["code"])

    n_f = sum(len(a["functions"]) for a in areas)
    n_a = len(act_index)
    n_s = len(svc["services"])
    n_r = sum(len(s["requests"]) for s in svc["services"])
    n_used = len(used_by)
    print(f"OK: {n_s} services, {n_r} requests | {len(domains)} domains, {len(areas)} function areas, "
          f"{n_f} functions, {n_a} activities | {n_used} activities support a service (v{meta.get('version')})")
    if check_only:
        return

    DIST.mkdir(exist_ok=True)
    dname = {d["id"]: d["name"] for d in domains}

    # JSON: both views
    clean = lambda d: {k: v for k, v in d.items() if not k.startswith("_")}
    model = {
        "meta": meta,
        "services": {**{k: svc[k] for k in ("patterns", "users", "groups")},
                     "services": [{**clean(s), "requests": [clean(r) for r in s["requests"]]} for s in svc["services"]]},
        "domains": [{**d, "function_areas": [{k: v for k, v in a.items() if k != "domain"} for a in areas if a["domain"] == d["id"]]}
                    for d in domains],
    }
    (DIST / f"{SLUG}.json").write_text(json.dumps(model, indent=1, ensure_ascii=False), encoding="utf-8")

    # CSV: one row per activity
    with open(DIST / f"{SLUG}.csv", "w", newline="", encoding="utf-8") as f:
        wr = csv.writer(f)
        wr.writerow(["activity_code", "domain", "function_area_code", "function_area", "function_code", "function",
                     "activity", "supports_services"])
        for a in areas:
            for fn in a["functions"]:
                for x in fn["activities"]:
                    wr.writerow([x["code"], dname[a["domain"]], a["code"], a["name"], fn["code"], fn["name"], x["name"],
                                 " ".join(sorted(used_by.get(x["code"], []), key=num_key))])

    # CSV: one row per request
    gname = {g["id"]: g["name"] for g in svc["groups"]}
    uname = {u["id"]: u["name"] for u in svc["users"]}
    pname = {p["id"]: p["name"] for p in svc["patterns"]}
    with open(DIST / "open-housing-services.csv", "w", newline="", encoding="utf-8") as f:
        wr = csv.writer(f)
        wr.writerow(["request_code", "service_code", "service", "group", "users", "goal", "request", "pattern",
                     "uses", "function_areas"])
        for s in svc["services"]:
            for r in s["requests"]:
                fa = sorted({act_index[c][0]["code"] + " " + act_index[c][0]["name"] for c in r["_acts"]})
                wr.writerow([r["code"], s["code"], s["name"], gname[s["group"]], "; ".join(uname[u] for u in s["users"]),
                             s.get("goal", ""), r["name"], pname[r["pattern"]], " ".join(r["uses"]), "; ".join(fa)])

    # Compact data for the atlas page
    aidx = {a["code"]: i for i, a in enumerate(areas)}
    compact = {
        "version": meta.get("version"), "released": str(meta.get("released", "")), "repo": meta.get("repo_url", ""),
        "domains": [d["name"] for d in domains],
        "areas": [{"c": a["code"], "n": a["name"], "desc": a.get("description", ""), "d": domain_ids.index(a["domain"]),
                   "s": [{"c": f["code"], "n": f["name"], "a": [x["name"] for x in f["activities"]],
                          "u": [sorted(used_by.get(x["code"], []), key=num_key) for x in f["activities"]]}
                         for f in a["functions"]]} for a in areas],
        "patterns": [{"id": p["id"], "n": p["name"], "desc": p.get("description", "")} for p in svc["patterns"]],
        "users": [{"id": u["id"], "n": u["name"]} for u in svc["users"]],
        "groups": [{"id": g["id"], "n": g["name"]} for g in svc["groups"]],
        "services": [{"c": s["code"], "n": s["name"], "g": s["group"], "u": s["users"], "goal": s.get("goal", ""),
                      "r": [{"c": r["code"], "n": r["name"], "p": r["pattern"],
                             "a": [[aidx[act_index[c][0]["code"]], c] for c in r["_acts"]]} for r in s["requests"]]}
                     for s in svc["services"]],
    }
    tpl = (SITE / "template.html").read_text(encoding="utf-8")
    (SITE / "index.html").write_text(tpl.replace("__DATA__", json.dumps(compact, ensure_ascii=False, separators=(",", ":"))),
                                     encoding="utf-8")
    for name in (f"{SLUG}.csv", f"{SLUG}.json", "open-housing-services.csv"):
        (SITE / name).write_bytes((DIST / name).read_bytes())

    # Refresh the generated parts of README.md
    readme_path = ROOT / "README.md"
    if readme_path.exists():
        readme = readme_path.read_text(encoding="utf-8")
        counts = (f"Version {meta.get('version')} has **{n_s} services** made up of **{n_r} requests**, delivered through "
                  f"**{len(areas)} function areas, {n_f} functions and {n_a} activities**.")
        svc_rows = ["| Code | Service | Group | Requests |", "|---|---|---|---|"] + [
            f"| {s['code']} | {s['name']} | {gname[s['group']]} | {len(s['requests'])} |" for s in svc["services"]]
        area_rows = ["| Code | Function area | Domain | Functions | Activities |", "|---|---|---|---|---|"] + [
            f"| {a['code']} | {a['name']} | {dname[a['domain']]} | {len(a['functions'])} | "
            f"{sum(len(f['activities']) for f in a['functions'])} |" for a in areas]
        readme = replace_block(readme, "counts", counts)
        readme = replace_block(readme, "services", "\n".join(svc_rows))
        readme = replace_block(readme, "areas", "\n".join(area_rows))
        readme_path.write_text(readme, encoding="utf-8")

    print(f"Wrote dist/ (2 CSVs and JSON), site/index.html and refreshed README.md")


if __name__ == "__main__":
    main("--check" in sys.argv)
