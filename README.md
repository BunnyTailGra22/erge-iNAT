# 二格山稜線 · iNaturalist 物候 / Mt. Erge Ridgeline · iNaturalist Phenology

> 以 iNaturalist 公民科學資料，建立二格山稜線植物的長期定點觀測與物候時間軸。
> A long-term, fixed-point plant phenology archive for the 二格山 (Mt. Erge) ridgeline, built from iNaturalist citizen-science data.

🌐 **線上 / Live:** https://bunnytailgra22.github.io/erge-iNAT/
🏞️ 荒野保護協會 Society of Wilderness (SOW) · 地點 / Site: 二格山, New Taipei, Taiwan

---

## 專案 / About

**中文** — 以 2026-04-25 的稜線踏查為基準，建立 **93 個定點觀測樣點**（63 種木本植物），再回溯整理 iNaturalist 上同物種、同地點的歷史觀察，組成每個樣點的物候時間軸（葉／花／果＋照片），並每日自動更新。

**English** — Anchored on the 2026-04-25 ridge survey, the project establishes **93 fixed observation units** (63 woody species), back-fills the historical iNaturalist record for the same species at the same site, and assembles a per-unit phenology timeline (leaf / flower / fruit + photos) that refreshes daily.

## 功能 / Features

- **海拔剖面圖（索引）/ Elevation transect (index)** — 沿步道水平距離 × 海拔；點選任一植物 → 該樣點的物候時間軸。Click any plant to open its timeline. (`index.html`)
- **每樣點物候月曆 / Per-unit phenology calendar** — 一年中的日序 × 年份，物候階段以顏色標示，懸停看照片。Day-of-year × year, phenophase by colour, photo on hover. (`data/units/ERG-NNN.html`)
- **TaiCoL 學名校核 / TaiCoL-validated names** — 科別・屬別（中文＋拉丁）、臺灣特有、IUCN／國家紅皮書狀態。Family & genus (Chinese + Latin), endemism, Red List status.
- **GPS 品質處理 / GPS handling** — 精度 >100 m 之定位以鄰點時間內插校正。Low-accuracy fixes interpolated from neighbours.

基準資料 / Baseline: 93 樣點 · 63 種 · 36 科 · 步道 636 m · 海拔 524→659 m。歷史 / History: 2008–2026, 196 觀察者, 1,916 筆紀錄。

## 資料來源與方法 / Data & methods

| 項目 / Item | 來源 / Source |
|---|---|
| 觀察與照片 / Observations & photos | iNaturalist API（`place_id 130869`, user `bunnytailgrass`） |
| 海拔 / Elevation | SRTM 30 m（雙線性內插，via Open Topo Data） |
| 分類與保育 / Taxonomy & conservation | TaiCoL 臺灣物種名錄 Catalogue of Life in Taiwan (`api.taicol.tw/v2`) |
| 樣點身分 / Unit identity | 物種×樣點 + GPS 就近歸屬 hybrid species×site + GPS attribution |

## 架構與重建 / Architecture & rebuild

```
fetch_inat.py        # 抓單一踏查日觀察 / pull one survey day
build_profile.py     # 稜線剖面 + GPS 校正 + 海拔 / ridge profile + GPS fix + elevation
taicol.py            # TaiCoL 學名/科屬/特有/保育 / TaiCoL taxonomy & status
backfill.py          # 歷史回溯 + 樣點歸屬 / historical backfill + attribution
build_unit_page.py --all   # 93 樣點物候頁 / 93 unit timeline pages
build_transect_html.py     # 剖面圖索引 / transect index → index.html
```

純標準函式庫，無需安裝套件 / Pure Python stdlib — no dependencies.

## 自動更新 / Automation

每日 06:00（台北）GitHub Actions 重抓歷史觀察 → 重建頁面 → 有變動才提交並部署。
Daily at 06:00 CST, GitHub Actions re-syncs from iNaturalist, rebuilds the pages, and deploys only if data changed. See [`.github/workflows/daily-sync.yml`](.github/workflows/daily-sync.yml).

## 注意事項 / Caveats

- **物候標記稀疏 / Sparse phenophase** — iNat 註記僅約 8%，且無「葉相」欄位；灰點為僅有照片之觀察，葉/花/果完整判讀需後續照片分類。Annotations cover ~8% and there is no leaf annotation; grey points are photo-only.
- **非樣區優勢度 / Not quadrat data** — 為機會性點位觀察，非系統樣區，故不呈現優勢度。Opportunistic points, not quadrat sampling — no dominance values.
- **資料快照 / Snapshot** — 基準鎖定於 2026/04/25 · 14:41 CST（iNat 鑑定會隨時間變動）。Baseline pinned at 2026/04/25 · 14:41 CST.

## 致謝與授權 / Credits & license

觀察與照片版權屬各 iNaturalist 觀察者（依其授權）。分類資料 © TaiCoL。色彩採荒野保護協會品牌色。
Observations & photos © their respective iNaturalist observers (per each licence). Taxonomy © TaiCoL. Colours follow the SOW brand palette.

🤖 Pipeline & site built with [Claude Code](https://claude.com/claude-code).
