#!/usr/bin/env python3
"""Phase-2 step 1: establish the 93-unit base registry, backfill ALL historical
iNaturalist observations of those species at 二格山 (place 130869), attribute each
to the nearest same-species unit (hybrid species×site + GPS), and MEASURE coverage
(how rich the per-unit phenology timelines will be).

Outputs: data/registry/units.{json,csv}, data/history/records.json,
         data/history/coverage.csv  + a printed summary."""
import csv, json, math, os, time, collections, datetime
import urllib.request, urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
ENR = os.path.join(HERE, "data", "2026-04-25", "profile_enriched.json")
REG = os.path.join(HERE, "data", "registry")
HIST = os.path.join(HERE, "data", "history")
os.makedirs(REG, exist_ok=True); os.makedirs(HIST, exist_ok=True)
PLACE = "130869"
BASE_DATE = "2026-04-25"
PHENO = {13: "flower", 14: "fruit", 15: "bud", 21: "none"}   # iNat term 12 values


def hav(a1, o1, a2, o2):
    R = 6371000; p1, p2 = math.radians(a1), math.radians(a2)
    dp, dl = math.radians(a2 - a1), math.radians(o2 - o1)
    x = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2 * R * math.asin(math.sqrt(x))


# ---- 1. base registry (stable unit_id by trail order) ----
pts = json.load(open(ENR))
units = []
for i, p in enumerate(pts, 1):
    units.append({"unit_id": f"ERG-{i:03d}", "base_obs_id": p["u"].rstrip("/").split("/")[-1],
                  "taxon_id": p["tid"], "scientific": p["s"], "common": p["c"],
                  "family": p["f"], "family_zh": p["fz"], "lat": p["lat"], "lng": p["lng"],
                  "elev_m": p["y"], "dist_m": p["x"], "quality": p["g"]})
# ---- 1b. manually included units ----
# Observations that the 2026-04-25 walk did not produce a unit for, but that should
# still be tracked as ridgeline samples. They are appended AFTER the baseline units,
# so ERG-001..ERG-093 keep their trail-order ids (and their page URLs) unchanged.
# Position/elevation are resolved the same way as the baseline: iNat coordinates,
# SRTM 30 m elevation, and along-trail distance = projection onto the 2026-04-25
# trail polyline (perpendicular offset kept separately as off_trail_m, never folded
# into dist_m). A id that cannot be fetched is skipped with a warning rather than
# failing the whole daily sync.
EXTRA_UNIT_IDS = [395425555, 343780669]


def _get(url, timeout=40):
    return json.load(urllib.request.urlopen(url, timeout=timeout))


def trail_projection(lat, lng):
    """(along-trail m, perpendicular offset m) of a point against the baseline trail.

    Projected in local equirectangular metres (degrees are ~9% anisotropic at this
    latitude, which would bias the nearest-segment parameter)."""
    k = math.cos(math.radians(lat)) * 111320.0                      # m per ° lng
    def xy(la, ln):
        return (ln - lng) * k, (la - lat) * 110540.0                # m per ° lat
    best = (0.0, float("inf"))
    for a, b in zip(pts, pts[1:]):
        ax, ay = xy(a["lat"], a["lng"]); bx, by = xy(b["lat"], b["lng"])
        vx, vy = bx - ax, by - ay
        seg2 = vx * vx + vy * vy
        t = 0.0 if seg2 == 0 else max(0.0, min(1.0, (-ax * vx + -ay * vy) / seg2))
        px, py = ax + t * vx, ay + t * vy
        off = math.hypot(px, py)                                    # point is at the origin
        if off < best[1]:
            best = (a["x"] + t * (b["x"] - a["x"]), off)
    return round(best[0], 1), round(best[1], 1)


