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
| `taicol.py` | Validate the registry species against Catalogue of Life in Taiwan (TaiCoL): Taiwan-accepted name, family & genus 中拉, endemism, IUCN/Red List. Reuses the sibling erge-phenology cache **and its own previous output**; queries only species not yet resolved. Runs in the daily sync (between `backfill.py` and the page builds). | `data/registry/taxa_taicol.json` |
| `build_unit_page.py --all` | Per-unit phenology calendar pages (TaiCoL family/genus 中拉 + 特有/保育 badges). | `data/units/ERG-*.html` |
| `build_transect_html.py` | Render the self-contained transect page + summary cards + 科/屬 filters (Chinese + Latin from TaiCoL); merges the supplementary units from `units.json`. | `data/.../transect_2026-04-25.html`, **`index.html`** (Pages entry) |

`index.html` is the published transect (served by GitHub Pages from repo root).

## Data source (iNaturalist API)
- Endpoint `https://api.inaturalist.org/v1/observations`
- `user_login=bunnytailgrass`, `place_id=130869` (二格山, NT, TW), `observed_on=<date>`, `locale=zh-TW`
- Family is **not** embedded — enrich via `/v1/taxa/<ids>` reading `ancestors[rank=family]`.
- Elevation is **not** in iNat — sampled from SRTM 30 m (Open Topo Data, bilinear).

## Key decisions
- **Supplementary samples**: `EXTRA_UNIT_IDS` in `backfill.py` lists observations the 2026-04-25 walk
  did not produce a unit for. They are resolved against iNat and **appended after** the 93 baseline
  units (ERG-094+), so ERG-001–ERG-093 keep their trail-order ids and page URLs; their taxa join the
  backfill query, so the archive picks up those species' history too. Position from iNat, elevation
  from SRTM, `dist_m` = projection onto the 2026-04-25 trail polyline with the perpendicular offset
  kept separately as `off_trail_m` (never folded into `dist_m`). The transect draws them as
  **triangles** with their own observation date in the tooltip — they are on the trail but not from
  the survey day, so they must never read as baseline points. Currently ERG-094 *Castanopsis carlesii*
  (obs 395425555) and ERG-095 *Quercus gilva* 赤皮 (obs 343780669, the 64th species).
- **Ridgeline scope = observations before 14:56 CST, minus the first two trailhead points**
  (93 obs / 63 species from the walk itself; excluded IDs 353345277, 353345653 via `EXCLUDE_IDS` in build_profile.py). The real off-crest
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
- **Phenophase source of truth = iNaturalist annotations.** Flower/fruit/bud come from iNat
  term-12 annotations, read by `backfill.py`; annotate ON iNat (Identify/Annotate panel) and the
  daily sync ingests them — no separate codes file. Leaf has no native iNat annotation → deferred
  (would need an iNat Observation Field). Never auto-write annotations back to iNat.
- **Daily changelog**: the daily sync workflow runs `changelog.py` (HEAD vs new `records.json`:
  新增/移除/重新鑑定/品質變更/新物候註記) and puts the summary in each commit message.
- **Two sync cadences (two topics)**: the ridgeline **plant** phenology syncs **daily**
  (`.github/workflows/daily-sync.yml`, 06:00 CST); the **butterfly** source data syncs **monthly**
  (`.github/workflows/monthly-butterfly-sync.yml`, 1st 22:30 UTC = 2nd 06:30 CST). They are
  independent — plants are presence + phenophase of a fixed 93-unit registry; butterflies are
  per-species iNat counts over a book-curated host-plant network (below). The butterfly source
  data moves slowly (host plants, taxonomy), so monthly is deliberate — not a weaker daily.

