# Data Documentation
Last updated: April 16, 2026 (added download dates and provenance for v1.0 release)
Previous update: April 8, 2026 (automated scan + manual PDF organization)

## Summary
- **Total files:** 70+ across raw/, processed/, and RTM microdata folders
- **Total size:** ~1.2 GB
- **Key update:** RTM 2022 and 2024 microdata now present (2022: 27,469 obs × 423 vars; 2024: 27,229 obs × 281 vars)
- **Processed files:** EPL gap, task profile, typology positions, AIOE crosswalk all computed

## Manual notes (preserved from previous documentation)

### Known data issues
1. **EPL EPRC missing (RESOLVED):** The original `oecd_epl_v4.csv` contains EPL_T and EPL_OV but not EPRC. As of April 9, 2026, `oecd_epl_database_full.xlsx` supersedes `oecd_epl_v4.csv` as the authoritative EPL source because the CSV was missing the EPRC measure. The old CSV is retained for provenance. Script 01 should be rerun against the new file to compute the correct dualization gap (EPRC − EPT).
2. **PIAAC skill-use indices:** Data Explorer shows missing values for skill-use-at-work indices (Reports 4-6). Proficiency scores used as proxy.
3. **Country code inconsistencies:** EPL=ISO3, ESS=ISO2, Eurostat=ISO2. Standardized to ISO3 in processing.

---

## Files in data/raw/ (original downloads)

### Overview of raw files
- **2022_RTM.xlsx** (Excel) — 0.5 MB, modified 2026-04-02 17:30:09
- **2024-RTM.xlsx** (Excel) — 5.8 MB, modified 2026-04-02 17:30:17
- **AIOE_DataAppendix.xlsx** (Excel) — 0.2 MB, modified 2026-04-02 17:14:58
- **estat_lfsi_pt_a_en.csv** (CSV) — 3.3 MB, modified 2026-04-02 17:19:39
- **gincdif-cntry.xlsx** (Excel) — 9695 bytes, modified 2026-04-02 17:16:49
- **isco_soc_crosswalk.xls** (Excel) — 0.3 MB, modified 2026-04-02 17:48:04
- **oecd_epl_overview_all-versions_v1-v4.csv** (CSV) — 0.7 MB, modified 2026-04-03 11:04:34
- **oecd_epl_v4.csv** (CSV) — 0.1 MB, modified 2026-04-02 16:55:59
- **piaac_cycle2_summary.xls** (Excel) — 38912 bytes, modified 2026-04-02 17:10:22
- **prgautp2.csv** (CSV) — 42.3 MB, modified 2026-04-02 18:14:35
- **prgbelp2.csv** (CSV) — 35.4 MB, modified 2026-04-02 18:15:20
- **prgcanp2.csv** (CSV) — 112.3 MB, modified 2026-04-02 18:23:31
- **prgchep2.csv** (CSV) — 61.6 MB, modified 2026-04-02 23:00:36
- **prgchlp2.csv** (CSV) — 43.7 MB, modified 2026-04-02 18:19:43
- **prgczep2.csv** (CSV) — 46.6 MB, modified 2026-04-02 18:20:22
- **prgdeup2.csv** (CSV) — 44.6 MB, modified 2026-04-02 18:20:12
- **prgdnkp2.csv** (CSV) — 43.3 MB, modified 2026-04-02 18:20:00
- **prgespp2.csv** (CSV) — 54.2 MB, modified 2026-04-02 23:00:19
- **prgestp2.csv** (CSV) — 61.5 MB, modified 2026-04-03 10:51:44
- **prgfinp2.csv** (CSV) — 35.6 MB, modified 2026-04-02 18:18:09
- **prgfrap2.csv** (CSV) — 56.7 MB, modified 2026-04-02 18:21:29
- **prggbrp2.csv** (CSV) — 44.2 MB, modified 2026-04-02 22:59:22
- **prghrvp2.csv** (CSV) — 39.4 MB, modified 2026-04-02 18:18:37
- **prghunp2.csv** (CSV) — 41.1 MB, modified 2026-04-02 22:03:36
- **prgirlp2.csv** (CSV) — 34.1 MB, modified 2026-04-02 22:03:57
- **prgisrp2.csv** (CSV) — 53.1 MB, modified 2026-04-03 10:44:53
- **prgitap2.csv** (CSV) — 45.2 MB, modified 2026-04-02 22:08:39
- **prgjpnp2.csv** (CSV) — 45.6 MB, modified 2026-04-02 22:07:01
- **prgkorp2.csv** (CSV) — 58.2 MB, modified 2026-04-03 10:45:54
- **prgltup2.csv** (CSV) — 54.1 MB, modified 2026-04-02 22:09:09
- **prglvap2.csv** (CSV) — 57.1 MB, modified 2026-04-02 22:08:58
- **prgnldp1.csv** (CSV) — 18.1 MB, modified 2026-04-03 10:50:34
- **prgnorp2.csv** (CSV) — 30.6 MB, modified 2026-04-02 22:06:37
- **prgnzlp2.csv** (CSV) — 46.1 MB, modified 2026-04-02 22:08:53
- **prgpolp2.csv** (CSV) — 43.9 MB, modified 2026-04-02 22:56:21
- **prgprtp2.csv** (CSV) — 28.8 MB, modified 2026-04-02 22:54:11
- **prgsgpp2.csv** (CSV) — 44.1 MB, modified 2026-04-02 22:58:55
- **prgsvkp2.csv** (CSV) — 50.3 MB, modified 2026-04-02 22:59:54
- **prgswep2.csv** (CSV) — 34.3 MB, modified 2026-04-02 22:58:28
- **prgusap2.csv** (CSV) — 33.6 MB, modified 2026-04-02 22:58:29
- **stfedu-cntry.xlsx** (Excel) — 10990 bytes, modified 2026-04-02 17:39:10
- **stfhlth-cntry.xlsx** (Excel) — 10962 bytes, modified 2026-04-02 17:38:21