def fetch_extra_units(ids, start_index):
    if not ids:
        return []
    try:
        obs = _get("https://api.inaturalist.org/v1/observations/" +
                   ",".join(map(str, ids)) + "?locale=zh-TW")["results"]
    except Exception as e:
        print("extra units: iNat fetch failed, skipping:", e)
        return []
    found = {o["id"]: o for o in obs}
    for i in ids:
        if i not in found:
            print(f"extra units: observation {i} not returned by iNat — skipped")

    # family (Latin + 中文) via /taxa ancestors, same enrichment as fetch_inat.py
    fam = {}
    txids = sorted({(o.get("taxon") or {}).get("id") for o in obs} - {None})
    if txids:
        try:
            for t in _get("https://api.inaturalist.org/v1/taxa/" +
                          ",".join(map(str, txids)) + "?locale=zh-TW")["results"]:
                a = next((x for x in (t.get("ancestors") or []) if x.get("rank") == "family"), None)
                fam[t["id"]] = (a.get("name", ""), a.get("preferred_common_name", "")) if a else ("", "")
        except Exception as e:
            print("extra units: family enrichment failed:", e)

    out = []
    for n, i in enumerate(ids):
        o = found.get(i)
        if not o:
            continue
        coords = (o.get("geojson") or {}).get("coordinates")
        if not coords:
            print(f"extra units: observation {i} has no coordinates — skipped")
            continue
        lng, lat = coords
        tx = o.get("taxon") or {}
        dist_m, off_m = trail_projection(lat, lng)
        elev = None
        try:
            d = _get("https://api.opentopodata.org/v1/srtm30m?" + urllib.parse.urlencode(
                {"locations": f"{lat:.7f},{lng:.7f}", "interpolation": "bilinear"}))
            if d.get("status") == "OK":
                elev = d["results"][0]["elevation"]
        except Exception as e:
            print(f"extra units: DEM sample failed for {i}:", e)
        if elev is None:
            print(f"extra units: observation {i} has no DEM elevation — skipped")
            continue
        f_sci, f_zh = fam.get(tx.get("id"), ("", ""))
        out.append({"unit_id": f"ERG-{start_index + n:03d}", "base_obs_id": str(i),
                    "taxon_id": tx.get("id"), "scientific": tx.get("name"),
                    "common": tx.get("preferred_common_name") or "",
                    "family": f_sci, "family_zh": f_zh, "lat": lat, "lng": lng,
                    "elev_m": elev, "dist_m": dist_m, "quality": o.get("quality_grade"),
                    "source": "manual", "off_trail_m": off_m,
                    "observed_on": o.get("observed_on")})
        print(f"extra unit {out[-1]['unit_id']}: {out[-1]['scientific']} "
              f"obs {i} · {out[-1]['observed_on']} · {elev} m · "
              f"trail {dist_m} m (offset {off_m} m)")
    return out


units += fetch_extra_units(EXTRA_UNIT_IDS, len(units) + 1)

json.dump(units, open(os.path.join(REG, "units.json"), "w"), ensure_ascii=False, indent=2)
with open(os.path.join(REG, "units.csv"), "w", newline="") as f:
    cols = list(dict.fromkeys(k for u in units for k in u))          # baseline keys first
    w = csv.DictWriter(f, fieldnames=cols, restval=""); w.writeheader(); w.writerows(units)

by_tid = collections.defaultdict(list)
for u in units:
    by_tid[u["taxon_id"]].append(u)
tids = sorted(by_tid)
print(f"registry: {len(units)} units, {len(tids)} taxa")


# ---- 2. backfill: all historical obs of these taxa at the site, all observers/time ----
def fetch_all():
    res, page = [], 1
    params = {"place_id": PLACE, "taxon_id": ",".join(map(str, tids)), "per_page": "200",
              "order_by": "observed_on", "order": "asc", "locale": "zh-TW"}
    while True:
        url = "https://api.inaturalist.org/v1/observations?" + urllib.parse.urlencode(dict(params, page=str(page)))
        d = json.load(urllib.request.urlopen(url))
        res += d["results"]
        if len(res) >= d["total_results"] or not d["results"]:
            break
        page += 1; time.sleep(1)
    return res


obs = fetch_all()
print(f"historical observations pulled (63 species @ site, all time): {len(obs)}")


