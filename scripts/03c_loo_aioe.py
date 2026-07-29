"""
Script 03c: Leave-One-Out Jackknife for AIOE External Validation

Formalizes the ad-hoc LOO jackknife run on 2026-04-17 (result table at
validation/aioe_leave_one_out.md) as a reproducible v1-pipeline script.

For each of the 21 European countries in the validation set, drops that
country and recomputes Pearson r and Spearman rho between PIAAC PC1 and
Eurostat-employment-weighted Felten AIOE. Verifies cell-by-cell against
the published table.

Inputs
------
- data/processed/pca_aioe_validation.csv  (from script 03b)
- validation/aioe_leave_one_out.md        (published reference values)

Outputs
-------
- data/processed/aioe_loo_jackknife.csv     (the LOO table)
- data/processed/aioe_loo_verification.txt  (per-row replication log)

Invocation
----------
python scripts/03c_loo_aioe.py
"""

import os
import re
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8")

import pandas as pd
from scipy import stats

from utils import PROCESSED_DIR, ROOT_DIR

# ── Configuration ──────────────────────────────────────────────────────────

VALIDATION_CSV = PROCESSED_DIR / "pca_aioe_validation.csv"
REFERENCE_MD = ROOT_DIR / "validation" / "aioe_leave_one_out.md"
OUT_CSV = PROCESSED_DIR / "aioe_loo_jackknife.csv"
OUT_LOG = PROCESSED_DIR / "aioe_loo_verification.txt"

EXPECTED_COUNTRIES = frozenset({
    "AUT", "BEL", "CHE", "CZE", "DEU", "DNK", "ESP", "EST", "FIN", "FRA",
    "HUN", "IRL", "ITA", "LTU", "LVA", "NLD", "NOR", "POL", "PRT", "SVK",
    "SWE",
})

# Published reference values from validation/aioe_leave_one_out.md (2026-04-17)
PUBLISHED_BASELINE_R = 0.7087
PUBLISHED_BASELINE_RHO = 0.6987
PUBLISHED_BASELINE_P = 0.000323
PUBLISHED_MEAN_LOO_R = 0.7087
PUBLISHED_SD_LOO_R = 0.0247
PUBLISHED_ESP_R = 0.7712
PUBLISHED_HUN_R = 0.6684

TOLERANCE = 5e-5  # tighter than 4 decimal places to avoid rounding-edge ties


# ── 1. Load input contract ─────────────────────────────────────────────────


def load_validation_frame() -> pd.DataFrame:
    """Load the 21-country merged frame written by 03b_validate_aioe.py."""
    df = pd.read_csv(VALIDATION_CSV)

    # Defensive checks — fail loudly per spec
    assert len(df) == 21, (
        f"Expected 21 countries in pca_aioe_validation.csv, found {len(df)}. "
        f"Upstream 03b output has drifted; re-run 03b before continuing."
    )
    actual_countries = set(df["country_iso3"])
    assert actual_countries == EXPECTED_COUNTRIES, (
        f"Country set mismatch.\n"
        f"  Expected: {sorted(EXPECTED_COUNTRIES)}\n"
        f"  Found:    {sorted(actual_countries)}\n"
        f"  Missing:  {sorted(EXPECTED_COUNTRIES - actual_countries)}\n"
        f"  Extra:    {sorted(actual_countries - EXPECTED_COUNTRIES)}"
    )
    assert not df[["task_profile_pc1", "mean_aioe"]].isna().any().any(), (
        "NaN values in task_profile_pc1 or mean_aioe — input data corrupt."
    )
    return df


# ── 2. Parse published reference table ─────────────────────────────────────


def parse_published_table() -> dict[str, dict[str, float]]:
    """Parse the per-country (r, delta_r, rho) values from the reference .md.

    Returns a dict keyed by ISO3 country code with sub-keys 'r', 'delta_r', 'rho'.
    """
    text = REFERENCE_MD.read_text(encoding="utf-8")
    rows: dict[str, dict[str, float]] = {}

    # Match rows like: | HUN | 0.6684 | -0.0403 | 0.6632 | influential ... |
    row_re = re.compile(
        r"^\|\s*([A-Z]{3})\s*\|\s*"
        r"(-?\d+\.\d+)\s*\|\s*"
        r"([+-]?\d+\.\d+)\s*\|\s*"
        r"(-?\d+\.\d+)\s*\|",
        re.MULTILINE,
    )
    for m in row_re.finditer(text):
        iso3, r_str, dr_str, rho_str = m.groups()
        rows[iso3] = {
            "r": float(r_str),
            "delta_r": float(dr_str),
            "rho": float(rho_str),
        }

    assert len(rows) == 21, (
        f"Failed to parse 21 country rows from {REFERENCE_MD}; "
        f"got {len(rows)}: {sorted(rows)}"
    )
    return rows


