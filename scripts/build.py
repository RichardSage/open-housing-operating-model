#!/usr/bin/env python3
"""Validate the Open Housing Operating Model and build its outputs.

Usage:
  python scripts/build.py            # validate, then write dist/ and site/
  python scripts/build.py --check    # validate only (used on pull requests)

Needs Python 3.9+ and PyYAML (pip install pyyaml).
"""
import csv
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
MODEL = ROOT / "model"
DIST = ROOT / "dist"
SITE = ROOT / "site"
SLUG = "open-housing-operating-model"

AREA_KEYS = {"code", "name", "domain", "description", "services", "notes", "references"}
SERVICE_KEYS = {"code", "name", "description", "activities", "notes", "references"}
ACTIVITY_KEYS = {"code", "name", "description", "notes", "references", "aliases"}

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
    return [int(p) for p in str(code).split(".")]


def main(check_only):
    meta = load(MODEL / "meta.yaml")
    domains = load(MODEL / "domains.yaml").get("domains", [])
    retired = {str(r.get("code")) for r in (load(MODEL / "retired.yaml").get("retired") or [])}
    domain_ids = [d["id"] for d in domains]
    if len(set(domain_ids)) != len(domain_ids):
        err("domains.yaml", "domain ids must be unique")

    areas, seen = [], {}
    files = sorted((MODEL / "areas").glob("*.yaml"))
    if not files:
        err("model/areas", "no service area files found")

    for path in files:
        a = load(path)
        if not a:
            continue
        w = path.name
        for k in set(a) - AREA_KEYS:
            err(w, f"unknown field '{k}' (allowed: {', '.join(sorted(AREA_KEYS))})")
        code = str(a.get("code", ""))
        if not re.fullmatch(r"\d{2}", code):
            err(w, f"area code '{code}' must be two digits, e.g. \"07\"")
        if not path.name.startswith(code + "-"):
            err(w, f"file name should start with the area code '{code}-'")
        check_name(w, a.get("name"))
        if a.get("domain") not in domain_ids:
            err(w, f"domain '{a.get('domain')}' is not in domains.yaml ({', '.join(domain_ids)})")
        services = a.get("services") or []
        if not services:
            err(w, "has no services")
        names = set()
        for s in services:
            sc = str(s.get("code", ""))
            sw = f"{w} › {sc or '?'}"
            for k in set(s) - SERVICE_KEYS:
                err(sw, f"unknown field '{k}'")
            if not re.fullmatch(rf"{code}\.\d+", sc):
                err(sw, f"service code must look like {code}.N")
            check_name(sw, s.get("name"))
            if s.get("name") in names:
                err(sw, f"duplicate service name '{s.get('name')}' in this area")
            names.add(s.get("name"))
            acts = s.get("activities") or []
            if not acts:
                err(sw, "has no activities")
            anames = set()
            for x in acts:
                xc = str(x.get("code", ""))
                xw = f"{w} › {xc or '?'}"
                for k in set(x) - ACTIVITY_KEYS:
                    err(xw, f"unknown field '{k}'")
                if not re.fullmatch(rf"{re.escape(sc)}\.\d+", xc):
                    err(xw, f"activity code must look like {sc}.N")
                check_name(xw, x.get("name"))
                if x.get("name") in anames:
                    err(xw, f"duplicate activity name '{x.get('name')}' in this service")
                anames.add(x.get("name"))
        for c in [code] + [str(s.get("code")) for s in services] + [str(x.get("code")) for s in services for x in (s.get("activities") or [])]:
            if c in seen:
                err(w, f"code {c} is already used in {seen[c]}")
            seen[c] = w
            if c in retired:
                err(w, f"code {c} has been retired and must not be reused")
        areas.append(a)

    for m in warnings:
        print("warning:", m)
    if errors:
        print(f"\n{len(errors)} problem(s) found:")
        for m in errors:
            print("  -", m)
        sys.exit(1)

    areas.sort(key=lambda a: num_key(a["code"]))
    for a in areas:
        a["services"].sort(key=lambda s: num_key(s["code"]))
        for s in a["services"]:
            s["activities"].sort(key=lambda x: num_key(x["code"]))
    n_s = sum(len(a["services"]) for a in areas)
    n_a = sum(len(s["activities"]) for a in areas for s in a["services"])
    print(f"OK: {len(domains)} domains, {len(areas)} service areas, {n_s} services, {n_a} activities (v{meta.get('version')})")
    if check_only:
        return

    DIST.mkdir(exist_ok=True)
    dname = {d["id"]: d["name"] for d in domains}
    model = {"meta": meta, "domains": [
        {**d, "service_areas": [{k: v for k, v in a.items() if k != "domain"} for a in areas if a["domain"] == d["id"]]}
        for d in domains]}
    (DIST / f"{SLUG}.json").write_text(json.dumps(model, indent=1, ensure_ascii=False), encoding="utf-8")
    with open(DIST / f"{SLUG}.csv", "w", newline="", encoding="utf-8") as f:
        wr = csv.writer(f)
        wr.writerow(["activity_code", "domain", "service_area_code", "service_area", "service_code", "service", "activity"])
        for a in areas:
            for s in a["services"]:
                for x in s["activities"]:
                    wr.writerow([x["code"], dname[a["domain"]], a["code"], a["name"], s["code"], s["name"], x["name"]])

    # Compact data for the atlas page
    compact = {"version": meta.get("version"), "repo": meta.get("repo_url", ""), "domains": [d["name"] for d in domains], "areas": [
        {"c": a["code"], "n": a["name"], "desc": a.get("description", ""), "d": domain_ids.index(a["domain"]),
         "s": [{"c": s["code"], "n": s["name"], "a": [x["name"] for x in s["activities"]]} for s in a["services"]]}
        for a in areas]}
    tpl = (SITE / "template.html").read_text(encoding="utf-8")
    (SITE / "index.html").write_text(tpl.replace("__DATA__", json.dumps(compact, ensure_ascii=False, separators=(",", ":"))), encoding="utf-8")
    for ext in ("csv", "json"):
        (SITE / f"{SLUG}.{ext}").write_bytes((DIST / f"{SLUG}.{ext}").read_bytes())
    print(f"Wrote dist/{SLUG}.csv, dist/{SLUG}.json and site/index.html")


if __name__ == "__main__":
    main("--check" in sys.argv)
