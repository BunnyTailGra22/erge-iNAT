#!/usr/bin/env python3
"""Print a one-line changelog comparing the committed (HEAD) records.json against
the freshly-built working copy: new / removed / re-identified / quality-changed /
newly-phenology-annotated counts. Used in the daily-sync commit message."""
import json, subprocess, os

HERE = os.path.dirname(os.path.abspath(__file__))
PATH = "data/history/records.json"


def head_version():
    r = subprocess.run(["git", "-C", HERE, "show", "HEAD:" + PATH],
                       capture_output=True, text=True)
    if r.returncode != 0 or not r.stdout.strip():
        return []
    try:
        return json.loads(r.stdout)
    except Exception:
        return []


old = {str(r["obs_id"]): r for r in head_version()}
new = {str(r["obs_id"]): r for r in json.load(open(os.path.join(HERE, PATH)))}

added = [k for k in new if k not in old]
removed = [k for k in old if k not in new]
reid = [k for k in new if k in old and new[k].get("taxon_id") != old[k].get("taxon_id")]
qual = [k for k in new if k in old and new[k].get("quality") != old[k].get("quality")]
newph = [k for k in new if k in old and not old[k].get("phenophase") and new[k].get("phenophase")]
observers = len({r.get("user") for r in new.values() if r.get("user")})

parts = [f"新增 {len(added)}"]
if removed:
    parts.append(f"移除 {len(removed)}")
if reid:
    parts.append(f"重新鑑定 {len(reid)}")
if qual:
    parts.append(f"品質變更 {len(qual)}")
parts.append(f"新物候註記 {len(newph)}")
print(" · ".join(parts) + f"（總計 {len(new)} 筆 / {observers} 觀察者）")
