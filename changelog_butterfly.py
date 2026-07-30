#!/usr/bin/env python3
"""One-line changelog for the weekly butterfly sync commit message: compares the
committed (HEAD) registry against the freshly-built working copy — new species,
observation-count changes, and totals. Mirrors changelog.py."""
import json, subprocess, os

HERE = os.path.dirname(os.path.abspath(__file__))
PATH = "data/butterfly/registry.json"


def head_version():
    r = subprocess.run(["git", "-C", HERE, "show", "HEAD:" + PATH],
                       capture_output=True, text=True)
    if r.returncode != 0 or not r.stdout.strip():
        return []
    try:
        return json.loads(r.stdout)["butterflies"]
    except Exception:
        return []


old = {b["sci"]: b for b in head_version()}
new = {b["sci"]: b for b in json.load(open(os.path.join(HERE, PATH)))["butterflies"]}

added = [b for s, b in new.items() if s not in old]
delta = sum(abs(new[s].get("count", 0) - old[s].get("count", 0)) for s in new if s in old)
total_obs = sum(b.get("count", 0) for b in new.values())

parts = [f"新增蝶種 {len(added)}"]
if added:
    parts.append("（" + "、".join(b.get("zh") or b["sci"] for b in added[:5])
                 + ("…" if len(added) > 5 else "") + "）")
parts.append(f"觀察數異動 {delta}")
print(" · ".join(parts) + f"（總計 {len(new)} 蝶種 / {total_obs} 筆觀察）")
