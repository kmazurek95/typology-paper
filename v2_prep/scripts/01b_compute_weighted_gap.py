"""
Script 01b: Axis 2 weighted-gap robustness construction

Implements decision S2 from v2_measurement_decisions_log.md: stages the
involuntary-temp-weighted dualization gap as a robustness specification
alongside the raw EPRC - EPT primary measure.

Inputs
------
- data/raw/eurostat_lfsa_etgar.csv             (staged 2026-05-26)
- data/processed/epl_gap.csv                   (v1 primary measure, raw gap)
- data/processed/typology_positions.csv        (v1 typology cluster file)
- v2_prep/docs/lfsa_etgar_coverage_check_2026-05-26.md  (exclusion rules)

Outputs
-------
- data/processed/epl_gap.csv (updated with the weighted-gap columns)
- data/processed/typology_positions.csv (same; clusters unchanged)

Construction
------------
For each RTM country with Eurostat coverage:
    invol_temp_share_pct = Eurostat lfsa_etgar value at TIME_PERIOD = wave year
    dualization_gap_weighted = dualization_gap_raw * (invol_temp_share / 100)

Coverage check document (lfsa_etgar_coverage_check_2026-05-26.md) hard-excludes
six countries: CHL, ISR, KOR, MEX (no Eurostat coverage), LVA (coverage ends
2021), EST (low-reliability flags across the period). Their weighted-gap
values are NaN.

Eurostat introduced a break in series at 2021. Construction uses only
post-break values: 2022 for the 2022-wave columns, 2024 for the 2024-wave
columns. Per coverage check, the 2024 value is also the "headline" (most
recent post-break) value used in the brief's primary weighted column.

Cluster assignments are NOT recomputed; the raw dualization_gap_raw remains
the clustering input. The weighted gap is a separate column for downstream
regressions.

Invocation
----------
python v2_prep/scripts/01b_compute_weighted_gap.py
"""

import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from utils import ISO2_TO_ISO3  # noqa: E402

RAW_EUROSTAT = ROOT / "data" / "raw" / "eurostat_lfsa_etgar.csv"
EPL_GAP = ROOT / "data" / "processed" / "epl_gap.csv"
TYPOLOGY = ROOT / "data" / "processed" / "typology_positions.csv"

# Hard exclusions per the coverage check document (in ISO3)
HARD_EXCLUDE = frozenset({"CHL", "ISR", "KOR", "MEX", "LVA", "EST"})


# ── 1. Load and reshape Eurostat lfsa_etgar ────────────────────────────────


def load_eurostat() -> pd.DataFrame:
    """Load the filtered lfsa_etgar artifact and convert to (iso3, year) frame."""
    df = pd.read_csv(RAW_EUROSTAT, dtype=str)

    # Defensive: confirm we're looking at the target filter slice only
    assert (df["unit"] == "PC_SAL_TEMP").all(), "unexpected unit values"
    assert (df["sex"] == "T").all(), "unexpected sex values"
    assert (df["age"] == "Y15-64").all(), "unexpected age values"
    assert (df["reason"] == "NF_PJOB").all(), "unexpected reason values"

    # ISO2 -> ISO3 (Greece special case: EL -> GRC handled by utils mapping)
    df["country_iso3"] = df["geo"].map(ISO2_TO_ISO3)
    # Drop aggregates (EU27_2020, EA21) and any geo not in our ISO2 map
    df = df[df["country_iso3"].notna()].copy()

    # Numeric value (preserve flag for diagnostics)
    df["OBS_VALUE_num"] = pd.to_numeric(df["OBS_VALUE"], errors="coerce")
    df["year"] = df["TIME_PERIOD"].astype(int)

    return df[["country_iso3", "year", "OBS_VALUE_num", "OBS_FLAG"]].rename(
        columns={"OBS_VALUE_num": "invol_temp_share_pct"}
    )


# ── 2. Compute per-country involuntary-temp share at 2022 + 2024 ──────────


def country_year_shares(eurostat: pd.DataFrame) -> pd.DataFrame:
    """Reshape to one row per country with 2022 and 2024 columns.

    Applies the hard-exclude list and the 2023-substitution rule (use 2023 for
    the 2022 wave when 2022 is missing but 2023 is present).
    """
    wide = (
        eurostat.pivot_table(
            index="country_iso3",
            columns="year",
            values="invol_temp_share_pct",
            aggfunc="first",
        )
        .reset_index()
    )
    # Ensure all required year columns exist
    for y in (2020, 2021, 2022, 2023, 2024):
        if y not in wide.columns:
            wide[y] = np.nan

    substitutions = []
    invol_2022 = []
    invol_2024 = []
    for _, row in wide.iterrows():
        iso3 = row["country_iso3"]
        v22, v23, v24 = row[2022], row[2023], row[2024]

        if iso3 in HARD_EXCLUDE:
            invol_2022.append(np.nan)
            invol_2024.append(np.nan)
            continue

        # 2022-wave column
        if pd.notna(v22):
            invol_2022.append(float(v22))
        elif pd.notna(v23):
            invol_2022.append(float(v23))
            substitutions.append({"iso3": iso3, "wave_year": 2022, "substituted_from": 2023, "value": float(v23)})
        else:
            invol_2022.append(np.nan)

        # 2024-wave column (no fallback per brief; 2024 either present or NaN)
        invol_2024.append(float(v24) if pd.notna(v24) else np.nan)

    out = pd.DataFrame({
        "country_iso3": wide["country_iso3"],
        "invol_temp_share_pct_2022": invol_2022,
        "invol_temp_share_pct_2024": invol_2024,
    })

    return out, substitutions