# ── 3. Compute baseline ────────────────────────────────────────────────────


def compute_baseline(df: pd.DataFrame) -> tuple[float, float, float, float]:
    """Return (r, p_r, rho, p_rho) on the full 21-country frame."""
    r, p_r = stats.pearsonr(df["task_profile_pc1"], df["mean_aioe"])
    rho, p_rho = stats.spearmanr(df["task_profile_pc1"], df["mean_aioe"])
    return r, p_r, rho, p_rho


# ── 4. Compute LOO table ───────────────────────────────────────────────────


def compute_loo_table(df: pd.DataFrame, baseline_r: float) -> pd.DataFrame:
    """For each country, drop and recompute r, rho on the remaining 20."""
    records = []
    for iso3 in sorted(df["country_iso3"]):
        sub = df[df["country_iso3"] != iso3]
        assert len(sub) == 20, f"LOO subset for {iso3} has {len(sub)} rows, expected 20"

        r, p_r = stats.pearsonr(sub["task_profile_pc1"], sub["mean_aioe"])
        rho, p_rho = stats.spearmanr(sub["task_profile_pc1"], sub["mean_aioe"])

        records.append({
            "dropped_country": iso3,
            "n_remaining": len(sub),
            "r_pearson": r,
            "r_pearson_p": p_r,
            "rho_spearman": rho,
            "rho_spearman_p": p_rho,
            "shift_from_baseline": r - baseline_r,
            "significant": bool(p_r < 0.001),
        })

    out = pd.DataFrame.from_records(records)
    return out.sort_values("shift_from_baseline", ascending=False).reset_index(drop=True)


# ── 5. Verification log ────────────────────────────────────────────────────


def matches(computed: float, published: float, tol: float = TOLERANCE) -> bool:
    return abs(computed - published) < tol


