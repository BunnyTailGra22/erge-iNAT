#!/usr/bin/env bash
# rebuild_after_vision.sh
# Rebuild all phenology pages after an AI vision backfill (ai_flower.py).
#
# Run this AFTER `ai_flower.py --all --skip-annotated` has updated
# data/phenophase/ai_flower.json. It rebuilds the per-unit timeline pages and
# the transect index so the new "AI 建議開花" layer shows up, prints a summary
# of what changed, and (after you confirm) commits + pushes so GitHub Pages
# redeploys.
#
# It deliberately does NOT run backfill.py: that re-pulls iNat data and could
# change records.json out from under the vision results. This is a pure rebuild
# from the data already on disk.
#
# Usage:
#   ./rebuild_after_vision.sh        # rebuild, summarise, ask before commit/push
#   ./rebuild_after_vision.sh -y     # rebuild + commit + push without prompting

set -euo pipefail
cd "$(dirname "$0")"

AUTO_YES=0
if [ "${1:-}" = "-y" ]; then AUTO_YES=1; fi

AI_JSON="data/phenophase/ai_flower.json"
if [ ! -f "$AI_JSON" ]; then
  echo "ERROR: $AI_JSON not found — run ai_flower.py first." >&2
  exit 1
fi

echo "==> AI cache: $(python3 -c "import json;print(len(json.load(open('$AI_JSON'))))") observations classified"

echo "==> Refreshing per-sample insight digest (insights.py) …"
python3 insights.py

echo "==> Rebuilding per-unit timeline pages (build_unit_page.py --all) …"
python3 build_unit_page.py --all

echo "==> Rebuilding transect index (build_transect_html.py) …"
python3 build_transect_html.py

# Summary: how many AI-suggested flowerings will actually surface on the pages
# (confidence >= 0.5 AND iNat hasn't already annotated that obs as flowering) —
# mirrors the gate in build_unit_page.py.
python3 - <<'PY'
import json
recs = json.load(open("data/history/records.json"))
ai   = json.load(open("data/phenophase/ai_flower.json"))
ph   = {str(r["obs_id"]): (r.get("phenophase") or "") for r in recs}
unit = {str(r["obs_id"]): r["unit_id"] for r in recs}
flowering = [o for o, v in ai.items() if v.get("flower")]
surfaced  = [o for o in flowering
             if ai[o].get("confidence", 0) >= 0.5 and "flower" not in ph.get(o, "")]
units = sorted({unit[o] for o in surfaced if o in unit})
print(f"==> {len(ai)} obs classified · {len(flowering)} flowering · "
      f"{len(surfaced)} newly surfaced (conf>=0.5, iNat-unmarked) across {len(units)} units")
PY

echo "==> Staging changes …"
git add -A
git diff --cached --stat || true

if git diff --cached --quiet; then
  echo "==> No changes to commit — pages already up to date."
  exit 0
fi

if [ "$AUTO_YES" -ne 1 ]; then
  printf "==> Commit and push to deploy? [y/N] "
  read -r ans
  case "$ans" in
    [yY]*) ;;
    *) echo "Left staged, not committed. Review with: git diff --cached"; exit 0;;
  esac
fi

N=$(python3 -c "import json;print(len(json.load(open('$AI_JSON'))))")
git commit -m "AI flower-suggestion vision backfill (${N} obs)" \
           -m "Rebuilt all unit pages + transect with the AI 開花 layer from ai_flower.json." \
           -m "Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
git push
echo "==> Pushed. GitHub Pages will redeploy in ~1 min."
