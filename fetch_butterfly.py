#!/usr/bin/env python3
"""Weekly butterfly sync — fully automatic, no manual step.

1. Pull per-species observation counts of Papilionoidea (taxon 47224) recorded at
   二格山 (place_id 130869, all observers) and update each curated butterfly's
   `count` (the set of present species + counts is the only thing iNat supplies).
2. For any species NOT yet in the registry, append it AND resolve its larval host
   plants automatically: GloBI (host-plant interactions) → TaiCoL (Taiwan-accepted
   name + 中文 科/屬 + 特有/保育). The host `sp` list and the network structures
   (edges_bf_fam / fam_nodes / pgenus / gg_edges / bgenus) are extended from that,
   flagged `hostsrc:"GloBI"` to keep provenance distinct from the book-curated set.

The curated 97-species 《臺灣蝶類誌》 network is never modified — new species only
*extend* it. Anything GloBI/TaiCoL can't resolve leaves the species `host_pending`
(empty hosts) to retry next week; nothing is ever fabricated. Curated species are
never deleted, and a species missing from a run keeps its count (partial fetch is
non-destructive). Run `build_butterfly.py` afterwards to re-inline the registry.

Pure stdlib + curl — mirrors backfill.py / taicol.py."""
import json, os, time, urllib.request, urllib.parse
import globi, taicol

HERE = os.path.dirname(os.path.abspath(__file__))
REG = os.path.join(HERE, "data", "butterfly", "registry.json")
# Book-curated 《臺灣蝶類誌》 host cache from the sibling `update-erge-papilionoidea`
# skill — the canonical origin of this page. Soft-reused (like taicol.py reuses the
# update-erge-phenology cache): preferred over GloBI when present, no-ops when absent
# (e.g. in CI). Shape: {"<butterfly binomial>": ["<host binomial>", ...]}.
SKILL_HOSTS = os.path.expanduser("~/.claude/skills/update-erge-papilionoidea/hosts_book.json")
PLACE = "130869"
TAXON = "47224"          # Papilionoidea superfamily (see papilionoidea.html footer)
FAMORDER = ["鳳蝶科", "粉蝶科", "弄蝶科", "蛺蝶科", "灰蝶科", "蜆蝶科"]
UA = {"User-Agent": "erge-iNAT butterfly sync (github.com/bunnytailgra22/erge-iNAT)"}


def book_hosts(sci):
    """《臺灣蝶類誌》 host binomials for a butterfly, from the update-erge-papilionoidea
    skill cache when installed locally; [] otherwise. Book is the gold standard, so
    it is tried before GloBI."""
    try:
        return json.load(open(SKILL_HOSTS)).get(sci, []) or []
    except Exception:
        return []


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
    """Family (中文), genus (Latin) and genus (中文) for a newly-seen butterfly,
    read from its iNat taxon ancestors."""
    fam_zh = gen = genzh = ""
    try:
        d = get(f"https://api.inaturalist.org/v1/taxa/{taxon_id}?locale=zh-TW")
        anc = (d["results"][0].get("ancestors") or []) if d.get("results") else []
        for t in anc:
            if t.get("rank") == "family":
                fam_zh = t.get("preferred_common_name") or t.get("name") or ""
            elif t.get("rank") == "genus":
                gen = t.get("name") or ""
                genzh = t.get("preferred_common_name") or ""
    except Exception as e:
        print(f"  ! enrich failed for taxon {taxon_id}: {e}")
    return fam_zh, gen, genzh


