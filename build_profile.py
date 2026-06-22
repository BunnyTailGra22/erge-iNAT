#!/usr/bin/env python3
"""Build the 二格山 ridgeline elevation transect (before 14:56), with GPS quality
handling: any fix with accuracy >100 m is unreliable in position AND in the DEM
elevation sampled there, so we snap it to the time-interpolated position between
its nearest reliable neighbours, then re-sample elevation and recompute distance.
Outputs profile_before_1456.json + profile_enriched.json (photo + zh family)."""
import csv, json, math, datetime, urllib.request, urllib.parse, os
from datetime import timezone, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(HERE, "data", "2026-04-25")
TW = timezone(timedelta(hours=8))
ACC_THRESH = 100.0            # m; above this a fix is treated as unreliable
CUTOFF = "2026-04-25T14:56:00+08:00"
EXCLUDE_IDS = {"353345277", "353345653"}   # first two (trailhead) obs, removed per request


def t(s):
    return datetime.datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(TW)


def hav(a1, o1, a2, o2):
    R = 6371000
    p1, p2 = math.radians(a1), math.radians(a2)
    dp, dl = math.radians(a2 - a1), math.radians(o2 - o1)
    x = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(x))


rows = list(csv.DictReader(open(os.path.join(BASE, "observations.csv"))))
for r in rows:
    r["_t"] = t(r["time_observed_at"]); r["_lat"] = float(r["lat"]); r["_lng"] = float(r["lng"])
    r["_acc"] = float(r["positional_accuracy"]) if r["positional_accuracy"] else 0.0
rows.sort(key=lambda r: r["_t"])
seg = [r for r in rows if r["_t"] < t(CUTOFF) and r["id"] not in EXCLUDE_IDS]  # ridgeline obs

# --- snap every unreliable fix (acc>thresh) to time-interpolated good neighbours ---
def good(i):
    return seg[i]["_acc"] <= ACC_THRESH
for r in seg:                                  # preserve every original coordinate first
    r["_orig_lat"], r["_orig_lng"] = r["_lat"], r["_lng"]
for i, r in enumerate(seg):
    if r["_acc"] <= ACC_THRESH:
        r["fl"] = 0; r["corr"] = 0; continue
    r["fl"] = 1; r["corr"] = 1
    L = i - 1
    while L >= 0 and not good(L): L -= 1
    R = i + 1
    while R < len(seg) and not good(R): R += 1
    a, b = (seg[L] if L >= 0 else None), (seg[R] if R < len(seg) else None)
    if a and b:
        f = (r["_t"] - a["_t"]).total_seconds() / (b["_t"] - a["_t"]).total_seconds()
        r["_lat"] = a["_orig_lat"] + f * (b["_orig_lat"] - a["_orig_lat"])
        r["_lng"] = a["_orig_lng"] + f * (b["_orig_lng"] - a["_orig_lng"])
    elif a:
        r["_lat"], r["_lng"] = a["_orig_lat"], a["_orig_lng"]
    elif b:
        r["_lat"], r["_lng"] = b["_orig_lat"], b["_orig_lng"]

# --- elevation at corrected positions: SRTM 30m bilinear (fallback: interpolate y) ---
locs = "|".join(f"{r['_lat']:.7f},{r['_lng']:.7f}" for r in seg)
el = None
try:
    url = "https://api.opentopodata.org/v1/srtm30m?" + urllib.parse.urlencode(
        {"locations": locs, "interpolation": "bilinear"})
    d = json.load(urllib.request.urlopen(url, timeout=40))
    if d.get("status") == "OK":
        el = [x["elevation"] for x in d["results"]]; src = "SRTM 30m (bilinear)"
except Exception as e:
    print("opentopodata failed:", e)
if el is None or any(v is None for v in el):
    el = [None] * len(seg); src = "interpolated (DEM fetch failed)"
for r, e in zip(seg, el):
    r["_el"] = e

