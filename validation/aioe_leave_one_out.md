# AIOE Validation: Leave-One-Out Sensitivity

**Date:** 2026-04-17

Drops each of the 21 European countries one at a time and recomputes the Pearson r between PIAAC task-profile PC1 and employment-weighted Felten AIOE. Full-sample baseline: r = 0.7087, rho = 0.6987.

| Dropped | r | delta_r | rho | Flag |
|---|---|---|---|---|
| HUN | 0.6684 | -0.0403 | 0.6632 | influential (pulls r up) |
| CHE | 0.6689 | -0.0397 | 0.6737 | |
| ITA | 0.6853 | -0.0234 | 0.6797 | |
| NOR | 0.6886 | -0.0201 | 0.6887 | |
| SVK | 0.6893 | -0.0194 | 0.6812 | |
| CZE | 0.6901 | -0.0186 | 0.6812 | |
| BEL | 0.6966 | -0.0121 | 0.6887 | |
| IRL | 0.7011 | -0.0076 | 0.6887 | |
| POL | 0.7058 | -0.0029 | 0.6872 | |
| DEU | 0.7060 | -0.0027 | 0.7023 | |
| FRA | 0.7080 | -0.0007 | 0.6977 | |
| DNK | 0.7080 | -0.0007 | 0.6887 | |
| AUT | 0.7135 | +0.0048 | 0.6857 | |
| LVA | 0.7136 | +0.0049 | 0.6902 | |
| NLD | 0.7152 | +0.0065 | 0.6962 | |
| EST | 0.7161 | +0.0074 | 0.6902 | |
| PRT | 0.7167 | +0.0080 | 0.6902 | |
| LTU | 0.7255 | +0.0168 | 0.7158 | |
| FIN | 0.7353 | +0.0266 | 0.7068 | |
| SWE | 0.7592 | +0.0505 | 0.7639 | influential (pulls r down) |
| ESP | 0.7712 | +0.0625 | 0.7850 | influential (pulls r down) |

**Summary statistics:**
- Range of r across 21 LOO samples: 0.6684 to 0.7712 (spread: 0.103)
- Mean LOO r: 0.7087
- SD LOO r: 0.0247
- All 21 LOO correlations remain positive and significant (p < .005 in all cases; 19 of 21 with p < .001). Two correlations are p ≈ .0013 (HUN-dropped p = 0.001276, CHE-dropped p = 0.001259) — the earlier "p < .001 in all cases" phrasing was a slight overstatement, corrected here after the formalized re-run in `scripts/03c_loo_aioe.py` (see `v2_prep/docs/loo_aioe_formalization.md`).

**Interpretation:**

Spain is the single most influential country, as expected from the Section 3.1 footnote. Dropping Spain raises r from 0.71 to 0.77. This confirms Spain is a genuine outlier (high task complexity, low aggregate AIOE) but does not undermine the validation: the correlation strengthens without Spain rather than collapsing. The substantive interpretation in the footnote holds — Spain's ICT-intensive service sectors produce a task-complexity score that exceeds what its occupational composition alone would predict, which is exactly what PIAAC measures and SOC-based indices miss.

Sweden is the second most influential country (dropping it raises r to 0.76), for the mirror-image reason: Sweden has low task complexity on PIAAC but relatively high aggregate AIOE due to its high-AIOE professional/managerial employment structure.

Hungary is the most influential in the other direction (dropping it lowers r to 0.67). Hungary has the lowest task-profile score in the sample and a moderately negative AIOE, consistent with the relationship but influential because it anchors the low end of both distributions.

No single country's exclusion reverses the sign or eliminates the significance of the correlation. The validation result is not driven by any one case.

**Status:** v1.1 polish item. Not a v1.0 blocker. Could become an appendix table for the v2 journal submission.