def resolve_hosts(entry, data, seed):
    """Fill entry['sp'] from GloBI host plants enriched through TaiCoL, and extend
    the derived network structures in `data`. Returns the number of hosts resolved.
    Only Taiwan-resolved hosts (TaiCoL family known) are kept; the rest are dropped."""
    fam_nodes = {f["zh"]: f for f in data["fam_nodes"]}
    pgenus = {g["zh"]: g for g in data["pgenus"]}
    bgenus = {g["gen"]: g for g in data["bgenus"]}
    gg_seen = {(e[0], e[1]) for e in data["gg_edges"]}

    # 《臺灣蝶類誌》 (skill cache) is the gold standard; GloBI fills in when it's absent.
    book = book_hosts(entry["sci"])
    hosts, host_src = (book, "臺灣蝶類誌") if book else (globi.host_species(entry["sci"]), "GloBI")

    sp, seen, bf_fams, plant_gen_zh = [], set(), set(), set()
    endemic, conserv = [], []
    for host in hosts:
        tx = taicol.resolve(host, None, seed)
        fam_zh = tx.get("fam_zh")
        if tx["src"] == "unresolved" or not fam_zh:
            continue                                  # not in Taiwan flora / unresolved
        sci = tx.get("accepted_sci") or host
        if sci in seen:
            continue
        seen.add(sci)
        zh, threat = tx.get("accepted_zh") or "", tx.get("threat")
        sp.append({"zh": zh, "sci": sci, "fam": fam_zh,
                   "end": bool(tx.get("is_endemic")), "cons": threat})
        if tx.get("is_endemic") and zh:
            endemic.append(zh)
        if threat and zh:
            conserv.append(zh)
        bf_fams.add(fam_zh)
        if fam_zh not in fam_nodes and tx.get("fam_sci"):
            fam_nodes[fam_zh] = {"zh": fam_zh, "sci": tx["fam_sci"]}
            data["fam_nodes"].append(fam_nodes[fam_zh])
        gen_zh, gen_sci = tx.get("gen_zh"), tx.get("gen_sci") or sci.split(" ")[0]
        if gen_zh:
            plant_gen_zh.add(gen_zh)
            if gen_zh not in pgenus:
                pgenus[gen_zh] = {"zh": gen_zh, "sci": gen_sci}
                data["pgenus"].append(pgenus[gen_zh])

    entry["sp"] = sp
    entry["nfam"] = len(bf_fams)
    entry["endemic"] = sorted(set(endemic))
    entry["conserv"] = sorted(set(conserv))
    entry["hostsrc"] = host_src if sp else entry.get("hostsrc", "")
    entry["host_pending"] = not sp

    for f in sorted(bf_fams):
        data["edges_bf_fam"].append([entry["id"], f])
    bgen = entry.get("gen")
    if bgen:
        if bgen not in bgenus:
            bgenus[bgen] = {"gen": bgen, "zh": entry.get("genzh", ""),
                            "fam": entry.get("fam", ""), "famo": entry.get("famo")}
            data["bgenus"].append(bgenus[bgen])
        for gz in sorted(plant_gen_zh):
            if (bgen, gz) not in gg_seen:
                data["gg_edges"].append([bgen, gz, ""])
                gg_seen.add((bgen, gz))
    return len(sp)


def main():
    data = json.load(open(REG))
    bfs = data["butterflies"]
    by_sci = {b["sci"]: b for b in bfs}
    next_id = max((int(b["id"][1:]) for b in bfs if b["id"][1:].isdigit()), default=-1) + 1
    seed = taicol.load_seed()

    counts = fetch_species_counts()
    print(f"iNat species_counts (Papilionoidea @ {PLACE}, all observers): "
          f"{len(counts)} species, {sum(c['count'] for c in counts.values())} obs")

    updated = added = 0
    new_entries = []
    for sci, info in counts.items():
        b = by_sci.get(sci)
        if b is not None:
            if b.get("count") != info["count"]:
                updated += 1
            b["count"] = info["count"]
        else:
            fam_zh, gen, genzh = enrich_new(info["taxon_id"])
            entry = {
                "id": f"b{next_id}", "zh": info["common"] or sci, "alias": "",
                "zhlist": "", "zhsrc": "iNaturalist", "sci": sci,
                "gen": gen, "genzh": genzh, "fam": fam_zh,
                "famo": FAMORDER.index(fam_zh) if fam_zh in FAMORDER else len(FAMORDER),
                "count": info["count"], "nfam": 0, "sp": [],
                "endemic": [], "conserv": [], "host_pending": True, "hostsrc": "",
            }
            bfs.append(entry)
            by_sci[sci] = entry
            new_entries.append(entry)
            next_id += 1
            added += 1

    # resolve host plants for new species + retry any earlier host_pending ones
    for entry in bfs:
        if entry.get("host_pending") and not entry.get("sp"):
            n = resolve_hosts(entry, data, seed)
            tag = "新增" if entry in new_entries else "重試"
            state = f"{n} 寄主" if n else "寄主待補（GloBI/TaiCoL 無解析）"
            print(f"  {'+' if entry in new_entries else '~'} {tag}蝶種 {entry['zh']} "
                  f"({entry['sci']}) {entry.get('fam') or '科未定'} · iNat {entry['count']} 筆 · {state}")

    bfs.sort(key=lambda b: (b.get("famo", len(FAMORDER)), b.get("gen", ""), b.get("sci", "")))
    json.dump(data, open(REG, "w"), ensure_ascii=False, indent=2)
    print(f"registry updated: {updated} count change(s), {added} new species, "
          f"{len(bfs)} total.")


if __name__ == "__main__":
    main()
