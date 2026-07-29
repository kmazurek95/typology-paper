# Institutional Configurations and the Social Politics of AI

A two-dimensional typology of OECD countries based on the type of AI effect their workforces face (displacement vs. complementarity) and the depth of labor market dualization (employment protection gap between permanent and temporary workers).

This repository contains two related bodies of work:

- **v1: Typology paper (working paper, complete).** The two-dimensional country typology described below, with illustrative preference evidence. The material in `scripts/`, `data/`, and `figures/` corresponds to this paper.
- **v2: Multilevel extension (in progress).** An individual-level multilevel analysis testing whether the typology's two axes moderate how AI exposure relates to welfare-state preferences, using OECD Risks That Matter microdata (2022 and 2024). This work lives in `v2_prep/` and is in active development; the results there are preliminary and not yet written up.

## Paper

**Working paper:** [Mazurek_2026_Typology_v1.pdf](./Mazurek_2026_Typology_v1.pdf)

**Preprint:** SocArXiv DOI pending.

## Citation

Mazurek, K. (2026). Institutional Configurations and the Social Politics of AI: A Two-Dimensional Typology of OECD Countries. Working Paper v1.0.

```bibtex
@unpublished{mazurek2026typology,
  author = {Mazurek, Kaleb},
  title  = {Institutional Configurations and the Social Politics of AI: A Two-Dimensional Typology of OECD Countries},
  note   = {Working Paper v1.0},
  year   = {2026}
}
```

## Repository structure

```text
scripts/        v1 pipeline: PIAAC/EPL/AIOE → typology
data/           public inputs + processed typology outputs
figures/        v1 figures
v2_prep/        v2 multilevel extension (in progress; see v2_prep/README.md)
```

The `v2_prep/` directory contains an in-progress extension and is not part of the v1 paper. See [`v2_prep/README.md`](v2_prep/README.md) for its status and contents.

## Getting started

1. Clone the repo and install dependencies:
   ```
   git clone https://github.com/kmazurek95/typology-paper.git
   cd typology-paper
   pip install -r requirements.txt
   ```

2. Download the PIAAC Cycle 2 Public Use Files (~1.5 GB, 31 country-level CSVs). These are freely available but too large for GitHub. See [`data/raw/README.md`](data/raw/README.md) for the download URL and file list.

3. Run the pipeline from the repo root, **in this order**:
   ```
   python scripts/01_clean_epl.py
   python scripts/02_clean_piaac.py
   python scripts/03_crosswalk_aioe.py
   python scripts/05_merge_typology.py     # must precede 03b
   python scripts/03b_validate_aioe.py
   python scripts/03c_loo_aioe.py
   python scripts/07_descriptive.py
   ```

   **Order note.** `03b_validate_aioe.py` reads `data/processed/typology_positions.csv`,
   which `05_merge_typology.py` writes — so 05 must run first. Earlier versions of this
   README listed 03b before 05; because `data/processed/` is committed, that ordering did
   not error, it silently validated against the *committed* typology positions instead of
   the ones just rebuilt. If you want a genuinely clean rebuild, clear `data/processed/`
   first so no stale intermediate can be picked up.

4. Outputs appear at `figures/figure1_typology_scatter.png` (Figure 1), `figures/figure2_preferences_by_cluster.png` (Figure 2), and `data/processed/typology_positions.csv` (country-level data).

> ### ⚠️ If you also use the v2 chain, re-run the weighted-gap steps afterwards
>
> `v2_prep/scripts/01b_compute_weighted_gap.py` and `01c_unconditional_weighted_gap.py`
> mutate `epl_gap.csv` and `typology_positions.csv` **in place** after Script 05 has
> written them: they add the weighted-dualization columns and rename `dualization_gap`
> → `dualization_gap_raw`. The v2 chain
> (`v2_prep/scripts/06_merge_country_level.py`) reads those added columns.
>
> Re-running the v1 pipeline above regenerates both files from scratch and **strips
> everything 01b/01c added**, which breaks v2. Scripts 01 and 05 now print a loud warning
> naming the dropped columns when this happens. To restore them:
>
> ```
> python v2_prep/scripts/01b_compute_weighted_gap.py
> python v2_prep/scripts/01c_unconditional_weighted_gap.py
> ```
>
> Run 01b **exactly once** per v1 rebuild — it asserts the pre-rename `dualization_gap`
> column, so it succeeds after a fresh Script 01 but fails if run twice in a row. 01c is
> idempotent and safe to re-run.

## Scripts

| Script | Description |
|---|---|
| `01_clean_epl.py` | Computes the dualization gap (EPRC - EPT) from OECD EPL Version 4 |
| `02_clean_piaac.py` | Computes country-level task profiles from PIAAC skill-use indices, runs PCA |
| `03_crosswalk_aioe.py` | Maps Felten AIOE scores from US SOC codes to ISCO-08 |
| `03b_validate_aioe.py` | External validation: correlates PIAAC PC1 with employment-weighted AIOE |
| `05_merge_typology.py` | Merges both axes, standardizes, assigns countries to four cells |
| `07_descriptive.py` | Produces the typology scatter plot and preference comparison figure |
| `plot_aioe_validation.py` | Produces the AIOE validation scatter plot (Figure A1) |
| `utils.py` | Shared paths, country code mappings, plot style |

## Data

Public raw data files ship in `data/raw/`: OECD EPL sub-indices, Felten AIOE scores, BLS SOC-to-ISCO crosswalk, Eurostat temporary employment shares, and RTM 2022 Collected Statlinks. PIAAC Public Use Files and RTM individual-level microdata are excluded for size and licensing reasons; the RTM microdata is the basis for the v2 multilevel extension in `v2_prep/`. `data/raw/README.md` documents where to obtain each excluded file. `scripts/03b_validate_aioe.py` auto-downloads the Eurostat LFS employment-by-ISCO table it needs on first run.

## License

Code (`scripts/`, `requirements.txt`): [MIT](./LICENSE-CODE)

Paper, data, and figures: [CC-BY-4.0](./LICENSE-DATA-AND-PAPER)

## Contact

Kaleb Mazurek — [institutional email] — Chicago, IL