# ── 3. Merge into epl_gap.csv and typology_positions.csv ───────────────────


def update_epl_gap(shares: pd.DataFrame) -> tuple[pd.DataFrame, list[str], list[str]]:
    """Update epl_gap.csv with the weighted-gap columns. Returns (df, asserts_pass, asserts_fail)."""
    orig = pd.read_csv(EPL_GAP)
    assert "dualization_gap" in orig.columns, "expected existing dualization_gap col"
    assert "country_iso3" in orig.columns

    # Rename existing column for clarity
    df = orig.rename(columns={"dualization_gap": "dualization_gap_raw"}).copy()

    # Merge involuntary-temp shares (left join — keep all v1 countries)
    df = df.merge(shares, on="country_iso3", how="left")

    # Weighted columns (per-wave); headline matches the brief's
    # dualization_gap_weighted column = use 2024 (most recent post-break)
    df["dualization_gap_weighted_2022"] = (
        df["dualization_gap_raw"] * df["invol_temp_share_pct_2022"] / 100.0
    )
    df["dualization_gap_weighted_2024"] = (
        df["dualization_gap_raw"] * df["invol_temp_share_pct_2024"] / 100.0
    )
    # Per the brief's literal spec: a single "dualization_gap_weighted" column.
    # Use 2024 values (most recent post-break observation; captures
    # current-state weighting most relevant to the 2024 RTM wave).
    df["dualization_gap_weighted"] = df["dualization_gap_weighted_2024"]
    df["invol_temp_share_pct"] = df["invol_temp_share_pct_2024"]

    # Defensive checks
    passes, failures = [], []

    def check(label, cond, detail=""):
        (passes if cond else failures).append(f"{label}: {detail}" if detail else label)

    # Raw values must match the original dualization_gap exactly
    matched = np.allclose(
        df["dualization_gap_raw"].values, orig["dualization_gap"].values,
        rtol=0, atol=0,
    )
    check("dualization_gap_raw values match original dualization_gap exactly",
          matched, "values differ" if not matched else "")

    # Weighted column should be NaN for exactly the 6 excluded countries
    # that ARE in the v1 epl_gap file
    in_v1 = set(orig["country_iso3"])
    expected_nan = HARD_EXCLUDE & in_v1
    actual_nan = set(df.loc[df["dualization_gap_weighted"].isna(), "country_iso3"])
    # Countries with no Eurostat coverage at all (non-EU OECD) will also be NaN
    # in addition to the hard-exclude list; account for those too.
    iso3_with_data = set(shares.loc[shares["invol_temp_share_pct_2024"].notna(), "country_iso3"])
    expected_nan_full = (in_v1 - iso3_with_data) | (HARD_EXCLUDE & in_v1)
    check(f"dualization_gap_weighted NaN for hard-excluded + no-Eurostat-coverage countries "
          f"(expected: {sorted(expected_nan_full)})",
          actual_nan == expected_nan_full,
          f"actual: {sorted(actual_nan)}")

    # Sanity: weighted should be smaller in magnitude than raw (since temp share < 1)
    non_nan = df.dropna(subset=["dualization_gap_weighted", "dualization_gap_raw"])
    rel = np.abs(non_nan["dualization_gap_weighted"]) <= np.abs(non_nan["dualization_gap_raw"])
    check("|weighted| <= |raw| for all non-NaN rows (temp share is a proportion < 1)",
          rel.all(),
          f"violations: "
          f"{non_nan[~rel][['country_iso3', 'dualization_gap_raw', 'dualization_gap_weighted']].to_dict(orient='records')}")

    return df, passes, failures


