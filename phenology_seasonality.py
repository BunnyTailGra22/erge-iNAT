#!/usr/bin/env python3
"""Community + per-species phenophase seasonality, pooled by calendar month.

This is the phenology half of a climate cross-check: it summarises WHEN (which
months) the ridgeline community is flowering / fruiting / in bud, from iNat
term-12 annotations only. It makes NO trend or causal claim — annotations are
too sparse (≈1 flowering record / species / year, 2018–2024) to attribute
inter-annual shifts to climate, and the cross-species pooled signal is
observer-effort confounded. What it *is* good for: a descriptive seasonal
calendar to later overlay against a station climate normal (mean temp / rain).

Writes data/registry/phenology_seasonality.json and prints a readable digest.
Usage:  python3 phenology_seasonality.py
"""
import json, os, datetime, collections

HERE = os.path.dirname(os.path.abspath(__file__))
RECS = json.load(open(os.path.join(HERE, "data", "history", "records.json")))
REG = json.load(open(os.path.join(HERE, "data", "registry", "units.json")))
OUT = os.path.join(HERE, "data", "registry", "phenology_seasonality.json")

PHASES = ("flower", "fruit", "bud")
ZH = {"flower": "開花", "fruit": "結果", "bud": "花苞"}
NAME = {u["unit_id"]: (u["common"] or "", u["scientific"]) for u in REG}

# month bins (1..12): per-phase annotation counts + total observation effort
comm = {ph: [0] * 12 for ph in PHASES}
obs_by_month = [0] * 12
sp_flower = collections.defaultdict(lambda: [0] * 12)   # unit_id -> flower count per month

for r in RECS:
    on = r.get("observed_on")
    if not on:
        continue
    m = datetime.date.fromisoformat(on).month - 1
    obs_by_month[m] += 1
    phs = (r.get("phenophase") or "").split(";")
    for ph in PHASES:
        if ph in phs:
            comm[ph][m] += 1
    if "flower" in phs:
        sp_flower[r["unit_id"]][m] += 1


def span(counts):
    """Tightest month-range covering all non-zero months (wrap-aware: the arc
    excludes the single largest gap between consecutive annotated months)."""
    ms = sorted(i + 1 for i, c in enumerate(counts) if c)
    if not ms:
        return None
    if len(ms) == 1:
        return (ms[0], ms[0])
    ext = ms + [ms[0] + 12]
    _, gi = max((ext[i + 1] - ext[i], i) for i in range(len(ms)))
    return (ms[(gi + 1) % len(ms)], ms[gi])   # start just after the largest gap


def fmt_months(counts):
    parts = [f"{i+1}月×{c}" for i, c in enumerate(counts) if c]
    return "、".join(parts) if parts else "—"


out = {
    "community": {
        "by_month": [
            {"m": i + 1,
             "flower": comm["flower"][i], "fruit": comm["fruit"][i], "bud": comm["bud"][i],
             "obs_total": obs_by_month[i]}
            for i in range(12)],
        "totals": {ph: sum(comm[ph]) for ph in PHASES},
        "note": ("Pooled across all species; observer-effort confounded. "
                 "Descriptive seasonality only, not a climate trend."),
    },
    "by_species": {},
}
for uid, mc in sorted(sp_flower.items(), key=lambda kv: -sum(kv[1])):
    n = sum(mc)
    if n < 3:                       # too sparse to describe a window
        continue
    sp = span(mc)
    out["by_species"][uid] = {
        "common": NAME[uid][0], "scientific": NAME[uid][1],
        "n_flower": n, "flower_by_month": mc,
        "flower_span": (f"{sp[0]}–{sp[1]} 月" if sp and sp[0] != sp[1]
                        else (f"{sp[0]} 月" if sp else None)),
    }

json.dump(out, open(OUT, "w"), ensure_ascii=False, indent=1)

# ── readable digest ───────────────────────────────────────────────────────────
print(f"wrote {OUT}\n")
print("社區層級 月份物候 (community phenophase by month, pooled):")
print("  月 ", " ".join(f"{i+1:>3}" for i in range(12)))
for ph in PHASES:
    print(f"  {ZH[ph]}", " ".join(f"{comm[ph][i]:>3}" for i in range(12)),
          f"  Σ={sum(comm[ph])}")
print("  obs", " ".join(f"{obs_by_month[i]:>3}" for i in range(12)),
      f"  Σ={sum(obs_by_month)}  (取樣強度 effort)")

fl = comm["flower"]
peak = max(range(12), key=lambda i: fl[i]) + 1
half = sum(fl) / 2
# central months holding the bulk of flowering
order = sorted(range(12), key=lambda i: -fl[i])
acc, core = 0, []
for i in order:
    if acc >= half:
        break
    acc += fl[i]
    core.append(i + 1)
print(f"\n開花高峰 peak month = {peak} 月；"
      f"逾半開花註記集中於 {sorted(core)} 月（共 {sum(fl)} 筆，跨 species 合計）。")
print("注意：跨物種彙整受觀察者取樣影響，僅為季節分布，非氣候趨勢。\n")

print(f"取樣較足物種的開花季 (species with ≥3 flower annotations): "
      f"{len(out['by_species'])} 種")
for uid, d in list(out["by_species"].items())[:12]:
    print(f"  {uid} {d['common']} ({d['scientific']}): "
          f"花期 {d['flower_span']}  · n={d['n_flower']}  · {fmt_months(d['flower_by_month'])}")