# --- reuse cached family→中文 map from previous enriched file (+ manual fallback) ---
MAN = {"Rubiaceae":"茜草科","Elaeocarpaceae":"杜英科","Primulaceae":"報春花科","Phyllanthaceae":"葉下珠科",
"Apocynaceae":"夾竹桃科","Lauraceae":"樟科","Pandanaceae":"露兜樹科","Fagaceae":"殼斗科","Ebenaceae":"柿樹科",
"Euphorbiaceae":"大戟科","Theaceae":"山茶科","Myricaceae":"楊梅科","Arecaceae":"棕櫚科","Sabiaceae":"清風藤科",
"Aquifoliaceae":"冬青科","Ericaceae":"杜鵑花科","Annonaceae":"番荔枝科","Symplocaceae":"灰木科",
"Proteaceae":"山龍眼科","Lamiaceae":"唇形科","Hydrangeaceae":"八仙花科","Pentaphylacaceae":"五列木科",
"Oleaceae":"木犀科","Sapindaceae":"無患子科","Daphniphyllaceae":"交讓木科","Actinidiaceae":"獼猴桃科",
"Moraceae":"桑科","Rhamnaceae":"鼠李科","Myrtaceae":"桃金孃科","Elaeagnaceae":"胡頹子科","Araliaceae":"五加科",
"Boraginaceae":"紫草科","Schisandraceae":"五味子科","Viburnaceae":"莢蒾科","Trochodendraceae":"昆欄樹科"}
fam_zh = dict(MAN)
old = os.path.join(BASE, "profile_enriched.json")
if os.path.exists(old):
    for p in json.load(open(old)):
        if p.get("f") and p.get("fz"):
            fam_zh[p["f"]] = p["fz"]

# --- cumulative distance + assemble ---
dist = 0.0
pts = []
for j, r in enumerate(seg):
    if j > 0:
        dist += hav(seg[j-1]["_lat"], seg[j-1]["_lng"], r["_lat"], r["_lng"])
    pts.append({"n": j+1, "t": r["_t"].strftime("%H:%M"), "s": r["scientific_name"],
                "c": r["common_name"] or "", "f": r["family"] or "",
                "fz": fam_zh.get(r["family"], ""), "g": r["quality_grade"],
                "a": r["_acc"], "x": round(dist, 1), "y": r["_el"], "fl": r["fl"],
                "corr": r["corr"], "u": r["uri"], "ph": r["first_photo"] or ""})

# fallback: interpolate any missing elevation by distance between good neighbours
for i, p in enumerate(pts):
    if p["y"] is None:
        L = i-1
        while L >= 0 and pts[L]["y"] is None: L -= 1
        R = i+1
        while R < len(pts) and pts[R]["y"] is None: R += 1
        if L >= 0 and R < len(pts):
            f = (p["x"]-pts[L]["x"])/(pts[R]["x"]-pts[L]["x"] or 1)
            p["y"] = round(pts[L]["y"] + f*(pts[R]["y"]-pts[L]["y"]), 1)
for p in pts:
    p["y"] = round(p["y"], 1)

json.dump(pts, open(os.path.join(BASE, "profile_enriched.json"), "w"), ensure_ascii=False, indent=2)
core = [{k: p[k] for k in ("n","t","s","c","f","g","a","x","y","fl","corr","u")} for p in pts]
json.dump(core, open(os.path.join(BASE, "profile_before_1456.json"), "w"), ensure_ascii=False, indent=2)

# --- report ---
old_y = {p["n"]: p["y"] for p in json.load(open(old))} if os.path.exists(old) else {}
print(f"elevation source: {src}")
print(f"trail length: {pts[-1]['x']:.0f} m  (was ~870)")
print("GPS>100m points — elevation before -> after correction:")
for p in pts:
    if p["fl"]:
        print(f"  #{p['n']:>2} {p['t']} {p['s'][:22]:22} acc {p['a']:>5.0f}m  "
              f"x={p['x']:>6.1f}  y={p['y']:.0f} m")
ys = [p["y"] for p in pts]
print(f"elevation range: {min(ys):.0f}–{max(ys):.0f} m")
