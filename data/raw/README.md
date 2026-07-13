# Raw Data

Source data for the typology paper pipeline. Some files ship with the repository; others must be obtained separately due to size or licensing. The pipeline scripts fail with an informative error if a required file is missing.

## Files included in the repository

- `oecd_epl_v4.csv` — OECD EPL Version 4 sub-indices (EPRC, EPT). Source: OECD. Used by `scripts/01_clean_epl.py`.
- `oecd_epl_overview_all-versions_v1-v4.csv` — OECD EPL all versions (fallback for countries without V4). Source: OECD. Used by `scripts/01_clean_epl.py`.
- `AIOE_DataAppendix.xlsx` — Felten, Raj & Seamans (2021) AI Occupational Exposure scores. Source: [AIOE-Data/AIOE](https://github.com/AIOE-Data/AIOE). Used by `scripts/03_crosswalk_aioe.py`.
- `isco_soc_crosswalk.xls` — BLS SOC 2010 to ISCO-08 correspondence table. Source: US Bureau of Labor Statistics. Used by `scripts/03_crosswalk_aioe.py`.
- `estat_lfsi_pt_a_en.csv` — Eurostat temporary employment shares. Source: Eurostat table lfsi_pt_a. Used by `scripts/01_clean_epl.py`.
- `2022_RTM.xlsx` — OECD Risks that Matter 2022 Collected Statlinks (aggregate country-level tables). Source: OECD. Used by `scripts/07_descriptive.py`.

## Files NOT included (obtain separately)

- **PIAAC Public Use Files** (`prg*p2.csv`, `prgnldp1.csv`) — ~1.5 GB total, 31 country-level CSVs. Freely downloadable from https://www.oecd.org/en/data/datasets/piaac.html. Used by `scripts/02_clean_piaac.py`.
- **Eurostat LFS employment by ISCO** (`eurostat_lfsa_eisn2.csv`) — ~18 MB. Downloaded automatically by `scripts/03b_validate_aioe.py` on first run. No manual action needed.
- **RTM 2022 and 2024 microdata** (`.dta` files) — Restricted access. Request from OECD Directorate for Employment, Labour and Social Affairs (Pauline Fron, Pauline.FRON@oecd.org). Used by v2 regression scripts, not required for v1.
- **OECD Social Expenditure Database (SOCX)** — public. April 2025 release; download from https://www.oecd.org/social/expenditure.htm. Used by the v2 country-level merge (`v2_prep/scripts/06_merge_country_level.py`), not required for v1.
- **CWEP welfare-generosity index** — Comparative Welfare Entitlements Project (Scruggs et al.); download from https://www.cwep.us/home/data. Used by the v2 welfare-robustness rung, not required for v1.
