# Climate × phenology — potential insights, tiered by defensibility

Memo · 2026-06-27 (CST) · 二格山稜線長期定點植物調查 (SOW)

Scope: what a cross-check between station climate data and the iNat phenology of
the 93 ridgeline samples could honestly yield. Tiers are ordered by how much the
data actually supports the claim — Tier 0 holds today; Tier 2 does **not** yet,
and is listed so we don't over-claim it later.

This memo inherits the project's anti-fabrication rule: phenophase comes from
iNat term-12 annotations, sparse signals stay labelled 不足/尚無, and encounter
frequency is never read as abundance or as a trend.

---

## Data realities this memo is anchored to

**Phenology side (on disk, `data/history/records.json` + `data/registry/phenology_seasonality.json`):**
- 1,916 historical observations; **108 flower / 55 fruit / 20 bud** annotations.
- Annotations only meaningful **2018–2024**; earlier years are single records.
- Community flowering peaks **Mar–Apr (76/108 = 70%)**; 大頭茶 (*Polyspora axillaris*)
  is the lone **Oct–Dec** winter-flowering outlier; fruiting has a secondary **Oct** peak.
- Density per species ≈ **1 flowering record / species / year**; only **15 species**
  carry ≥3 flower annotations.
- **Effort confound:** April is simultaneously peak-flowering (47) and peak-observation
  (458 obs). Pooled monthly curves are shaped by when people walked, not only by biology.

**Climate side (not yet retrievable here):**
- Target station **82A750 (茶改場北部分場)**, user-chosen proxy for the ridge.
- `O-A0001-001` / `O-A0003-001` are **nowcast** (today only) — cannot backfill.
- `C-B0024-002` is the **historical (C- = 氣候) archive** — the correct seed source,
  pending confirmation of (a) station 82A750 coverage, (b) daily vs monthly granularity,
  (c) historical depth.
- Hard gate: `*.cwa.gov.tw` is blocked by the environment egress policy (403) and needs
  a `CWA_TOKEN`. Nothing runs until both are in place.

---

## Tier 0 — Defensible now (descriptive, one season suffices)

These are seasonality/normal statements, not trends. They hold the moment a single
station climatology is paired with the existing month-binned phenology.

1. **Seasonality alignment.** Overlay the community flowering curve (Mar–Apr peak)
   on the station's spring temperature rise and rainfall onset; place the Oct fruiting
   peak against the autumn rains. Claim form: *"flowering activity coincides with X",*
   never *"X causes / is shifting flowering."*
2. **Per-phenophase climate envelope.** The temperature / rainfall band within which
   flower, fruit, and bud annotations fall — a descriptive window per phase.
3. **Live "flowering-weather" readout.** Because a synced feed is current, the page can
   compare today's reading to the historical envelope ("today sits inside the typical
   開花 band"). This is the only feature that genuinely requires *daily* cadence rather
   than a static normal.

Caveat carried on every Tier 0 output: pooled across species and effort-confounded;
keep the observation-effort row visible.

---

## Tier 1 — Comparative (needs a few accumulating years; heavily caveated)

Available only after the forward archive accrues multiple paired seasons, and even
then framed as association, not attribution.

4. **Anomaly framing.** Was this spring warmer/wetter than the accumulating baseline,
   and did the community flowering peak move with it? Must be reported beside the
   effort series — a warm spring that also drew more observers is not a phenology signal.
5. **Degree-day / chill accumulation** as a flowering predictor for the well-sampled
   species (金毛杜鵑 Jan–Apr, 華八仙 Feb–Apr, 大頭茶 Oct–Dec) — accumulated GDD-to-first-flower
   as a descriptive threshold, not a fitted forecast.
6. **Lead/lag structure.** Whether fruiting trails flowering by a roughly consistent,
   climate-mediated interval within a species.

---

## Tier 2 — Not yet supported (the real climate-change question)

Listed explicitly so it is never asserted prematurely.

7. **Phenological-shift detection** — does flowering day-of-year trend with warming.
   This needs many years of paired data **and** far denser phenology than ≈1 record/
   species/year. With today's data a per-species DOY regression is statistically empty
   and would manufacture a signal. Do not publish a trend line until the density and
   the year count support it.
8. **Microclimate / lapse-rate structure** along the 512–645 m transect — a single
   station cannot resolve within-transect gradients; this would need on-trail loggers.

---

## The binding constraint — and the lever already in the repo

Daily climate sync is cheap and will be clean, but it **does not fix the limiting
factor**, which is phenology annotation density. The highest-value pairing is daily
climate × a denser flowering-event series.

That denser series may already exist: **`ai_flower.py`** emits a confidence-gated
flowering verdict on **all ~1,916 observations**, not just the ~108 hand-annotated
ones (human fixes layered via `ai_corrections.json`). Treated as a separate,
clearly-labelled event stream — never merged into the iNat term-12 source of truth —
AI-flower could lift the climate cross-check from "too sparse" to a usable n for
Tier 1, with the vision caveats (fruit-as-flower on showy fruit) kept in view.

---

## Honesty guards to bake into any climate output

- Forward-only archive from a nowcast feed; never imply it backfilled the past.
- Seed history from `C-B0024-002`; label its station/granularity/depth explicitly.
- Words: **seasonality / normal / anomaly**, never **trend**, until the years and
  density earn it.
- Keep the observation-effort row in every overlay.
- Pin climate snapshots with provenance (station ID, fetch time), like iNat snapshots.
- Keep AI-flower a separate layer from iNat annotations.

---

## Prerequisites before any of this runs

- [ ] `*.cwa.gov.tw` allowlisted in the egress policy.
- [ ] `CWA_TOKEN` provided (env var, never committed).
- [ ] `C-B0024-002` confirmed to include station 82A750 (else nearest staffed-station
      fallback, accepting a location/elevation offset).
- [ ] Granularity + historical depth confirmed → decides daily-join vs monthly-overlay.
- [ ] `fetch_climate.py` + `climate.json` schema built against the real rows (no
      synthetic data).