### Detailed file descriptions

#### oecd_epl_v4.csv
- **Source:** OECD Employment Protection Legislation, Version 4 (EPLex), https://stats.oecd.org/
- **Downloaded:** 2026-04-02
- **Role:** Axis 2 (dualization gap)
- **Used by:** `scripts/01_clean_epl.py`
- **Format:** SDMX-CSV (556 rows × 26 columns)
- **Key columns:** REF_AREA (ISO3), MEASURE, TIME_PERIOD, OBS_VALUE (0-6 scale)
- **Measures:** EPL_T (temporary) and EPL_OV (overall). Note: EPRC (regular contracts) requires separate download.
- **Countries:** 43 (ARG, AUS, AUT, BEL, CAN, CHE, CHL, COL, CRI, CZE, DEU, DNK, ESP, EST, FIN, FRA, GBR, GRC, HUN, IRL, ISL, ISR, ITA, JPN, KOR, LTU, LUX, LVA, MEX, NLD, NOR, NZL, OECD, PER, POL, PRT, PRY, SVK, SVN, SWE, TUR, URY, USA)
- **Years:** 2013-2019

#### PIAAC Cycle 2 files (32 country-specific .csv files + summary .xls)
- **Source:** OECD PIAAC Data Explorer, https://www.oecd.org/en/data/datasets/piaac.html
- **Downloaded:** 2026-04-02 to 2026-04-03
- **Role:** Axis 1 (task-profile ratio) + proficiency baselines
- **Used by:** `scripts/02_clean_piaac.py`
- **Country files:** prg[COUNTRY]p2.csv (e.g., prgautP2.csv for Austria, prgcanp2.csv for Canada)
- **Summary:** piaac_cycle2_summary.xls with 6 sheets (Literacy, Numeracy, Problem Solving, ICT use, Numeracy use, Reading use)
- **Note:** Skill-use-at-work indices (Reports 4-6) show missing values in Data Explorer export. Individual country files contain raw item data for manual computation if needed.
- **Countries:** 32 total (OECD Cycle 2 participants)

