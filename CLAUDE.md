# iNAT in Erge — 二格山稜線長期定點植物調查

Visualising iNaturalist plant observations along the 二格山 (Mt. Erge) ridgeline trail
(New Taipei, Taiwan) for the Society of Wilderness (荒野保護協會, SOW).

Live site (GitHub Pages): https://bunnytailgra22.github.io/erge-iNAT/

## Project scope (3 items)
1. **Identify the ridgeline samples** — DONE for the 2026-04-25 baseline.
2. **Collect historical iNat observations** — GPS quality is the expected bottleneck.
3. **Analyse trend / phenology from photos** — future.

## Architecture / pipeline
Run the scripts in order from the project root; each writes into `data/<survey-date>/`.

| Script | Does | Key outputs |
|---|---|---|
| `fetch_inat.py [YYYY-MM-DD] ["snapshot label"]` | Pull observations from the iNat API for one survey day; enrich family (Latin) via `/taxa`; stamp a snapshot. | `observations_raw.json`, `observations.csv`, `metadata.json` |
| `build_profile.py` | Scope to the ridgeline; **GPS-correct** unreliable fixes; sample SRTM elevation; compute along-trail distance; enrich photo + 中文科名. | `profile_before_1456.json`, `profile_enriched.json` |
| `build_transect_html.py` | Render the self-contained transect page + summary cards + 科/屬 filters. | `data/.../transect_2026-04-25.html`, **`index.html`** (Pages entry) |

`index.html` is the published transect (served by GitHub Pages from repo root).

## Data source (iNaturalist API)
- Endpoint `https://api.inaturalist.org/v1/observations`
- `user_login=bunnytailgrass`, `place_id=130869` (二格山, NT, TW), `observed_on=<date>`, `locale=zh-TW`
- Family is **not** embedded — enrich via `/v1/taxa/<ids>` reading `ancestors[rank=family]`.
- Elevation is **not** in iNat — sampled from SRTM 30 m (Open Topo Data, bilinear).

## Key decisions
- **Ridgeline scope = observations before 14:56 CST, minus the first two trailhead points**
  (93 obs / 63 species; excluded IDs 353345277, 353345653 via `EXCLUDE_IDS` in build_profile.py). The real off-crest
  descent begins at the 14:56 time-gap, not the earlier 14:37:27 trial cutoff (DEM-confirmed:
  crest ~645 m, roadside herbs after 14:56 drop 584→502 m and are excluded).
- **GPS handling**: any fix with `positional_accuracy > 100 m` (6 points, incl. the displaced
  #27 *Prunus phaeosticta* at 1594 m) is unreliable in position AND in the DEM elevation sampled
  there. Each is **snapped to the time-interpolated position between its nearest reliable
  neighbours**, then elevation re-sampled and distance recomputed. This removed artificial
  elevation dips and ~230 m of spurious back-and-forth distance (true trail ≈ 636 m, not 870 m).
- **Snapshot pinning**: iNat IDs are mutable (needs_id → research-grade over time); datasets are
  pinned to a snapshot label (baseline `2026/04/25 · 14:41 CST`) recorded in `metadata.json`.
- **Visualization** = elevation transect (x = along-trail distance, y = elevation). The full
  南仁山-style 圖18 vegetation profile with 優勢單位 is **deferred** — it needs measured 優勢度
  (quadrat / point-intercept) + canopy height; iNat walk data is presence-only, so do NOT
  fabricate dominance from encounter frequency.

## Conventions
- **Brand palette = 荒野保護協會 (SOW)**; tokens in `SOW/brand/` (`sow_palette.css/json`).
  research = 荒野綠 `#587A30`, needs-ID = 荒野綠2 `#90B821`, terrain/grid = 荒野灰 `#666666`/`#B2B2B2`,
  GPS-flag = 紅 `#E8380D`. Minimalist, font Noto Sans TC.
- Deliverables are **self-contained HTML** (CDN for Chart.js/fonts; data inlined; photos from iNat CDN).
- 中文科名 from iNat `locale=zh-TW`, with a manual fallback map in `build_profile.py`.
- Dates/timestamps in **CST (UTC+8)**.

## Reproduce
```bash
python3 fetch_inat.py 2026-04-25 "2026/04/25 · 14:41 CST"
python3 build_profile.py
python3 build_transect_html.py
```
New survey day: run `fetch_inat.py <date>`, adjust the scope cutoff in `build_profile.py`, rebuild.
