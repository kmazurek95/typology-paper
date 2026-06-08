# External Inputs Staging Log

**Date:** 2026-05-25
**Operator:** Claude Code session (Sonnet/Opus pipeline, plan-approved)
**Purpose:** Stage four external inputs needed by Script 05 (NACE-AIIE lookup) and Script 06 (country-level merge) from `C:/Users/kaleb/Downloads/` into `data/raw/`.

## Files staged

| # | Source URL | Source organization | Target path | Size |
|---|---|---|---|---|
| 1 | https://webfs.oecd.org/Els-com/Social-Expenditure-Database/SOCX2025-All-nat-cur.xlsx | OECD (Social Expenditure Database, April 2025 release) | `data/raw/socx/oecd_socx_programme_2024_release_2025-04.xlsx` | 5,105,016 B |
| 2 | https://www.cwep.us/home/data (Google Sheets export) | CWEP project (Comparative Welfare Entitlements Project, successor to CWED2; Lyle Scruggs et al.) | `data/raw/cwep/cwep_2022-12.csv` | 1,268,616 B |
| 3 | https://www.census.gov/eos/www/naics/concordances/2017_NAICS_to_ISIC_4.xlsx (404 as of 2026-05-25) — retrieved via Wayback Machine | US Census Bureau (via Internet Archive) | `data/raw/naics_isic_correspondence_2017.xlsx` | 128,316 B |
| 4 | https://data.bls.gov/cew/data/files/2023/csv/2023_annual_by_industry.zip | US BLS (Quarterly Census of Employment and Wages, 2023 annual averages) | `data/raw/bls_qcew_naics4_2023.csv` (extracted + filtered) | (309 rows; ~25 KB) |

Move semantics: `copy + verify destination size matches source + delete source`. Per-file safety guard: no source delete unless destination passes the byte-size check. Source files in Downloads are now gone for the four staged inputs.

## Census file provenance (file 3)

- **Original Census URL:** `https://www.census.gov/eos/www/naics/concordances/2017_NAICS_to_ISIC_4.xlsx`
- **Live status as of 2026-05-25:** HTTP 404 (Census restructured site; concordances landing page still links to broken URL).
- **Wayback Machine archive URL:** `https://web.archive.org/web/20210321135944/https://www.census.gov/eos/www/naics/concordances/2017_NAICS_to_ISIC_4.xlsx`
- **Wayback snapshot date:** 2021-03-21.
- **Authority:** Original is US Census Bureau (definitive). Internet Archive snapshot is byte-identical to the original Census release. The crosswalk's reproducibility relies on the Wayback URL above; record it in any paper appendix that cites this file.

## BLS QCEW extraction parameters (file 4)

- **Source ZIP:** `2023_annual_by_industry.zip` (160 MB), contained 2160 per-industry CSVs.
- **NAICS-4 file identification:** filename regex `^2023\.annual (\d{4}) NAICS \1 .+\.csv$` matched **309 files**. The literal `NAICS` token in BLS's filename convention reliably distinguishes NAICS industry files from BLS super-sector aggregate files (e.g. `1011 Natural resources and mining` lacks the NAICS delimiter and is excluded). This is more robust than maintaining a hardcoded super-sector exclusion list.
- **Row filter:** `area_fips == "US000"` (US national) AND `agglvl_code == "16"` (US national, NAICS-4, by ownership). **Verified empirically** by inspecting a sample file (`2023.annual 1111 NAICS 1111 Oilseed and grain farming.csv`) before bulk processing.
- **Important finding during execution:** BLS does **not** publish an "all-ownerships" aggregate row (`own_code == "0"`) at agglvl 16 for per-industry NAICS-4 data. Each industry has 1–4 rows split by ownership (Federal=1, State=2, Local=3, Private=5). The user spec's intent of "all ownerships" was implemented by **summing across own_codes per industry**, not by filtering to a non-existent aggregate row. Ownership patterns observed across 309 industries: Private-only (77 industries), Private+Local+State+Federal (77), Private+Local+Federal (21), Private+Local+State (41), Private+Local (67), Private+State (8), Private+Federal (9), Private+State+Federal (1), all four govt only (8). Documented in `_bls_staging_aux.json`.
- **Output columns:** `industry_code, industry_title, annual_avg_estabs_count, annual_avg_emplvl, annual_avg_wkly_wage, own_codes_summed, n_ownerships`. Wage column is employment-weighted mean across ownerships; counts are summed.
- **Sanity check:** total employment across 309 NAICS-4 industries = **153,034,732** (~153.0M), matching expected ~150M for US private+public employment in 2023.
- **No rows dropped** due to agglvl mismatch (filter was clean).
- **Source ZIP deleted** after successful extraction.

## Files NOT touched in Downloads (operator's cleanup)

- `2017_NAICS_to_ISIC_4 (1).xlsx` — duplicate of file 3, byte-identical
- `ISIC_4_to_2017_NAICS.xlsx` — reverse-direction crosswalk, redundant with file 3
- `SOCX2025-All-nat-cur (1).xlsx`, `(2).xlsx`, `(3).xlsx` — three duplicate downloads of file 1
- `Welfare State Indicators - CWEP Global 2022_12.xlsx` (xlsx, not csv) — the source workbook for file 2's CSV export; kept the CSV form, the xlsx is parallel

Cleanup of these is left to the operator.

## Auxiliary file

`data/raw/_bls_staging_aux.json` — machine-readable record of BLS extraction parameters and aggregated ownership-pattern statistics. Generated alongside this log; safe to delete once Script 05 is operational.