#### ESS Round 11 country-level files
- **gincdif-cntry.xlsx** — 'Government should reduce income differences' (redistribution DV proxy)
  - 28 countries, 5-point Likert scale with percentages
- **stfedu-cntry.xlsx** — 'State of education in country' (social investment proxy)
  - 30 countries, 0-10 scale
- **stfhlth-cntry.xlsx** — 'State of health services in country' (social investment proxy)
  - 30 countries, 0-10 scale

#### estat_lfsi_pt_a_en.csv
- **Source:** Eurostat table lfsi_pt_a (part-time and temporary employment), https://ec.europa.eu/eurostat/databrowser/view/lfsi_pt_a/
- **Downloaded:** 2026-04-02
- **Role:** Supplementary indicator for Axis 2
- **Used by:** `scripts/01_clean_epl.py`
- **Format:** SDMX-CSV (42,773 rows × 12 columns)
- **Work status:** EMP_PT, EMP_TEMP, UEMP_PT
- **Units present (per work status):** PC_EMP (% of total employment), PC_SAL (% of salaried employees), THS_PER (count)
- **Countries:** 38 (ISO2 codes)
- **Years:** 2003-2025
- **Errata (2026-05-29):** the `temp_share` column derived from this file into `processed/epl_gap.csv` by `scripts/01_clean_epl.py` is **PC_EMP**-based (% of total employment) because that script filters EMP_TEMP/T/Y15-64 but **not** `unit`, then takes the first row per country. It is mislabeled relative to a temps-over-employees reading and **inert** (pass-through only; never used in any computation). Do not reuse it. The unconditional weighted-gap construction pulls a fresh **PC_SAL** series instead (`v2_prep/scripts/01c_unconditional_weighted_gap.py`). See decision log entry #18.

#### AIOE_DataAppendix.xlsx
- **Source:** Felten, Raj & Seamans (2021), https://doi.org/10.1002/smj.3286
- **Downloaded:** 2026-04-02
- **Role:** AI Occupational Exposure scores
- **Used by:** `scripts/03_crosswalk_aioe.py`
- **Sheets:** Index, Appendix A-E (occupational, industry, geographic, ability scores)
- **Appendix A key sheet:** 774 rows with SOC Code (6-digit), Occupation Title, AIOE score
- **Note:** Indexed by US SOC codes; requires crosswalk to ISCO-08 for international use.

#### isco_soc_crosswalk.xls
- **Source:** BLS SOC Policy Committee (August 2012, updated June 2015), https://www.bls.gov/soc/soccrosswalks.htm
- **Downloaded:** 2026-04-02
- **Role:** SOC 2010 ↔ ISCO-08 mapping
- **Used by:** `scripts/03_crosswalk_aioe.py`
- **Sheets:** Two (ISCO-08 to SOC and reverse)
- **Mapping:** ~1,126 rows per direction; many-to-many relationships

#### 2022_RTM.xlsx and 2024-RTM.xlsx
- **Source:** OECD Risks that Matter Surveys (published Statlinks), https://www.oecd.org/social/risks-that-matter.htm
- **Downloaded:** 2026-04-02
- **Role:** Aggregate country-level preference data for illustrative figures
- **Used by:** `scripts/07_descriptive.py`
- **2022 sheets:** 28 (including g3-5 on tax-the-rich, g2-2 on service satisfaction)
- **2024 sheets:** 24 (including g1.5-g1.8 on AI/technology, g3.1 on willingness to pay)
- **Use:** Support descriptive figures before individual-level regression.

---

## Files in data/processed/ (cleaned and computed outputs)
- **aioe_isco08.csv** (CSV) — 28.3 KB, modified 2026-04-03 11:21:45
- **aioe_isco08_2digit.csv** (CSV) — 1009 bytes, modified 2026-04-03 11:21:45
- **epl_gap.csv** (CSV) — 2.3 KB, modified 2026-04-03 11:19:28
- **eurostat_emp_by_isco.csv** (CSV) — 484.2 KB, modified 2026-04-06 18:58:18
- **pca_aioe_validation.csv** (CSV) — 1.2 KB, modified 2026-04-06 18:58:55
- **task_profile.csv** (CSV) — 3.8 KB, modified 2026-04-03 11:28:25
- **typology_positions.csv** (CSV) — 6.4 KB, modified 2026-04-03 12:01:50

