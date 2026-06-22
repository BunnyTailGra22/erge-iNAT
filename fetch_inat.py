#!/usr/bin/env python3
"""Retrieve bunnytailgrass's observations at 二格山 (place_id 130869) from the
iNaturalist API for a given survey day, and save raw JSON + a flattened,
family-enriched CSV for analysis.

Usage:
    python3 fetch_inat.py 2026-04-25                        # one survey day
    python3 fetch_inat.py 2026-04-25 "2026/04/25 · 14:41 CST"   # + snapshot label
    python3 fetch_inat.py                                   # defaults to example day

Outputs land in   data/<date>/observations_raw.json + observations.csv + metadata.json
The snapshot label pins which mutable iNat state this dataset represents; if omitted
it defaults to the retrieval time.
"""
import json, time, urllib.request, urllib.parse, csv, os, sys, datetime, collections
from datetime import timezone, timedelta

TW = timezone(timedelta(hours=8))   # Taiwan / CST (UTC+8)

BASE = "https://api.inaturalist.org/v1/observations"
TAXA = "https://api.inaturalist.org/v1/taxa/"
USER = "bunnytailgrass"
PLACE_ID = "130869"          # 二格山, NT, TW
HERE = os.path.dirname(os.path.abspath(__file__))

# iNat Plant Phenology controlled term (attribute 12) value map
PHENO = {13: "Flowering 開花", 14: "Fruiting 結果",
         15: "Flower Budding 花苞", 21: "No Evidence of Flowering 無花果"}


def fetch_all(date):
    params = {
        "user_login": USER, "observed_on": date, "place_id": PLACE_ID,
        "per_page": "200", "order_by": "id", "order": "asc",
        "locale": "zh-TW", "preferred_place_id": PLACE_ID,
    }
    results, page = [], 1
    while True:
        url = BASE + "?" + urllib.parse.urlencode(dict(params, page=str(page)))
        with urllib.request.urlopen(url) as r:
            d = json.load(r)
        results.extend(d["results"])
        if len(results) >= d["total_results"] or not d["results"]:
            break
        page += 1
        time.sleep(1)
    return results


def family_map(taxon_ids):
    """Family is not embedded in observations -> enrich via /taxa (batch <=30)."""
    fam = {}
    ids = sorted(taxon_ids)
    for i in range(0, len(ids), 30):
        batch = ids[i:i + 30]
        url = TAXA + ",".join(map(str, batch)) + "?locale=zh-TW"
        d = json.load(urllib.request.urlopen(url))
        for t in d["results"]:
            f = ""
            for a in t.get("ancestors", []) or []:
                if a.get("rank") == "family":
                    f = a.get("name", "")
            fam[t["id"]] = f
        time.sleep(1)
    return fam


def flatten(o, fam):
    t = o.get("taxon") or {}
    phenos = [PHENO.get(a.get("controlled_value_id"), str(a.get("controlled_value_id")))
              for a in (o.get("annotations") or [])
              if a.get("controlled_attribute_id") == 12]
    loc = (o.get("geojson") or {}).get("coordinates") or [None, None]
    photos = [(p.get("photo") or p).get("url", "").replace("square", "medium")
              for p in (o.get("photos") or [])]
    return {
        "id": o.get("id"), "uri": o.get("uri"),
        "observed_on": o.get("observed_on"), "time_observed_at": o.get("time_observed_at"),
        "scientific_name": t.get("name"), "common_name": t.get("preferred_common_name"),
        "rank": t.get("rank"), "taxon_id": t.get("id"),
        "iconic_taxon": t.get("iconic_taxon_name"), "family": fam.get(t.get("id"), ""),
        "quality_grade": o.get("quality_grade"),
        "identifications_count": o.get("identifications_count"),
        "num_agreements": o.get("num_identification_agreements"),
        "phenology": "; ".join(phenos),
        "lat": loc[1] if len(loc) == 2 else None,
        "lng": loc[0] if len(loc) == 2 else None,
        "positional_accuracy": o.get("positional_accuracy"),
        "place_guess": o.get("place_guess"),
        "photo_count": len(photos), "first_photo": photos[0] if photos else "",
    }


def write_metadata(out, date, rows, obs, snapshot_label):
    def tw(s):
        return datetime.datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(TW)
    oss = sorted(tw(o["time_observed_at"]) for o in obs if o.get("time_observed_at"))
    ups = sorted(tw(o["created_at"]) for o in obs if o.get("created_at"))
    qg = collections.Counter(r["quality_grade"] for r in rows)
    meta = {
        "survey": "二格山 長期定點調查 (iNAT in Erge)",
        "observer": USER, "place": "二格山, NT, TW", "place_id": int(PLACE_ID),
        "observed_on": date,
        "snapshot_label": snapshot_label,
        "data_retrieved_at": datetime.datetime.now(TW).strftime("%Y-%m-%dT%H:%M:%S+08:00"),
        "source": "iNaturalist API v1 /observations",
        "query": {"user_login": USER, "observed_on": date, "place_id": int(PLACE_ID)},
        "totals": {"observations": len(rows),
                   "species": len({r["taxon_id"] for r in rows}),
                   "families": len({r["family"] for r in rows if r["family"]}),
                   "research_grade": qg.get("research", 0),
                   "needs_id": qg.get("needs_id", 0)},
        "observation_time_window_cst": f"{oss[0]:%H:%M}–{oss[-1]:%H:%M}" if oss else None,
        "upload_time_window_cst": f"{ups[0]:%H:%M}–{ups[-1]:%H:%M}" if ups else None,
        "note": ("Snapshot pins the mutable iNat state this dataset represents "
                 "(needs_id records may later reach research grade); baseline "
                 "target sample for the long-term site survey."),
    }
    json.dump(meta, open(os.path.join(out, "metadata.json"), "w"),
              ensure_ascii=False, indent=2)


def main():
    date = sys.argv[1] if len(sys.argv) > 1 else "2026-04-25"
    snapshot_label = (sys.argv[2] if len(sys.argv) > 2
                      else datetime.datetime.now(TW).strftime("%Y/%m/%d · %H:%M CST"))
    out = os.path.join(HERE, "data", date)
    os.makedirs(out, exist_ok=True)
    obs = fetch_all(date)
    if not obs:
        print(f"No observations for {USER} at place {PLACE_ID} on {date}.")
        return
    with open(os.path.join(out, "observations_raw.json"), "w") as f:
        json.dump(obs, f, ensure_ascii=False, indent=2)
    fam = family_map({o["taxon"]["id"] for o in obs if o.get("taxon")})
    rows = [flatten(o, fam) for o in obs]
    with open(os.path.join(out, "observations.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    write_metadata(out, date, rows, obs, snapshot_label)
    nsp = len({r["taxon_id"] for r in rows})
    print(f"{date}: saved {len(obs)} observations / {nsp} species "
          f"(snapshot {snapshot_label}) -> {out}")


if __name__ == "__main__":
    main()
