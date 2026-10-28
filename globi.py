#!/usr/bin/env python3
"""Larval host plants for a butterfly, from GloBI (Global Biotic Interactions,
https://api.globalbioticinteractions.org) — the machine-readable aggregator that
includes the NHM "HOSTS – a Database of the World's Lepidopteran Hostplants".

iNaturalist has no host-plant data, so this is what lets the weekly sync fill a
newly-seen butterfly's hosts automatically instead of by hand. Returns species-
level plant names only; Taiwan-localisation + 中文 names come later via TaiCoL.

Degrades safely: any network / shape problem yields [] (the species just stays
`host_pending`) — it never invents hosts. Pure stdlib + curl, like taicol.py."""
import json, subprocess, urllib.parse

BASE = "https://api.globalbioticinteractions.org/interaction"
# herbivory / host relations a lepidopteran larva has with its food plant
INTERACTIONS = ["eats", "hasHost", "interactsWith"]


def _curl(url):
    return subprocess.run(["curl", "-s", "--max-time", "30", "-H",
                           "User-Agent: erge-inat/1.0", url], capture_output=True, text=True).stdout


def _is_binomial(name):
    """True for 'Genus species' (or a trinomial we can trim); False for bare genus/family."""
    p = (name or "").split()
    return len(p) >= 2 and p[0][:1].isupper() and p[1][:1].islower()


def host_species(sci):
    """Unique Taiwan-agnostic plant binomials GloBI records as hosts of `sci`.
    Roll subspecies up to the binomial; drop genus/family-only records."""
    found = set()
    for itype in INTERACTIONS:
        q = urllib.parse.urlencode({"sourceTaxon": sci, "interactionType": itype,
                                    "targetTaxon": "Plantae", "fields": "target_taxon_name"})
        try:
            d = json.loads(_curl(BASE + "?" + q) or "{}")
        except Exception:
            continue
        for row in d.get("data", []):
            name = (row[0] if row else "").strip()
            if _is_binomial(name):
                found.add(" ".join(name.split()[:2]))
    return sorted(found)


if __name__ == "__main__":   # manual probe: python3 globi.py "Papilio polytes"
    import sys
    for h in host_species(sys.argv[1] if len(sys.argv) > 1 else "Papilio polytes"):
        print(h)