### Processed file descriptions

#### epl_gap.csv
- **Output from:** Script 01
- **Shape:** 21 countries × 6 columns
- **Columns:** country_iso3, country_name, eprc, ept, dualization_gap, year
- **Use:** Axis 2 of typology (labor market dualization)

#### task_profile.csv
- **Output from:** Script 02
- **Shape:** ~28 countries × 6 columns
- **Columns:** country_iso3, country_name, ict_use_work, numeracy_use_work, reading_use_work, task_profile_ratio
- **Use:** Axis 1 of typology (AI displacement vs. complementarity)

#### aioe_isco08.csv
- **Output from:** Script 03
- **Shape:** ~460 occupations × 4 columns
- **Columns:** isco08_code, isco08_label, aioe_score, n_soc_matches
- **Use:** Crosswalk for individual-level AI exposure variable in regression

#### aioe_isco08_2digit.csv
- **Aggregated version:** 2-digit ISCO-08 level (occupational major groups)
- **Use:** Sensitivity analysis or visualizations

#### typology_positions.csv
- **Output from:** Script 05
- **Shape:** ~22 countries × 8 columns
- **Columns:** country_iso3, country_name, task_profile_ratio, dualization_gap, task_profile_z, dualization_z, cluster, cluster_label
- **Cluster coding:** 1=Complementary+Low, 2=Complementary+Deep, 3=Displacement+Low, 4=Displacement+Deep
- **Use:** Typology scatter plot (signature figure) and cluster analysis

#### eurostat_emp_by_isco.csv
- **Derivation:** Aggregated from Eurostat `lfsa_eisn2` (Employment by sex, age, occupation and full-time/part-time activity — ISCO-08 1-digit). Earlier versions of this documentation incorrectly listed `lfsi_pt_a` as the source; corrected 2026-05-26 (errata flagged in [`v2_prep/docs/axis2_weighting_diagnostic_2026-05-26.md`](../v2_prep/docs/axis2_weighting_diagnostic_2026-05-26.md) Unexpected Finding 3).
- **Use:** Employment structure by occupation and country (input to Eurostat-employment-weighted Felten AIOE in [`scripts/03b_validate_aioe.py`](../scripts/03b_validate_aioe.py)).

#### pca_aioe_validation.csv
- **Validation check:** PCA on skill-use indices vs. task_profile_ratio

---

## RTM 2022 microdata

**Location:** `data/OECD_RTM_2022_Public_Use_Microdata/FinalData_dta/FinalData_dta/`
- **File:** OECD_RTM_2022_Public_Use_Microdata.dta (90 MB)
- **Shape:** 27,469 observations × 423 variables
- **Years:** 2022
- **Survey design:** Stratified by country; respondents are nationally representative samples (18+)

### RTM 2022 variable structure
- **Core ID/weight variables:** id, ctrcode (country numeric code), year, ctryear, weight (survey weight), year
- **Treatment flags:** a_treatment, break, cc_treatment (experimental design markers)
- **Time stamps:** starttime, endtime
- **Question variables:** q1-q48b (main questionnaire items, ~200 variables)
- **Sociodemographic variables:** s1-s40 (background and context)

### RTM 2022 variables of interest
- **Redistribution preference:** See questionnaire for items on taxing the rich, income inequality
- **Social investment:** Items on education/training spending, health service quality
- **Automation risk perception:** (Note: Limited in 2022 wave; full module added in 2024)
- **Employment status:** s4, s5, s6 (employment type and contract status)
- **Occupation:** s9, s10 (job type; ISCO coding appears indirect)
- **Income:** s8_dec (income decile); s8_eq (equivalized); s8_standard
- **Education:** s6_cat2, s6_cat3 (categorical education levels)
- **Demographics:** s3_age, s3_agegroup, s4 (age, employment); gender encoded in various s-vars
- **Survey weight:** weight (main expansion weight for national representation)

