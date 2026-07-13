# v2 — Multilevel extension (in progress)

This directory contains an in-progress extension of the v1 typology paper to individual-level analysis. This work is under active development. Results here are preliminary and have not yet been written up; specifications and findings may change.

## What this does

The v1 paper maps OECD countries on two axes: AI task-profile composition and labor market dualization. This extension asks an individual-level question: do those structural axes moderate how a person's AI exposure relates to their welfare-state preferences? It fits multilevel models on OECD Risks That Matter (RTM) microdata (2022 and 2024 waves), with respondents nested in countries positioned by the v1 typology.

## Pipeline

> **Note:** Unlike the self-contained v1 pipeline, the v2 chain requires the restricted OECD RTM microdata (`.dta` files), which are **not** shipped in this repository (see [`../data/raw/README.md`](../data/raw/README.md)). The scripts are documented for methodological transparency; running them requires obtaining the RTM data from OECD.

The analysis runs `00 → 04 → 05 → 06 → 08`, with the dualization-gap and variable-harmonization steps as inputs.

| Script | Purpose |
|---|---|
| `00_ingest_rtm.py` | Reads the raw RTM 2022 & 2024 `.dta` microdata, writes per-wave Parquet + metadata. Isolates the `.dta` dependency to one place; no recoding. |
| `04_clean_rtm.py` | Pools the two per-wave Parquets into one analytic dataset, applying the rename/recode rules in `variable_mapping_2022_2024.csv`; writes a verification log. |
| `05_build_nace_aiie.py` | Builds the 21-row NACE-section AI Industry Exposure (AIIE) lookup, crosswalking Felten NAICS-4 → ISIC-4 → NACE, employment-weighted by BLS QCEW 2023. (Lookup table only; the per-respondent join is in Script 06.) |
| `06_merge_country_level.py` | The individual×country merge: joins pooled RTM respondents to country covariates — per-respondent AIIE (via NACE sector), v1 typology axes, dualization gaps, SOCX welfare, GDP per capita — producing the analytic dataset. |
| `08_multilevel_regression.R` | The multilevel models. Part A: pooled objective-exposure typology models (M0–M6, random slopes, cross-level interactions). Part B: 2024 subjective-fear redescription (M7) and descriptive cleavage-shape. Inference: REML with Satterthwaite/Kenward-Roger df, bootstrap CIs, CR2 cluster-robust SEs, and brms as a co-primary check on variance components. |
| `08_packages.R` | Installs and verifies the R toolchain (lme4, lmerTest, pbkrtest, clubSandwich, WeMix, brms, arrow) and checks for the Rtools45 build tools brms needs. |
| `01b_compute_weighted_gap.py` | Conditional involuntary-temp-weighted dualization gap (Axis-2 robustness), from Eurostat `lfsa_etgar`. *One-shot in-place mutator — not re-runnable; see `01c`.* |
| `01c_unconditional_weighted_gap.py` | Unconditional (Häusermann–Schwander) weighted gap as a separate, idempotent step, based on all salaried employees (Eurostat `lfsi_pt_a`). |

The `build_*_mapping.py` scripts (10 files) each construct one thematic block of `variable_mapping_2022_2024.csv` — the harmonization contract that aligns individual RTM variables across the 2022 and 2024 waves (one row per analytic item, recording each wave's source variable and recode rules). Together they generate the mapping that `04_clean_rtm.py` consumes.

## Results

`output/` contains preliminary model results: fixed-effect coefficient tables (`coef_table_*.csv`), variance components and model metadata (`model_meta_*.csv`), cross-level interaction inference (`headline_inference_M4.csv`), and a robustness panel (`robustness_panel.csv`). Fitted model objects are not included (large; restricted-data-derived).

## Status

Active work in progress. Measurement and specification decisions are tracked in a separate research log not included in this public repository.
