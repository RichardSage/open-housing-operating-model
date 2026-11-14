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

Optional layers (layers/<id>/layer.yaml) add a point of view about activities, such as AI impact,
without changing the model. They are validated against the model and published separately.
"""
import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import yaml
from datetime import date

ROOT = Path(__file__).resolve().parent.parent
MODEL = ROOT / "model"
DIST = ROOT / "dist"
LAYERS = ROOT / "layers"
SITE = ROOT / "site"
SLUG = "open-housing-operating-model"

AREA_KEYS = {"code", "name", "domain", "description", "functions", "notes", "references"}
FUNCTION_KEYS = {"code", "name", "description", "activities", "notes", "references", "specialist"}
ACTIVITY_KEYS = {"code", "name", "description", "notes", "references", "aliases"}
SERVICE_KEYS = {"code", "name", "group", "users", "goal", "description", "requests", "notes", "references", "specialist"}
REQUEST_KEYS = {"code", "name", "pattern", "uses", "description", "notes", "aliases", "specialist"}

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


OBL_TYPES = {"act": "law", "regulations": "law", "standard": "standard", "code": "code"}
OBL_STATUS = {"in-force", "partly-in-force", "not-yet-in-force"}
AS_OF = date.today()


def parse_when(v):
    """YYYY, YYYY-MM or YYYY-MM-DD -> date (YYYY means 1 July, YYYY-MM the 1st of the month)."""
    m = re.fullmatch(r"(\d{4})(?:-(\d{2}))?(?:-(\d{2}))?", str(v or ""))
    if not m:
        return None
    y, mo, d = int(m.group(1)), m.group(2), m.group(3)
    return date(y, int(mo) if mo else 7, int(d) if d else 1)


def load_register_layer(ly, w, folder, fn_index, act_index):
    """A register layer: obligations plus links to functions/activities. Lenses are derived, not hand-edited."""
    reg = load(folder / str(ly.get("register", "register.yaml"))).get("obligations") or []
    ids = {}
    for i, o in enumerate(reg):
        ow = f"{w}/register.yaml › {o.get('id', '?')}"
        if not o.get("id") or not o.get("name"):
            err(ow, "each obligation needs an id and a name")
            continue
        if o["id"] in ids:
            err(ow, "duplicate obligation id")
        ids[o["id"]] = i
        if o.get("type") not in OBL_TYPES:
            err(ow, f"type must be one of: {', '.join(OBL_TYPES)}")
        if o.get("status") not in OBL_STATUS:
            err(ow, f"status must be one of: {', '.join(sorted(OBL_STATUS))}")
        for c in o.get("changes") or []:
            if not parse_when(c.get("date")):
                err(ow, f"change date '{c.get('date')}' must be YYYY, YYYY-MM or YYYY-MM-DD")
            if c.get("certainty") not in ("confirmed", "expected"):
                err(ow, "change certainty must be 'confirmed' or 'expected'")
        if not o.get("last_checked"):
            warn(ow, "has no last_checked date")
        watch = o.get("watch")
        if watch is not None and (not isinstance(watch, list)
                                  or not all(isinstance(u, str) and u.startswith("https://") for u in watch)):
            err(ow, "watch must be a list of https:// links")
    links = defaultdict(lambda: {"requires": set(), "shapes": set()})
    lpath = folder / str(ly.get("links", "links.csv"))
    if not lpath.is_file():
        err(w, f"links file '{lpath.name}' not found")
        return None
    with open(lpath, newline="", encoding="utf-8") as f:
        for i, row in enumerate(csv.DictReader(f), start=2):
            rw = f"{w}/{lpath.name} line {i}"
            code, ob, rel = (row.get("code") or "").strip(), (row.get("obligation") or "").strip(), (row.get("relation") or "").strip()
            if ob not in ids:
                err(rw, f"obligation '{ob}' is not in the register")
                continue
            if rel not in ("requires", "shapes"):
                err(rw, "relation must be 'requires' or 'shapes'")
                continue
            if code in fn_index:
                targets = [x["code"] for x in fn_index[code][1]["activities"]]
            elif code in act_index:
                targets = [code]
            else:
                err(rw, f"'{code}' is not a function or activity code in the model")
                continue
            for t in targets:
                links[t][rel].add(ob)
    rank = {"law": 0, "standard": 1, "code": 2}
    values = {}
    for code in act_index:
        lk = links.get(code, {"requires": set(), "shapes": set()})
        req_kinds = [OBL_TYPES[reg[ids[o]]["type"]] for o in lk["requires"]]
        basis = min(req_kinds, key=lambda k: rank[k]) if req_kinds else "none"
        soonest = None
        for o in lk["requires"] | lk["shapes"]:
            for c in reg[ids[o]].get("changes") or []:
                d = parse_when(c.get("date"))
                if d and d >= AS_OF and (soonest is None or d < soonest):
                    soonest = d
        if soonest is None:
            changing = "stable"
        else:
            months = (soonest.year - AS_OF.year) * 12 + soonest.month - AS_OF.month
            changing = "next-12" if months <= 12 else "1-3y" if months <= 36 else "later"
        values[code] = {"basis": basis, "changing": changing}
    ly["_register"] = reg
    ly["_reg_ids"] = ids
    ly["_links"] = {c: {k: sorted(v) for k, v in d.items()} for c, d in links.items()}
    ly["as_of"] = AS_OF.isoformat()
    return values


def load_layers(act_index, fn_index=None):
    """Load optional activity layers. Each has layer.yaml (definitions) and a CSV keyed by activity code."""
    layers = []
    if not LAYERS.exists():
        return layers
    for ly_path in sorted(LAYERS.glob("*/layer.yaml")):
        ly = load(ly_path)
        w = f"layers/{ly_path.parent.name}"
        if not ly:
            continue
        fields = ly.get("fields") or {}
        if ly.get("applies_to") != "activities":
            err(w, "only layers that apply to 'activities' are supported")
            continue
        if not fields:
            err(w, "layer.yaml needs at least one field under 'fields'")
            continue
        allowed = {f: [str(v["id"]) for v in (fd.get("values") or [])] for f, fd in fields.items()}
        if ly.get("kind") == "register":
            values = load_register_layer(ly, w, ly_path.parent, fn_index or {}, act_index)
            if values is not None:
                layers.append({**ly, "_values": values})
            continue
        data_path = ly_path.parent / str(ly.get("data", ""))
        if not data_path.is_file():
            err(w, f"data file '{ly.get('data')}' not found")
            continue
        values, missing_cols = {}, []
        with open(data_path, newline="", encoding="utf-8") as f:
            rd = csv.DictReader(f)
            missing_cols = [c for c in ["code", *fields] if c not in (rd.fieldnames or [])]
            if missing_cols:
                err(w, f"{data_path.name} is missing columns: {', '.join(missing_cols)}")
                continue
            for i, row in enumerate(rd, start=2):
                code = (row.get("code") or "").strip()
                rw = f"{w}/{data_path.name} line {i}"
                if code not in act_index:
                    err(rw, f"'{code}' is not an activity code in the model")
                    continue
                if code in values:
                    err(rw, f"activity {code} appears more than once")
                    continue
                if row.get("activity") and row["activity"].strip() != act_index[code][2]["name"]:
                    warn(rw, f"activity name differs from the model ('{act_index[code][2]['name']}'); the model's name is used")
                rec = {}
                for fld, ok in allowed.items():
                    v = (row.get(fld) or "").strip()
                    if ok and v not in ok:
                        err(rw, f"{fld} '{v}' must be one of: {', '.join(ok)}")
                    rec[fld] = v
                values[code] = rec
        gaps = [c for c in act_index if c not in values]
        if gaps:
            warn(w, f"{len(gaps)} activities have no values in this layer yet (e.g. {', '.join(gaps[:5])})")
        layers.append({**{k: v for k, v in ly.items() if k != "data"}, "_values": values})
    return layers


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
    specs = (load(MODEL / "specialist.yaml") or {}).get("specialist") or []
    spec_ids = [x["id"] for x in specs]
    def check_spec(where, item):
        tags = item.get("specialist") or []
        if not isinstance(tags, list):
            err(where, "specialist must be a list, e.g. [older-people]")
            tags = []
        for t in tags:
            if t not in spec_ids:
                err(where, f"specialist '{t}' is not in specialist.yaml ({', '.join(spec_ids)})")
        item["specialist"] = [t for t in tags if t in spec_ids]
    for a in areas:
        for f in a["functions"]:
            check_spec(f"{a['code']} › {f['code']}", f)
    for s in svc["services"]:
        check_spec(f"services.yaml › {s['code']}", s)
        for r in s["requests"]:
            check_spec(f"services.yaml › {r['code']}", r)
    layers = load_layers(act_index, fn_index)

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
    for ly in layers:
        print(f"Layer '{ly['id']}' v{ly.get('version')}: values for {len(ly['_values'])} of {n_a} activities")
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

    sname = {x["id"]: x["name"] for x in specs}
    # CSV: one row per activity
    with open(DIST / f"{SLUG}.csv", "w", newline="", encoding="utf-8") as f:
        wr = csv.writer(f)
        wr.writerow(["activity_code", "domain", "function_area_code", "function_area", "function_code", "function",
                     "activity", "supports_services", "specialist"])
        for a in areas:
            for fn in a["functions"]:
                for x in fn["activities"]:
                    wr.writerow([x["code"], dname[a["domain"]], a["code"], a["name"], fn["code"], fn["name"], x["name"],
                                 " ".join(sorted(used_by.get(x["code"], []), key=num_key)),
                                 "; ".join(sname[t] for t in fn["specialist"])])

    # CSV: one row per request
    gname = {g["id"]: g["name"] for g in svc["groups"]}
    uname = {u["id"]: u["name"] for u in svc["users"]}
    pname = {p["id"]: p["name"] for p in svc["patterns"]}
    with open(DIST / "open-housing-services.csv", "w", newline="", encoding="utf-8") as f:
        wr = csv.writer(f)
        wr.writerow(["request_code", "service_code", "service", "group", "users", "goal", "request", "pattern",
                     "uses", "function_areas", "specialist"])
        for s in svc["services"]:
            for r in s["requests"]:
                fa = sorted({act_index[c][0]["code"] + " " + act_index[c][0]["name"] for c in r["_acts"]})
                wr.writerow([r["code"], s["code"], s["name"], gname[s["group"]], "; ".join(uname[u] for u in s["users"]),
                             s.get("goal", ""), r["name"], pname[r["pattern"]], " ".join(r["uses"]), "; ".join(fa),
                             "; ".join(sname[t] for t in dict.fromkeys(s["specialist"] + r["specialist"]))])

    # Compact data for the atlas page
    aidx = {a["code"]: i for i, a in enumerate(areas)}
    compact = {
        "version": meta.get("version"), "released": str(meta.get("released", "")), "repo": meta.get("repo_url", ""),
        "domains": [d["name"] for d in domains],
        "areas": [{"c": a["code"], "n": a["name"], "desc": a.get("description", ""), "d": domain_ids.index(a["domain"]),
                   "s": [{"c": f["code"], "n": f["name"], "a": [x["name"] for x in f["activities"]],
                          "u": [sorted(used_by.get(x["code"], []), key=num_key) for x in f["activities"]],
                          "sp": [spec_ids.index(t) for t in f["specialist"]]}
                         for f in a["functions"]]} for a in areas],
        "patterns": [{"id": p["id"], "n": p["name"], "desc": p.get("description", "")} for p in svc["patterns"]],
        "users": [{"id": u["id"], "n": u["name"]} for u in svc["users"]],
        "groups": [{"id": g["id"], "n": g["name"]} for g in svc["groups"]],
        "specs": [{"id": x["id"], "n": x["name"], "desc": x.get("description", "")} for x in specs],
        "services": [{"c": s["code"], "n": s["name"], "g": s["group"], "u": s["users"], "goal": s.get("goal", ""),
                      "sp": [spec_ids.index(t) for t in s["specialist"]],
                      "r": [{"c": r["code"], "n": r["name"], "p": r["pattern"], "sp": [spec_ids.index(t) for t in r["specialist"]],
                             "a": [[aidx[act_index[c][0]["code"]], c] for c in r["_acts"]]} for r in s["requests"]]}
                     for s in svc["services"]],
        "layers": [{"id": ly["id"], "n": ly.get("name", ly["id"]), "v": str(ly.get("version", "")), "summary": ly.get("summary", ""),
                    "caveat": ly.get("caveat", ""), "sources": ly.get("sources") or [],
                    "fields": [{"id": f, "n": fd.get("name", f), "vals": [{"id": str(v["id"]), "n": v.get("name", str(v["id"])),
                                                                           "desc": v.get("description", "")} for v in fd.get("values") or []]}
                               for f, fd in ly["fields"].items()],
                    "data": {c: [next((i for i, v in enumerate(fd.get("values") or []) if str(v["id"]) == rec[f]), -1)
                                 for f, fd in ly["fields"].items()] for c, rec in ly["_values"].items()},
                    **({"asOf": ly.get("as_of"),
                        "register": [{"id": o["id"], "n": o["name"], "t": o.get("type"), "st": o.get("status"),
                                      "enf": o.get("enforcer", ""), "url": o.get("url", ""), "chk": str(o.get("last_checked", "")),
                                      "ch": [{"d": str(c.get("date")), "c": c.get("certainty"), "s": c.get("summary", "")}
                                             for c in o.get("changes") or []]} for o in ly["_register"]],
                        "links": {c: [[ly["_reg_ids"][o], 0] for o in d["requires"]] + [[ly["_reg_ids"][o], 1] for o in d["shapes"] if o not in d["requires"]]
                                  for c, d in ly["_links"].items()}} if ly.get("kind") == "register" else {})}
                   for ly in layers],
    }
    # Layers: one JSON and one CSV each, kept apart from the core model outputs
    if layers:
        (DIST / "layers").mkdir(exist_ok=True)
        (SITE / "layers").mkdir(exist_ok=True)
    for ly in layers:
        out = {k: v for k, v in ly.items() if not k.startswith("_")}
        lk = ly.get("_links", {})
        out["activities"] = [{"code": c, "activity": act_index[c][2]["name"], **rec,
                              **({"requires": lk.get(c, {}).get("requires", []), "shapes": lk.get(c, {}).get("shapes", [])} if lk else {})}
                             for c, rec in sorted(ly["_values"].items(), key=lambda kv: num_key(kv[0]))]
        if ly.get("_register"):
            out["register"] = ly["_register"]
        (DIST / "layers" / f"{ly['id']}.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
        with open(DIST / "layers" / f"{ly['id']}.csv", "w", newline="", encoding="utf-8") as f:
            wr = csv.writer(f)
            lk = ly.get("_links", {})
            wr.writerow(["activity_code", "function_area", "function", "activity", *ly["fields"].keys(),
                         *(["requires", "shapes"] if lk else [])])
            for c, rec in sorted(ly["_values"].items(), key=lambda kv: num_key(kv[0])):
                a, fn, x = act_index[c]
                wr.writerow([c, a["name"], fn["name"], x["name"], *[rec[k] for k in ly["fields"]],
                             *([" ".join(lk.get(c, {}).get("requires", [])), " ".join(lk.get(c, {}).get("shapes", []))] if lk else [])])
        for ext in ("json", "csv"):
            (SITE / "layers" / f"{ly['id']}.{ext}").write_bytes((DIST / "layers" / f"{ly['id']}.{ext}").read_bytes())

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