### Documentation and questionnaire documents (PDF)
- **OECD-RTM-Technical-Documentation-Survey-Design.pdf** (1.6 MB) — Technical documentation covering survey methodology, questionnaire design, and variable definitions across all RTM waves (2018, 2020, 2022, 2024). See OECD Working Papers No. 324 (https://dx.doi.org/10.1787/5eebe551-en). Recommended reference for understanding questionnaire construction and sample design.
- **OECD-Risks-That-Matter-2022-Core-Questionnaire.pdf** (349 KB) — Main survey instrument with full question text for 2022 wave
- **OECD-Risks-That-Matter-2022-Background-Questionnaire.pdf** (280 KB) — Sociodemographic item wording for 2022 wave
- **Terms_Conditions_OECD_RTM_microdata.pdf** (99 KB) — Data use agreement and attribution requirements

---

## RTM 2024 microdata

**Location:** `data/OECD_RTM_2024_Public_Use_Microdata/OECD_RTM_2024_Public_Use_Microdata/OECD_RTM_2024_Public_Use_Microdata/`
- **File:** OECD_RTM_2024_Public_Use_Microdata.dta (8.5 MB)
- **Shape:** 27,229 observations × 281 variables
- **Years:** 2024
- **Survey design:** Updated design with expanded AI/automation module

### RTM 2024 variable structure (restructured vs. 2022)
- **Core ID/weight variables:** id, country (country name), ctrcode, year, ctryear, weight
- **Updated variable prefixes:** More concise naming (s0-s35, q1-q30 mainly)
- **Question variables:** q1-q30 (consolidated question set, ~100 variables)
- **Sociodemographic variables:** s0-s35 (revised background structure)
- **Fewer derived variables:** Compared to 2022

### RTM 2024 variables of interest (enhanced)
- **Redistribution preference:** q2a-q2l, q3a-q3m (expanded items on wealth, taxation, inequality)
- **Social investment:** q9a-q9g (policy priorities), q23a-q23f (government responsibility)
- **Automation/AI risk perception (NEW MODULE):** q4a-q4e, q5-q7, q21-q22 (AI impact, retraining needs, AI skepticism)
- **Employment status:** s4, s5, s6 (employment contract type)
- **Occupation:** s10, s11 (job title/ISCO)
- **Income:** s9_dec (income decile)
- **Education:** s7_cat3 (education level)
- **Demographics:** s3_agegroup, country-level flags (s13_*, s35_*)
- **Survey weight:** weight

### Key differences from RTM 2022
- **Fewer variables overall** (281 vs. 423) due to streamlined questionnaire
- **Expanded AI/automation items** (new questions q4-q7, q21-q22)
- **Country variable added** (text country name for convenience)
- **Revised income/education coding** (fewer derived categories)
- **Same survey weight approach** (national expansion weights)

### Documentation and questionnaire documents (PDF)
- **OECD-RTM-2024-Main-Findings-Report.pdf** (2.3 MB) — Official OECD published report on 2024 RTM survey findings. Contains key policy insights, descriptive statistics by country, and cross-country comparisons on social policy preferences and automation concerns. See https://oecd-ilibrary (DOI 3947946a-en).
- **OECD-Risks-That-Matter-2024-Core-Questionnaire.pdf** (339 KB) — Updated main survey instrument for 2024 wave, includes expanded automation/AI module
- **OECD-Risks-That-Matter-2024-Background-Questionnaire.pdf** (529 KB) — Sociodemographic items for 2024 wave
- **Terms_and_Conditions.pdf** (57 KB) — Data use agreement

---

## Archive files (.zip)
The following .zip files are present and have been extracted:
- **OECD_RTM_2022_Public_Use_Microdata.zip** (7.6 MB) → Extracted to folder of same name
- **OECD_RTM_2024_Public_Use_Microdata.zip** (2.9 MB) → Extracted to folder of same name
- **FinalData_dta.zip** (7.4 MB, within 2022 folder) → Extracted to FinalData_dta/FinalData_dta/
- **OECD_RTM_2024_Public_Use_Microdata.zip** (2.1 MB, within 2024 subfolder) → Extracted

All microdata .dta files are now directly accessible without further extraction needed.

---

## Data completeness and readiness

### Ready for analysis (Axis 1 and 2, typology figure)
- EPL gap (dualization) computed — Script 01 complete
- Task profile ratio (AI displacement/complementarity) computed — Script 02 complete
- Typology positions (2D scatter) computed — Script 05 complete
- AIOE crosswalk to ISCO-08 computed — Script 03 complete
- Typology scatter plot generated — Script 07 (descriptive) ready

### Ready for regression analysis
- RTM 2022 microdata present (27,469 obs × 423 vars)
- RTM 2024 microdata present (27,229 obs × 281 vars)
- Both waves include redistribution preference items
- 2024 includes expanded AI/automation module (q4-q7, q21-q22)
- Employment status, income decile, education available in both waves
- Caveat: ISCO occupation codes not explicitly present in RTM; occupation coded as job title (s9/s10). Crosswalk to ISCO may require additional mapping.
- Survey weights present (weight variable) for population inference

### Still needed
- Manual ISCO coding or external crosswalk for RTM occupation variables (if ISCO-level AI exposure needed)
- ESS11 full microdata (fallback if RTM not sufficient; freely available after registration)

---

## Data processing pipeline status

| Script | Task | Input | Output | Status |
|--------|------|-------|--------|--------|
| 01 | EPL gap | oecd_epl_v4.csv | epl_gap.csv | Complete |
| 02 | Task profile | piaac_*.csv | task_profile.csv | Complete |
| 03 | AIOE crosswalk | AIOE_DataAppendix.xlsx + isco_soc_crosswalk.xls | aioe_isco08.csv | Complete |
| 04 | RTM cleaning | rtm_microdata.dta | (cleaned RTM) | Ready (microdata present) |
| 05 | Typology merge | epl_gap.csv + task_profile.csv | typology_positions.csv | Complete |
| 06 | Merge analysis | cleaned RTM + typology + AIOE | analysis_ready.csv | Pending RTM processing |
| 07 | Descriptive figures | typology_positions.csv, RTM aggregate data | scatter plot, preference figures | Executable |
| 08 | Multilevel regression | analysis_ready.csv | model_results.txt, coefficient plots | Pending Script 06 |

---

## Key variable codebooks

### RTM redistribution items (both waves)
Look in Core Questionnaire PDFs for exact wording. Typically:
- Items on wealth taxation ("Government should tax the wealthy more")
- Items on income inequality ("Government should reduce income differences")
- Measured on 5-10 point Likert scales
- 2022 uses q2/q3 blocks for preferences
- 2024 uses q2a-q2l and q3a-q3m for expanded preference items

### RTM social investment items (both waves)
- Education/retraining investment priorities (q9a-q9g in 2024)
- Willingness to pay for social programs
- Government responsibility for worker support

### RTM automation/AI items (2024 primarily)
- q4: AI impact perceptions (positive vs. negative)
- q5-q7: Retraining necessity, job security concerns
- q21-q22: Trust in government use of AI; AI skepticism
- Note: 2022 wave did not include automation module; 2024 is first comprehensive coverage

### RTM employment status (both waves)
- s4: Employment status (employed, unemployed, inactive, student, retired, other)
- s5: Employment type (permanent, temporary, self-employed, part-time, gig, etc.)
- s6: Additional employment detail (contract duration, working hours)
- Insider/outsider coding possible by combining s4-s6

### Income and education (both waves)
- **Income:** s8 in 2022 (multiple formats: decile, equivalized, standard); s9_dec in 2024 (income decile)
- **Education:** s6 in 2022 with categorical vars (s6_cat2/cat3); s7_cat3 in 2024
- Both use education attainment (ISCED or national equivalents)

---

## Technical notes

### Country coverage
- **RTM 2022:** 27+ OECD countries (check ctrcode in microdata)
- **RTM 2024:** 27+ OECD countries (same sampling frame)
- **EPL:** 43 countries including non-OECD (filter for OECD subset for merge)
- **PIAAC:** 32 countries (OECD + partners)
- **ESS:** ~30 European countries (ISO2 codes; requires conversion to ISO3)

### Recommended merge keys
- Country level: ISO3 code (standardize all sources to this)
- Individual level in RTM: ctrcode (country numeric) + id (respondent ID)
- Occupation: s9 or s10 (RTM) → manual ISCO mapping or external crosswalk

### Survey weights
- **RTM:** Use `weight` variable for national-representative estimates
- **PIAAC:** Country-level aggregate exports; individual weights in PUFs (not yet downloaded)
- **ESS:** Not available in country-level exports; available in full microdata after registration

### Missing data handling
- RTM: Check for negative codes indicating refusal, don't know, not applicable
- PIAAC: "—" indicates missing or not collected
- EPL: No missing values in version 4; imputation done by OECD

---

## File manifest (complete list)

### data/raw/ (~1.1 GB)
- oecd_epl_v4.csv (150 KB)
- oecd_epl_overview_all-versions_v1-v4.csv (760 KB) [duplicate/archive version]
- piaac_cycle2_summary.xls (38 KB)
- prg[COUNTRY]p2.csv (32 country files, ~30-113 MB each; total ~1.4 GB)
- AIOE_DataAppendix.xlsx (167 KB)
- isco_soc_crosswalk.xls (304 KB)
- 2022_RTM.xlsx (522 KB)
- 2024-RTM.xlsx (5.9 MB)
- estat_lfsi_pt_a_en.csv (3.4 MB)
- gincdif-cntry.xlsx (9.5 KB)
- stfedu-cntry.xlsx (11 KB)
- stfhlth-cntry.xlsx (11 KB)

### data/processed/ (~540 KB)
- epl_gap.csv (2.4 KB)
- task_profile.csv (3.8 KB)
- typology_positions.csv (6.5 KB)
- aioe_isco08.csv (29 KB)
- aioe_isco08_2digit.csv (1 KB)
- eurostat_emp_by_isco.csv (485 KB)
- pca_aioe_validation.csv (1.2 KB)

### data/OECD_RTM_2022_Public_Use_Microdata/ (~99 MB)
- OECD_RTM_2022_Public_Use_Microdata.zip (7.6 MB) [archive]
- **OECD-RTM-Technical-Documentation-Survey-Design.pdf (1.6 MB)** — Technical documentation for RTM survey design and methodology (covers 2018-2024 waves)
- OECD-Risks-That-Matter-2022-Background-Questionnaire.pdf (280 KB)
- OECD-Risks-That-Matter-2022-Core-Questionnaire.pdf (349 KB)
- Terms_Conditions_OECD_RTM_microdata.pdf (99 KB)
- FinalData_dta.zip (7.4 MB) [archive]
- FinalData_dta/FinalData_dta/OECD_RTM_2022_Public_Use_Microdata.dta (90 MB) [extracted]

### data/OECD_RTM_2024_Public_Use_Microdata/ (~14 MB)
- OECD_RTM_2024_Public_Use_Microdata.zip (2.9 MB) [archive]
- **OECD-RTM-2024-Main-Findings-Report.pdf (2.3 MB)** — Official OECD published report with key findings and policy implications from 2024 RTM survey
- OECD-Risks-That-Matter-2024-Background-Questionnaire.pdf (529 KB)
- OECD-Risks-That-Matter-2024-Core-Questionnaire.pdf (339 KB)
- OECD_Risks_that_Matter_2024_Terms_and_Conditions_PUMF.pdf (57 KB)
- OECD_RTM_2024_Public_Use_Microdata.zip (2.1 MB) [archive]
- OECD_RTM_2024_Public_Use_Microdata/OECD_RTM_2024_Public_Use_Microdata.dta (8.5 MB) [extracted]

---

**Documentation auto-generated on 2026-04-08 via Python scanning of data/ tree.**
**Manual notes from previous documentation preserved at top of this file.**
