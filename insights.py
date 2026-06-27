#!/usr/bin/env python3
"""Per-sample insight digest for the 93 ridgeline units.

Reads the registry + history store + TaiCoL, and for every ERG-* sample derives a
conservative, data-grounded summary:
  * phenophase windows  — months in which iNat term-12 annotations record
    開花/結果/花苞, WITH the underlying counts (no fabricated curve);
  * sampling depth       — n observations / years / observers / span;
  * GPS proximity        — share of located obs within 50 m of the sample point;
  * conservation         — 臺灣特有 / IUCN / 紅皮書 from TaiCoL;
  * a one-line Chinese insight sentence (used on each unit page).

Phenology claims stay honest: where annotations are too few we say 不足/尚無 rather
than infer a window. iNat annotations remain the phenophase source of truth.

Writes data/registry/insights.json  (keyed by unit_id).
Usage:  python3 insights.py
"""
import json, os, datetime, collections

HERE = os.path.dirname(os.path.abspath(__file__))
REG = json.load(open(os.path.join(HERE, "data", "registry", "units.json")))
RECS = json.load(open(os.path.join(HERE, "data", "history", "records.json")))
TX = json.load(open(os.path.join(HERE, "data", "registry", "taxa_taicol.json")))
OUT = os.path.join(HERE, "data", "registry", "insights.json")

PHASES = ("flower", "fruit", "bud")
ZH = {"flower": "開花", "fruit": "結果", "bud": "花苞"}

BYUNIT = collections.defaultdict(list)
for r in RECS:
    if r.get("observed_on"):
        BYUNIT[r["unit_id"]].append(r)


def fmt_months(ms):
    """Compact a set of month numbers: contiguous -> '3–5 月', else '3、5、7 月'."""
    ms = sorted(set(ms))
    if not ms:
        return ""
    if len(ms) >= 2 and ms == list(range(ms[0], ms[-1] + 1)):
        return f"{ms[0]}–{ms[-1]} 月"
    return "、".join(str(m) for m in ms) + " 月"


def digest(unit):
    uid = unit["unit_id"]
    rows = BYUNIT.get(uid, [])
    nobs = len(rows)
    years = sorted({datetime.date.fromisoformat(r["observed_on"]).year for r in rows})
    observers = len({r["user"] for r in rows if r.get("user")})

    # phenophase months per phase, from iNat annotations only
    pheno = {}
    for ph in PHASES:
        months = [datetime.date.fromisoformat(r["observed_on"]).month
                  for r in rows if ph in (r.get("phenophase") or "").split(";")]
        if months:
            pheno[ph] = {"n": len(months), "months": sorted(set(months))}

    # GPS proximity — of obs with a known distance, how many sit within 50 m
    located = [r["dist_to_unit_m"] for r in rows if r.get("dist_to_unit_m") is not None]
    near50 = sum(1 for d in located if d <= 50)
    near50_pct = round(100 * near50 / len(located)) if located else None

    e = TX.get(unit["scientific"], {})
    threat = e.get("threat")

    d = {
        "scientific": unit["scientific"],
        "common": unit["common"] or "",
        "fam_zh": e.get("fam_zh") or (unit["family_zh"] or ""),
        "fam_sci": e.get("fam_sci") or unit["family"],
        "nobs": nobs,
        "nyears": len(years),
        "y0": years[0] if years else None,
        "y1": years[-1] if years else None,
        "observers": observers,
        "near50": near50,
        "located": len(located),
        "near50_pct": near50_pct,
        "pheno": pheno,
        "endemic": bool(e.get("is_endemic")),
        "iucn": e.get("iucn"),
        "threat": threat,
        "protected": e.get("protected"),
    }

    # one-line, conservative insight sentence
    if nobs == 0:
        d["insight"] = "尚無歷史觀察，後續每日同步將累積。"
        return d
    if pheno:
        parts = [f"{ZH[ph]} {fmt_months(pheno[ph]['months'])}（n={pheno[ph]['n']}）"
                 for ph in PHASES if ph in pheno]
        d["insight"] = "；".join(parts) + "。其餘為僅照片觀察、葉/花/果待判讀。"
    else:
        d["insight"] = (f"目前 {nobs} 筆觀察尚無 iNat 物候標記，"
                        "待標記累積後方能判斷花/果期。")
    return d


def main():
    out = {u["unit_id"]: digest(u) for u in REG}
    json.dump(out, open(OUT, "w"), ensure_ascii=False, indent=1)
    n_pheno = sum(1 for d in out.values() if d["pheno"])
    n_end = sum(1 for d in out.values() if d["endemic"])
    n_thr = sum(1 for d in out.values() if d["threat"])
    print(f"wrote {len(out)} sample insights -> {OUT}")
    print(f"  {n_pheno} samples with iNat phenophase annotations · "
          f"{n_end} 臺灣特有 · {n_thr} IUCN/紅皮書")


if __name__ == "__main__":
    main()