# ---- 3. attribute each obs to nearest same-species unit ----
records = []
for o in obs:
    tx = o.get("taxon") or {}
    cands = by_tid.get(tx.get("id"), [])
    if not cands:
        continue
    coords = (o.get("geojson") or {}).get("coordinates")
    if coords:
        lng, lat = coords
        near = min(cands, key=lambda u: hav(lat, lng, u["lat"], u["lng"]))
        dm = round(hav(lat, lng, near["lat"], near["lng"]), 1)
    else:
        near = cands[0]; lat = lng = None; dm = None
    phenos = [PHENO[a["controlled_value_id"]] for a in (o.get("annotations") or [])
              if a.get("controlled_attribute_id") == 12 and a.get("controlled_value_id") in PHENO]
    photos = o.get("photos") or []
    records.append({"unit_id": near["unit_id"], "taxon_id": tx.get("id"),
                    "obs_id": o.get("id"), "observed_on": o.get("observed_on"),
                    "user": (o.get("user") or {}).get("login"),
                    "quality": o.get("quality_grade"),
                    "phenophase": ";".join(p for p in phenos if p != "none"),
                    "photo": (photos[0].get("url", "").replace("square", "small") if photos else ""),
                    "dist_to_unit_m": dm, "lat": lat, "lng": lng})
json.dump(records, open(os.path.join(HIST, "records.json"), "w"), ensure_ascii=False, indent=2)


# ---- 4. coverage per unit ----
def yr(d):
    return d[:4] if d else None
bu = collections.defaultdict(list)
for r in records:
    bu[r["unit_id"]].append(r)
cov = []
for u in units:
    rs = bu.get(u["unit_id"], [])
    dates = [r["observed_on"] for r in rs if r["observed_on"]]
    prior = [r for r in rs if r["observed_on"] and r["observed_on"] < BASE_DATE]
    cov.append({"unit_id": u["unit_id"], "scientific": u["scientific"], "common": u["common"],
                "n_total": len(rs), "n_prior": len(prior),
                "n_pheno": sum(1 for r in rs if r["phenophase"]),
                "n_photo": sum(1 for r in rs if r["photo"]),
                "n_years": len({yr(d) for d in dates}),
                "n_observers": len({r["user"] for r in rs}),
                "first": min(dates) if dates else "", "last": max(dates) if dates else "",
                "near_50m": sum(1 for r in rs if r["dist_to_unit_m"] is not None and r["dist_to_unit_m"] <= 50)})
with open(os.path.join(HIST, "coverage.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(cov[0].keys())); w.writeheader(); w.writerows(cov)

# ---- summary ----
N = len(units)
def pct(n): return f"{n} ({100*n//N}%)"
print(f"\n=== COVERAGE across {N} units ===")
print("units with >=1 PRIOR (pre-baseline) obs:", pct(sum(1 for c in cov if c["n_prior"] > 0)))
print("units with >=1 phenology annotation:    ", pct(sum(1 for c in cov if c["n_pheno"] > 0)))
print("units with obs in >=2 distinct years:    ", pct(sum(1 for c in cov if c["n_years"] >= 2)))
print("units with >=5 total obs:                ", pct(sum(1 for c in cov if c["n_total"] >= 5)))
tot_prior = sum(c["n_prior"] for c in cov)
print(f"\ntotal historical records attributed: {len(records)} ({tot_prior} pre-baseline)")
allyears = {yr(r['observed_on']) for r in records if r['observed_on']}
print(f"year span: {min(allyears)}–{max(allyears)}  |  observers: {len({r['user'] for r in records})}  |"
      f"  phenology-annotated records: {sum(1 for r in records if r['phenophase'])}")
print("\ntop 8 best-covered units (by prior obs):")
for c in sorted(cov, key=lambda c: -c["n_prior"])[:8]:
    print(f"  {c['unit_id']} {c['scientific'][:24]:24} prior={c['n_prior']:>3} pheno={c['n_pheno']:>3} "
          f"yrs={c['n_years']:>2} obs={c['n_observers']:>2} {c['first']}..{c['last']}")