## Butterfly page (papilionoidea.html) — monthly sync
Self-contained 鳳蝶總科 × 寄主植物 network page (iNat `place_id=130869`, `taxon 47224`
Papilionoidea, **all observers** × 《臺灣蝶類誌》 host plants × TaiCoL taxonomy). Fully
automatic — **no manual step**; a newly-seen butterfly arrives with its host plants already
resolved.
- **CI is the sole maintainer of this page.** The monthly workflow owns `papilionoidea.html`.
  The sibling **`update-erge-papilionoidea` skill is retired — do NOT run it by hand** any more:
  it rewrites the same file from a local copy of the data, so running both would make the two
  fight over the page and clobber each other's commits. The skill's caches stay useful only as
  the *local* fallback half of the book lookups below; the repo copies are what CI reads.
  Before this handover the page was refreshed weekly by that skill ("weekly butterfly page
  refresh" commits up to 2026-10-25); from the handover on it is refreshed monthly by CI.
- **Source of truth = `data/butterfly/registry.json`** — the entire inlined `DATA` object
  (butterflies + fam_nodes/edges_bf_fam/gg_edges/bgenus/pgenus + meta). Only each butterfly's
  `count` and the *set* of present species come from iNat.
- **Host-plant provenance is dual and additive.** The curated 97-species network is
  **《臺灣蝶類誌》+TaiCoL-derived** — never regenerate/overwrite it from an API. A *new* species'
  hosts are auto-sourced and only *extend* the network, `hostsrc` recording which source won:
  **`臺灣蝶類誌`** if the book host cache (shape `{butterfly_sci: [host_sci,…]}`) has the species —
  the book is the gold standard; else **`GloBI`** (∩ TaiCoL). The book cache is looked up in two
  places, in order: (1) repo copy **`data/butterfly/hosts_book.json`** — the only one CI can see,
  so commit the book data here to make it authoritative in the automated monthly sync; (2) the
  sibling **`update-erge-papilionoidea` skill** cache
  (`~/.claude/skills/update-erge-papilionoidea/hosts_book.json`) — soft-reused for *local* runs,
  exactly like `taicol.py` reuses the `update-erge-phenology` cache, and absent in CI. Both no-op
  cleanly when missing. Book and GloBI are real datasets, not encounter-frequency guesses.
- **Book 中文 names for new species** keep the priority 書 > TaiCoL > iNat (the c72eb2f decision)
  via the same two-place lookup: `data/butterfly/names_book.json` (repo, CI-visible) then the skill
  cache, shape `{butterfly_sci: {zh, zhlist, genzh}}`. A hit sets `zhsrc:"臺灣蝶類誌"` and keeps the
  iNat 俗名 as the searchable `alias`; a miss falls back to the iNat common name
  (`zhsrc:"iNaturalist"`). Without this the retired skill's book naming would have been lost at
  handover. **Extend both `hosts_book.json` and `names_book.json` from 《臺灣蝶類誌》** for species
  beyond the current roster — that is what makes the book, not GloBI/iNat, authoritative for the
  next new arrival.

| Script | Does |
|---|---|
| `fetch_butterfly.py` | Pull iNat `species_counts` for Papilionoidea @ site (all observers); update each species' `count`; append newly-seen species (family/genus 中拉 from taxon ancestors) **and auto-resolve their larval host plants** (see below). Curated species are never deleted; a species missing from a run keeps its count (partial fetch is non-destructive). |
| `globi.py` | `host_species(sci)` → larval host-plant binomials from GloBI (NHM HOSTS lepidoptera dataset). Degrades to `[]` on any error — never invents hosts. |
| `taicol.py` | `resolve(sci, common)` (also the `taicol.py` batch) → Taiwan-accepted name + 中文 科/屬 + 特有/保育 for a taxon. Reused to enrich each GloBI host. |
| `build_butterfly.py` | Recompute `meta`, re-inline `registry.json` as the single `const DATA=…;` line in `papilionoidea.html`. Compact JSON → **byte-identical** round-trip when data is unchanged (no spurious diff). |
| `changelog_butterfly.py` | HEAD vs new registry: 新增蝶種 / 觀察數異動 / totals → monthly commit message. |

- **Auto host resolution (new species)**: `globi.host_species(sci)` → for each host, `taicol.resolve`
  gives the Taiwan-accepted name + 中文 科/屬 + 特有/保育. Only TaiCoL-resolved hosts are kept — this
  both **Taiwan-localises** GloBI's global host list and **drops noise** (unresolved hosts are never
  written). The species' `sp` list + the derived structures (`edges_bf_fam`/`fam_nodes`/`pgenus`/
  `gg_edges`/`bgenus`) are extended from that. If GloBI/TaiCoL resolve nothing, the species stays
  `host_pending:true` with empty `sp` and is **retried automatically next month** — still no manual step.
  Resolution triggers on an **empty `sp`**, not the flag, so curated species that predate the flag
  (6 at present, e.g. 黃星弄蝶／虎灰蝶) are retried too rather than skipped forever.