def write_verification_log(
    *,
    baseline_r: float,
    baseline_rho: float,
    baseline_p: float,
    loo: pd.DataFrame,
    published: dict[str, dict[str, float]],
) -> bool:
    """Write the verification log. Returns True iff every check passed."""
    lines: list[str] = []
    failures: list[str] = []

    def check(label: str, computed: float, pub: float, tol: float = TOLERANCE) -> None:
        ok = matches(computed, pub, tol)
        status = "PASS" if ok else "FAIL"
        diff = abs(computed - pub)
        lines.append(
            f"  [{status}] {label}: published={pub:.4f}, computed={computed:.4f}, "
            f"|Δ|={diff:.6f}"
        )
        if not ok:
            failures.append(f"{label}: |Δ|={diff:.6f} exceeds tol={tol}")

    lines.append(f"AIOE LOO Jackknife — Verification Log")
    lines.append(f"Run: {datetime.now().isoformat(timespec='seconds')}")
    lines.append(f"Source script: scripts/03c_loo_aioe.py")
    lines.append(f"Reference: validation/aioe_leave_one_out.md (2026-04-17)")
    lines.append("")
    lines.append("─" * 70)
    lines.append("Baseline replication (full 21-country sample)")
    lines.append("─" * 70)
    check("baseline Pearson r", baseline_r, PUBLISHED_BASELINE_R)
    check("baseline Spearman ρ", baseline_rho, PUBLISHED_BASELINE_RHO)
    check("baseline p-value", baseline_p, PUBLISHED_BASELINE_P, tol=5e-6)

    lines.append("")
    lines.append("─" * 70)
    lines.append("Tail-anchor replication")
    lines.append("─" * 70)
    esp = loo[loo["dropped_country"] == "ESP"].iloc[0]
    hun = loo[loo["dropped_country"] == "HUN"].iloc[0]
    check("ESP-dropped r (largest +Δ)", float(esp["r_pearson"]), PUBLISHED_ESP_R)
    check("HUN-dropped r (largest −Δ)", float(hun["r_pearson"]), PUBLISHED_HUN_R)

    lines.append("")
    lines.append("─" * 70)
    lines.append("LOO summary-statistic replication")
    lines.append("─" * 70)
    mean_r = float(loo["r_pearson"].mean())
    # NB: the 2026-04-17 ad-hoc run used numpy's default ddof=0 (population SD).
    # pandas .std() defaults to ddof=1 (sample SD), which would give 0.0253
    # and would not match the published 0.0247. Use ddof=0 to match the
    # published convention.
    sd_r = float(loo["r_pearson"].std(ddof=0))
    check("mean LOO r", mean_r, PUBLISHED_MEAN_LOO_R)
    check("SD LOO r (ddof=0, matches published)", sd_r, PUBLISHED_SD_LOO_R)

    lines.append("")
    lines.append("─" * 70)
    lines.append("Cell-by-cell diff against validation/aioe_leave_one_out.md")
    lines.append("─" * 70)
    matched = 0
    cell_failures: list[str] = []
    for _, row in loo.iterrows():
        iso3 = row["dropped_country"]
        pub = published[iso3]
        r_ok = matches(float(row["r_pearson"]), pub["r"])
        rho_ok = matches(float(row["rho_spearman"]), pub["rho"])
        if r_ok and rho_ok:
            matched += 1
        else:
            cell_failures.append(
                f"  {iso3}: "
                f"r published={pub['r']:.4f} computed={float(row['r_pearson']):.4f} "
                f"|Δ|={abs(float(row['r_pearson']) - pub['r']):.6f} "
                f"{'OK' if r_ok else 'FAIL'} | "
                f"ρ published={pub['rho']:.4f} computed={float(row['rho_spearman']):.4f} "
                f"|Δ|={abs(float(row['rho_spearman']) - pub['rho']):.6f} "
                f"{'OK' if rho_ok else 'FAIL'}"
            )
    overall = "PASS" if matched == 21 else "FAIL"
    lines.append(f"  [{overall}] {matched}/21 rows match on both r and ρ to 4 decimal places")
    if cell_failures:
        lines.append("")
        lines.append("  Failing rows:")
        lines.extend(cell_failures)
        failures.append(f"Cell-by-cell diff: only {matched}/21 rows match")

    lines.append("")
    lines.append("─" * 70)
    # Tests the CORRECTED claim, not the original one. The original .md said
    # "p < .001 in all cases"; the formalized re-run showed that is a slight
    # overstatement (19/21 at p < .001; HUN-dropped p = 0.001276, CHE-dropped
    # p = 0.001259), and validation/aioe_leave_one_out.md was corrected on
    # 2026-04-17 to "p < .005 in all cases; 19 of 21 with p < .001".
    # Asserting the superseded claim made this script exit 1 on every run
    # forever, which hides a genuine regression inside a known failure. The
    # thresholds below encode what the .md now says, so a FAIL here again means
    # something actually moved.
    lines.append("'All 21 positive, p < .005 all, >= 19/21 at p < .001' check")
    lines.append("─" * 70)
    all_positive = bool((loo["r_pearson"] > 0).all())
    n_below_001 = int((loo["r_pearson_p"] < 0.001).sum())
    n_below_005 = int((loo["r_pearson_p"] < 0.005).sum())
    n_below_05 = int((loo["r_pearson_p"] < 0.05).sum())
    max_p = float(loo["r_pearson_p"].max())
    max_p_country = loo.loc[loo["r_pearson_p"].idxmax(), "dropped_country"]
    all_significant = (n_below_005 == 21) and (n_below_001 >= 19)
    lines.append(f"  All 21 r > 0:               {all_positive}")
    lines.append(f"  Count with p < .001:        {n_below_001}/21  (expect >= 19)")
    lines.append(f"  Count with p < .005:        {n_below_005}/21  (expect 21)")
    lines.append(f"  Count with p < .05:         {n_below_05}/21")
    lines.append(f"  Max p_pearson observed:     {max_p:.6f} (dropped: {max_p_country})")
    if not (all_positive and all_significant):
        failures.append(
            f"LOO significance has moved away from the corrected published claim "
            f"in validation/aioe_leave_one_out.md ('p < .005 in all cases; 19 of "
            f"21 with p < .001'). Observed: all positive = {all_positive}; "
            f"{n_below_005}/21 at p < .005 (expected 21); {n_below_001}/21 at "
            f"p < .001 (expected at least 19); max p = {max_p:.6f} when dropping "
            f"{max_p_country}. Either pca_aioe_validation.csv has drifted "
            f"(re-run 03b_validate_aioe.py) or the .md needs updating again."
        )

    lines.append("")
    lines.append("=" * 70)
    overall_status = "PASS" if not failures else "FAIL"
    lines.append(f"OVERALL: {overall_status}")
    if failures:
        lines.append("")
        lines.append("Failure summary:")
        for f in failures:
            lines.append(f"  - {f}")
    lines.append("=" * 70)
    lines.append("")
    lines.append(
        "Note: any FAIL above means either pca_aioe_validation.csv has drifted "
        "since 2026-04-17 (re-run 03b_validate_aioe.py) or the published "
        "reference at validation/aioe_leave_one_out.md needs updating. "
        "Both are findings worth investigating before trusting downstream uses."
    )

    OUT_LOG.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return not failures


# ── 6. Console output ──────────────────────────────────────────────────────