def update_typology_positions(shares: pd.DataFrame) -> tuple[pd.DataFrame, list[str], list[str]]:
    """Update typology_positions.csv with the same gap-related columns. Clusters unchanged."""
    orig = pd.read_csv(TYPOLOGY)
    assert "dualization_gap" in orig.columns
    assert "cluster" in orig.columns and "cluster_label" in orig.columns

    df = orig.rename(columns={"dualization_gap": "dualization_gap_raw"}).copy()
    df = df.merge(shares, on="country_iso3", how="left")
    df["dualization_gap_weighted_2022"] = (
        df["dualization_gap_raw"] * df["invol_temp_share_pct_2022"] / 100.0
    )
    df["dualization_gap_weighted_2024"] = (
        df["dualization_gap_raw"] * df["invol_temp_share_pct_2024"] / 100.0
    )
    df["dualization_gap_weighted"] = df["dualization_gap_weighted_2024"]
    df["invol_temp_share_pct"] = df["invol_temp_share_pct_2024"]

    passes, failures = [], []

    def check(label, cond, detail=""):
        (passes if cond else failures).append(f"{label}: {detail}" if detail else label)

    matched = np.allclose(
        df["dualization_gap_raw"].values, orig["dualization_gap"].values,
        rtol=0, atol=0,
    )
    check("typology_positions dualization_gap_raw matches original exactly",
          matched, "values differ" if not matched else "")

    clusters_unchanged = (df["cluster"].values == orig["cluster"].values).all()
    labels_unchanged = (df["cluster_label"].values == orig["cluster_label"].values).all()
    check("cluster assignments unchanged", clusters_unchanged,
          "cluster values changed (must not happen — clustering uses raw gap only)")
    check("cluster_label values unchanged", labels_unchanged, "labels changed")

    return df, passes, failures


# ── 4. Main ────────────────────────────────────────────────────────────────


def main() -> int:
    print(f"Loading Eurostat: {RAW_EUROSTAT.name}")
    es = load_eurostat()
    print(f"  Eurostat rows after ISO2->ISO3 + drop aggregates: {len(es):,}")
    print(f"  Distinct countries in Eurostat slice: {es['country_iso3'].nunique()}")

    print("\nComputing per-country involuntary-temp shares at 2022 and 2024...")
    shares, substitutions = country_year_shares(es)
    if substitutions:
        print(f"  Substitutions (2023 used for 2022 wave):")
        for s in substitutions:
            print(f"    {s['iso3']}: 2022 missing, used 2023 = {s['value']:.1f}%")
    else:
        print(f"  No 2022 substitutions needed.")

    # Report what each Eurostat-covered country contributes
    has_2022 = shares["invol_temp_share_pct_2022"].notna().sum()
    has_2024 = shares["invol_temp_share_pct_2024"].notna().sum()
    has_both = (shares["invol_temp_share_pct_2022"].notna()
                & shares["invol_temp_share_pct_2024"].notna()).sum()
    print(f"\n  Countries with non-NaN 2022 share: {has_2022}")
    print(f"  Countries with non-NaN 2024 share: {has_2024}")
    print(f"  Countries with both 2022 + 2024 share: {has_both}")

    print(f"\n  Hard-excluded per coverage check: {sorted(HARD_EXCLUDE)}")

    print(f"\nUpdating {EPL_GAP.name}...")
    epl_new, p1, f1 = update_epl_gap(shares)
    epl_new.to_csv(EPL_GAP, index=False)
    print(f"  Wrote {EPL_GAP} ({len(epl_new)} rows, {len(epl_new.columns)} columns)")
    print(f"  Columns: {list(epl_new.columns)}")
    print(f"  Defensive checks: {len(p1)} PASS, {len(f1)} FAIL")
    for f in f1:
        print(f"    [FAIL] {f}", file=sys.stderr)

    print(f"\nUpdating {TYPOLOGY.name}...")
    typ_new, p2, f2 = update_typology_positions(shares)
    typ_new.to_csv(TYPOLOGY, index=False)
    print(f"  Wrote {TYPOLOGY} ({len(typ_new)} rows, {len(typ_new.columns)} columns)")
    print(f"  Defensive checks: {len(p2)} PASS, {len(f2)} FAIL")
    for f in f2:
        print(f"    [FAIL] {f}", file=sys.stderr)

    # Report bucket counts and value ranges
    print("\n── Reporting ──")
    # In epl_gap, which countries got weighted values?
    weighted_present = epl_new[epl_new["dualization_gap_weighted"].notna()].copy()
    weighted_absent = epl_new[epl_new["dualization_gap_weighted"].isna()].copy()
    print(f"\nepl_gap.csv: weighted-gap coverage")
    print(f"  Countries with non-NaN dualization_gap_weighted: {len(weighted_present)}")
    print(f"  Countries with NaN dualization_gap_weighted:     {len(weighted_absent)}")
    print(f"  Excluded countries (NaN): {sorted(weighted_absent['country_iso3'])}")

    if len(weighted_present) > 0:
        print(f"\n  Value ranges (non-NaN rows):")
        print(f"    dualization_gap_raw:           "
              f"[{weighted_present['dualization_gap_raw'].min():+.4f}, "
              f"{weighted_present['dualization_gap_raw'].max():+.4f}]")
        print(f"    invol_temp_share_pct (2024):   "
              f"[{weighted_present['invol_temp_share_pct'].min():.1f}, "
              f"{weighted_present['invol_temp_share_pct'].max():.1f}]")
        print(f"    dualization_gap_weighted:      "
              f"[{weighted_present['dualization_gap_weighted'].min():+.4f}, "
              f"{weighted_present['dualization_gap_weighted'].max():+.4f}]")

    overall = "PASS" if (not f1 and not f2) else "FAIL"
    print(f"\nOVERALL: {overall}")
    return 0 if overall == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