- **Reproduce**: `python3 fetch_butterfly.py && python3 build_butterfly.py` (fetch needs network to
  iNat + GloBI + TaiCoL).

## AI flower-suggestion layer (vision) — optional, separate from iNat
The phenophase source of truth stays iNaturalist (above). On top of it a vision model adds an
independent **「AI 建議開花」** layer — it never writes back to iNat and is not merged into the
term-12 annotations.

- `ai_flower.py` aggregates ALL photos of an observation → `{flower, confidence}` (open flowers
  only; tight buds / fruit / leaves-only do NOT count). Writes `data/phenophase/ai_flower.json`
  (`{obs_id: {flower, confidence, n_photos, model, at}}`). Flower is the only reliable vision
  phenophase (fruit = medium, bud = med-low, 落葉 = infeasible — absence + evergreens).
- Needs `ANTHROPIC_API_KEY` (user-provided env var — **never commit it**; not wired into CI, to
  avoid per-run cost). The committed `ai_flower.json` was seeded by a hand-verified ERG-052 demo.
- **One-time backfill** (run in the terminal that holds the key; resumable — caches every 20 obs
  and skips already-classified ones on rerun, so Ctrl-C is safe):
  ```bash
  VISION_MODEL=claude-haiku-4-5 python3 ai_flower.py --all --skip-annotated
  ```
  Haiku 4.5 is enough for this binary call (~$1–2 for all ~1.8k obs; `claude-sonnet-4-6` is the
  script default). `--skip-annotated` skips obs iNat already marks as flowering; `--limit N` caps.
- `build_unit_page.py` renders an AI flowering suggestion (confidence ≥ 0.5, iNat-unmarked) as a
  distinct **red ring** + confidence tooltip + legend + per-unit count.
- **Human corrections overlay** `data/phenophase/ai_corrections.json` (`{obs_id: {flower, note, by, at}}`):
  `build_unit_page.py` always applies it over the AI verdict, so QA fixes survive even a full
  `ai_flower.json` rebuild. Keep `ai_flower.json` as raw AI output; record human verdicts here. The
  vision model is prone to **fruit-as-flower** errors on showy fruit (Illicium star-follicles,
  Viburnum/Psychotria/Clerodendrum berries) — to find them, cross-check AI-flower flags against iNat
  `phenophase` containing "fruit", then verify the photos before adding an override.
- **`rebuild_after_vision.sh`** rebuilds all unit pages + transect from the updated
  `ai_flower.json`, prints a summary, then asks before commit/push (`-y` skips the prompt). It
  deliberately skips `backfill.py` so it won't re-pull iNat data and desync from the vision run.

## Conventions
- **Brand palette = 荒野保護協會 (SOW)**; tokens in `SOW/brand/` (`sow_palette.css/json`).
  research = 荒野綠 `#587A30`, needs-ID = 荒野綠2 `#90B821`, terrain/grid = 荒野灰 `#666666`/`#B2B2B2`,
  GPS-flag = 橘 `#C85200`（Tableau color-blind 深橘，非 SOW 色票；剖面圖以**實心橘點**呈現，
  半徑略大於一般點；該 6 點不再顯示 research/needs-ID 品質色）. 單元頁物候的 開花/AI 建議開花
  仍用紅 `#E8380D`. Minimalist, font Noto Sans TC.
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
