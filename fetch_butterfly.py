#!/usr/bin/env python3
"""Weekly butterfly sync (iNat side only).

Pulls per-species observation counts of Papilionoidea (taxon 47224) recorded at
二格山 (place_id 130869, all observers) and folds them into the curated registry
`data/butterfly/registry.json`:

  * updates each curated butterfly's `count` (iNat observations of that species);
  * appends any species NOT yet in the registry as a new entry with an EMPTY
    host-plant list flagged `host_pending` (寄主待補) — its 《臺灣蝶類誌》 host
    plants are added by hand later. Family (中文) and genus (Latin) are enriched
    from the iNat taxon ancestors so it slots into the right 蝶科.

The host-plant network (fam_nodes / edges_bf_fam / gg_edges / bgenus / pgenus) is
book+TaiCoL-derived and is never touched here. Curated species are never deleted;
a species the API doesn't return this run keeps its existing count (so a partial
fetch can't destructively zero the data). Run `build_butterfly.py` afterwards to
re-inline the registry into papilionoidea.html.

Pure stdlib, no deps — mirrors backfill.py / fetch_inat.py."""
import json, os, time, urllib.request, urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
REG = os.path.join(HERE, "data", "butterfly", "registry.json")
PLACE = "130869"
TAXON = "47224"          # Papilionoidea superfamily (see papilionoidea.html footer)
FAMORDER = ["鳳蝶科", "粉蝶科", "弄蝶科", "蛺蝶科", "灰蝶科", "蜆蝶科"]
UA = {"User-Agent": "erge-iNAT butterfly sync (github.com/bunnytailgra22/erge-iNAT)"}


def get(url):
    return json.load(urllib.request.urlopen(urllib.request.Request(url, headers=UA)))


def binomial(name):
    """Roll a subspecies trinomial up to its species binomial; leave others as-is."""
    parts = (name or "").split()
    return " ".join(parts[:2]) if len(parts) >= 2 else name


def fetch_species_counts():
    """Species-level obs counts for Papilionoidea at the site, aggregated to binomial."""
    agg, page = {}, 1
    while True:
        params = {"place_id": PLACE, "taxon_id": TAXON, "locale": "zh-TW",
                  "per_page": "200", "page": str(page)}
        d = get("https://api.inaturalist.org/v1/observations/species_counts?"
                + urllib.parse.urlencode(params))
        for r in d["results"]:
            tx = r.get("taxon") or {}
            if tx.get("rank") not in ("species", "subspecies", "hybrid"):
                continue                      # skip genus/family-level (no binomial)
            sci = binomial(tx.get("name", ""))
            if not sci:
                continue
            a = agg.setdefault(sci, {"count": 0, "taxon_id": tx.get("id"),
                                     "common": tx.get("preferred_common_name") or ""})
            a["count"] += r.get("count", 0)
            if tx.get("rank") == "species":   # prefer the species-rank taxon id/name
                a["taxon_id"] = tx.get("id")
                a["common"] = tx.get("preferred_common_name") or a["common"]
        if page * 200 >= d["total_results"] or not d["results"]:
            break
        page += 1
        time.sleep(1)
    return agg


def enrich_new(taxon_id):
    """Family (中文) + genus (Latin) for a newly-seen species, from taxon ancestors."""
    fam_zh = gen = ""
    try:
        d = get(f"https://api.inaturalist.org/v1/taxa/{taxon_id}?locale=zh-TW")
        anc = (d["results"][0].get("ancestors") or []) if d.get("results") else []
        for t in anc:
            if t.get("rank") == "family":
                fam_zh = t.get("preferred_common_name") or t.get("name") or ""
            elif t.get("rank") == "genus":
                gen = t.get("name") or ""
    except Exception as e:
        print(f"  ! enrich failed for taxon {taxon_id}: {e}")
    return fam_zh, gen


def main():
    data = json.load(open(REG))
    bfs = data["butterflies"]
    by_sci = {b["sci"]: b for b in bfs}
    next_id = max((int(b["id"][1:]) for b in bfs if b["id"][1:].isdigit()), default=-1) + 1

    counts = fetch_species_counts()
    print(f"iNat species_counts (Papilionoidea @ {PLACE}, all observers): "
          f"{len(counts)} species, {sum(c['count'] for c in counts.values())} obs")

    updated = added = 0
    for sci, info in counts.items():
        b = by_sci.get(sci)
        if b is not None:
            if b.get("count") != info["count"]:
                updated += 1
            b["count"] = info["count"]
        else:
            fam_zh, gen = enrich_new(info["taxon_id"])
            entry = {
                "id": f"b{next_id}", "zh": info["common"] or sci, "alias": "",
                "zhlist": "", "zhsrc": "iNaturalist", "sci": sci,
                "gen": gen, "genzh": "", "fam": fam_zh,
                "famo": FAMORDER.index(fam_zh) if fam_zh in FAMORDER else len(FAMORDER),
                "count": info["count"], "nfam": 0, "sp": [],
                "endemic": [], "conserv": [], "host_pending": True,
            }
            bfs.append(entry)
            by_sci[sci] = entry
            next_id += 1
            added += 1
            print(f"  + 新增蝶種 {entry['zh']} ({sci}) {fam_zh or '科未定'} · iNat {info['count']} 筆 · 寄主待補")

    bfs.sort(key=lambda b: (b.get("famo", len(FAMORDER)), b.get("gen", ""), b.get("sci", "")))
    json.dump(data, open(REG, "w"), ensure_ascii=False, indent=2)
    print(f"registry updated: {updated} count change(s), {added} new species, "
          f"{len(bfs)} total.")


if __name__ == "__main__":
    main()