def print_console_summary(
    *,
    baseline_r: float,
    baseline_rho: float,
    baseline_p: float,
    loo: pd.DataFrame,
    published: dict[str, dict[str, float]],
) -> None:
    print("=" * 70)
    print("Baseline (full 21-country sample)")
    print("=" * 70)
    print(f"  N        = 21")
    print(f"  Pearson  r   = {baseline_r:.4f} (published: {PUBLISHED_BASELINE_R})")
    print(f"  Spearman ρ   = {baseline_rho:.4f} (published: {PUBLISHED_BASELINE_RHO})")
    print(f"  p-value      = {baseline_p:.6f} (published: {PUBLISHED_BASELINE_P})")
    print()

    print("=" * 70)
    print("LOO summary")
    print("=" * 70)
    print(f"  min r    = {loo['r_pearson'].min():.4f} "
          f"(dropped: {loo.loc[loo['r_pearson'].idxmin(), 'dropped_country']})")
    print(f"  max r    = {loo['r_pearson'].max():.4f} "
          f"(dropped: {loo.loc[loo['r_pearson'].idxmax(), 'dropped_country']})")
    print(f"  mean r   = {loo['r_pearson'].mean():.4f} (published: {PUBLISHED_MEAN_LOO_R})")
    print(f"  SD r     = {loo['r_pearson'].std(ddof=0):.4f} (published: {PUBLISHED_SD_LOO_R}, ddof=0)")
    print()

    print("=" * 70)
    print("Per-country PASS/FAIL (4 decimal-place tolerance)")
    print("=" * 70)
    for _, row in loo.iterrows():
        iso3 = row["dropped_country"]
        pub = published[iso3]
        r_ok = matches(float(row["r_pearson"]), pub["r"])
        rho_ok = matches(float(row["rho_spearman"]), pub["rho"])
        status = "PASS" if (r_ok and rho_ok) else "FAIL"
        print(f"  [{status}] {iso3}: r = {row['r_pearson']:.4f} "
              f"(pub {pub['r']:.4f}), ρ = {row['rho_spearman']:.4f} "
              f"(pub {pub['rho']:.4f})")
    print()

    all_positive = bool((loo["r_pearson"] > 0).all())
    n_below_001 = int((loo["r_pearson_p"] < 0.001).sum())
    n_below_005 = int((loo["r_pearson_p"] < 0.005).sum())
    max_p = float(loo["r_pearson_p"].max())
    max_p_country = loo.loc[loo["r_pearson_p"].idxmax(), "dropped_country"]
    # Mirrors the corrected thresholds asserted in build_verification_log().
    all_significant = (n_below_005 == 21) and (n_below_001 >= 19)
    overall_claim = "PASS" if (all_positive and all_significant) else "FAIL"
    print("=" * 70)
    print(f"  [{overall_claim}] All 21 LOO correlations positive, p < .005 in all "
          f"cases,")
    print(f"         >= 19/21 at p < .001 (corrected published claim)")
    print(f"        All 21 positive: {all_positive}")
    print(f"        Count p < .001:  {n_below_001}/21  (expect >= 19)")
    print(f"        Count p < .005:  {n_below_005}/21  (expect 21)")
    print(f"        Max p observed:  {max_p:.6f} (dropped: {max_p_country})")
    print("=" * 70)


# ── 7. Main ────────────────────────────────────────────────────────────────


def main() -> int:
    df = load_validation_frame()
    published = parse_published_table()
    baseline_r, baseline_p, baseline_rho, _ = compute_baseline(df)

    # Spec: stop immediately if baseline doesn't replicate.
    if not matches(baseline_r, PUBLISHED_BASELINE_R):
        print(
            f"FATAL: baseline Pearson r = {baseline_r:.6f} does not match "
            f"published {PUBLISHED_BASELINE_R:.4f} to 4 decimal places. "
            f"Either pca_aioe_validation.csv has drifted since 2026-04-17 "
            f"or the validation subset has changed.",
            file=sys.stderr,
        )
        return 2

    loo = compute_loo_table(df, baseline_r)
    loo.to_csv(OUT_CSV, index=False)

    log_ok = write_verification_log(
        baseline_r=baseline_r,
        baseline_rho=baseline_rho,
        baseline_p=baseline_p,
        loo=loo,
        published=published,
    )

    print_console_summary(
        baseline_r=baseline_r,
        baseline_rho=baseline_rho,
        baseline_p=baseline_p,
        loo=loo,
        published=published,
    )

    print()
    print(f"Wrote {OUT_CSV} ({len(loo)} rows)")
    print(f"Wrote {OUT_LOG}")
    print()

    if not log_ok:
        print("OVERALL: FAIL — see verification log for details.", file=sys.stderr)
        return 1

    print("OVERALL: PASS — every replication check matched to 4 decimal places.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
