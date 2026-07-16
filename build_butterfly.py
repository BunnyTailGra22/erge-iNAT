#!/usr/bin/env python3
"""Re-inline data/butterfly/registry.json into papilionoidea.html.

The butterfly page is self-contained: its whole dataset lives in a single
`const DATA={...};` line. The host-plant network (fam_nodes / edges_bf_fam /
gg_edges / bgenus / pgenus) is book+TaiCoL-derived and never changes on a sync;
only each butterfly's iNat `count` and the set of present species do (updated by
fetch_butterfly.py). This script recomputes `meta` from the data, then rewrites
just that one DATA line — the surrounding template is left untouched.

Serialisation matches the original inlined compact JSON, so a round-trip with no
data change produces a byte-identical papilionoidea.html (no spurious diff)."""
import json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
REG = os.path.join(HERE, "data", "butterfly", "registry.json")
HTML = os.path.join(HERE, "papilionoidea.html")


def recompute_meta(data):
    """meta drives the footer summary; derive it from the data so it can't drift."""
    data["meta"] = {
        "n_bf": len(data["butterflies"]),
        "n_fam": len(data["fam_nodes"]),
        "n_bgen": len(data["bgenus"]),
        "n_pgen": len(data["pgenus"]),
    }
    return data


def main():
    data = recompute_meta(json.load(open(REG)))
    compact = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    html = open(HTML).read()
    new, n = re.subn(r"const DATA=\{.*?\};\nconst FAMCOL",
                     "const DATA=" + compact + ";\nconst FAMCOL", html, count=1, flags=re.S)
    if n != 1:
        raise SystemExit("could not locate the `const DATA=...;` line in papilionoidea.html")
    if new != html:
        open(HTML, "w").write(new)
        print(f"papilionoidea.html rebuilt — {data['meta']['n_bf']} 蝶種, {data['meta']['n_fam']} 寄主科")
    else:
        print("papilionoidea.html already up to date (no data change)")


if __name__ == "__main__":
    main()
