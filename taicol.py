#!/usr/bin/env python3
"""Validate the 63 ridgeline species against the Catalogue of Life in Taiwan
(TaiCoL, https://api.taicol.tw/v2/, no key): Taiwan-accepted scientific name,
family & genus (Chinese + Latin), endemism, and IUCN / national Red List status.

Reuses the proven query pattern + 134-species cache from the sibling
update-erge-phenology skill; only queries TaiCoL for species not already cached.
Writes data/registry/taxa_taicol.json keyed by our (iNat) scientific name."""
import json, os, subprocess, urllib.parse, time

HERE = os.path.dirname(os.path.abspath(__file__))
UNITS = json.load(open(os.path.join(HERE, "data", "registry", "units.json")))
SKILL_CACHE = os.path.expanduser("~/.claude/skills/update-erge-phenology/taicol_cache.json")
OUT = os.path.join(HERE, "data", "registry", "taxa_taicol.json")


def _curl(u):
    return subprocess.run(["curl", "-s", "--max-time", "25", "-H",
                           "User-Agent: erge-inat/1.0", u], capture_output=True, text=True).stdout


def _taicol(common=None, sci=None):
    q = ("common_name=" + urllib.parse.quote(common)) if common else ("scientific_name=" + urllib.parse.quote(sci))
    try:
        d = json.loads(_curl("https://api.taicol.tw/v2/taxon?" + q))
    except Exception:
        return None
    recs = d.get("data", [])
    acc = [r for r in recs if r.get("taxon_status") == "accepted"] or recs
    tw = [r for r in acc if r.get("is_in_taiwan")] or acc
    for want in ("Species", "Variety", "Subspecies", "Genus"):
        for r in tw:
            if r.get("rank") == want:
                return r
    return tw[0] if tw else None


def _lineage(tid):
    try:
        d = json.loads(_curl("https://api.taicol.tw/v2/higherTaxa?taxon_id=" + tid))
    except Exception:
        return {}
    out = {}
    for t in d.get("data", []):
        if t.get("rank") == "Family":
            out["fam_zh"], out["fam_sci"] = t.get("common_name_c"), t.get("simple_name")
        elif t.get("rank") == "Genus":
            out["gen_zh"], out["gen_sci"] = t.get("common_name_c"), t.get("simple_name")
    return out


def conserv(iucn, redlist):
    if iucn in {"CR", "EN", "VU", "NT"}:
        return iucn
    if redlist and redlist not in ("NLC", "NA", "NE", "DD", None):
        return redlist
    return None


def query_taicol(sci, common):
    rec = _taicol(sci=sci); via = "taicol-sci"
    if not rec and common:
        rec = _taicol(common=common); via = "taicol-zh"
    if not rec:
        return None
    e = {"accepted_sci": rec.get("simple_name"), "accepted_zh": rec.get("common_name_c"),
         "is_endemic": bool(rec.get("is_endemic")), "iucn": rec.get("iucn"),
         "redlist": rec.get("redlist"), "protected": rec.get("protected"),
         "taxon_id": rec.get("taxon_id"), "src": via}
    e.update(_lineage(rec["taxon_id"]))
    time.sleep(0.4)
    return e


# seed indexes from the sibling skill's cache (keyed by zh; values carry accepted_sci)
seed = {}
if os.path.exists(SKILL_CACHE):
    tc = json.load(open(SKILL_CACHE)).get("taicol", {})
    by_sci, by_zh = {}, {}
    for zh, v in tc.items():
        if v.get("accepted_sci"):
            by_sci[v["accepted_sci"].lower()] = v
        by_zh[zh] = v
    seed = {"sci": by_sci, "zh": by_zh}

species = {}
for u in UNITS:
    species.setdefault(u["scientific"], u["common"])

out, reused, queried, unresolved = {}, 0, 0, []
for sci, common in species.items():
    v = (seed.get("sci", {}).get(sci.lower()) or seed.get("zh", {}).get(common))
    if v:
        e = {"accepted_sci": v.get("accepted_sci"), "accepted_zh": v.get("accepted_zh"),
             "fam_zh": v.get("fam_zh"), "fam_sci": v.get("fam_sci"),
             "gen_zh": v.get("gen_zh"), "gen_sci": v.get("gen_sci"),
             "is_endemic": bool(v.get("is_endemic")), "iucn": v.get("iucn"),
             "redlist": v.get("redlist"), "protected": v.get("protected"),
             "taxon_id": v.get("taxon_id"), "src": "cache"}
        reused += 1
    else:
        e = query_taicol(sci, common)
        if e:
            queried += 1
        else:
            unresolved.append(sci)
            e = {"accepted_sci": sci, "accepted_zh": common, "fam_zh": None, "fam_sci": None,
                 "gen_zh": None, "gen_sci": sci.split(" ")[0], "is_endemic": False,
                 "iucn": None, "redlist": None, "protected": None, "taxon_id": None, "src": "unresolved"}
    e["threat"] = conserv(e.get("iucn"), e.get("redlist"))
    out[sci] = e

json.dump(out, open(OUT, "w"), ensure_ascii=False, indent=2)

end = sum(1 for e in out.values() if e["is_endemic"])
threat = {k: v["threat"] for k, v in out.items() if v["threat"]}
mismatch = {k: v["accepted_sci"] for k, v in out.items() if v["accepted_sci"] and v["accepted_sci"] != k}
print(f"species: {len(out)}  | reused from cache: {reused}  queried TaiCoL: {queried}  unresolved: {len(unresolved)}")
print(f"endemic (特有): {end}")
print(f"threatened (IUCN/紅皮書): {len(threat)} -> {threat}")
print(f"name mismatches iNat→TaiCoL ({len(mismatch)}):")
for k, v in mismatch.items():
    print(f"   {k}  ->  {v}")
if unresolved:
    print("UNRESOLVED:", unresolved)
print("missing genus-zh:", [k for k, v in out.items() if not v["gen_zh"]])
