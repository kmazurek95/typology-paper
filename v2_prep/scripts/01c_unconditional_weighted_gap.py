"""
Script 01c: Unconditional (Häusermann–Schwander) weighted dualization gap

Adds an *unconditional* involuntary-temp-weighted dualization gap alongside the
*conditional* weighting already produced by Script 01b. Implements the
correction surfaced in the Script 06 preflight scrutiny (decision log #18 and
the entry S2 amendment).

Why a separate script (not an edit to 01b)
-------------------------------------------
Script 01b is a one-shot in-place mutator: it asserts the *pre-rename*
`dualization_gap` column exists and renames it to `dualization_gap_raw`, so
re-running 01b on the already-mutated CSVs fails the assert. 01c instead reads
the *current* state of epl_gap.csv (which already has `dualization_gap_raw` and
`invol_temp_share_pct_{2022,2024}`) and adds two columns. It is idempotent.

The correction
--------------
Script 01b's `invol_temp_share_pct` is from Eurostat `lfsa_etgar`
(unit=PC_SAL_TEMP, reason=NF_PJOB): the share *of temporary employees* who are
involuntary — a CONDITIONAL share. Häusermann–Schwander (2013) dualization
weighting wants an UNCONDITIONAL share (involuntary / employees). The existing
`temp_share` column in epl_gap.csv cannot be used to convert it: it is PC_EMP
(temps / total employment, self-employed in denominator) from an unfiltered
first-row grab in 01_clean_epl.py (decision log #18) and is mislabeled. To
compose correctly with the salaried-employee base of PC_SAL_TEMP, this script
pulls a FRESH `lfsi_pt_a` series at unit=PC_SAL (temps / salaried employees):

    uncond_invol_share = (pc_sal_temp_rate/100) * (invol_temp_share_pct/100)
                       = involuntary / salaried employees
    dualization_gap_weighted_uncond = dualization_gap_raw * uncond_invol_share

PC_SAL coverage was verified complete for all 23 weighted-gap countries at 2022
and 2024 (preflight check), so the columns are computed wave-specific with no
fallback. (Eurostat geo EL→GRC is handled by utils.ISO2_TO_ISO3; the only
unmapped geo codes in the PC_SAL slice are non-RTM aggregates BA/EA20/EA21/
EU27_2020, correctly dropped.)

Inputs
------
- data/raw/estat_lfsi_pt_a_en.csv        (already staged; PC_SAL series)
- data/processed/epl_gap.csv             (has dualization_gap_raw + invol cols)
- data/processed/typology_positions.csv  (same gap columns; updated for parity)

Outputs
-------
- data/processed/epl_gap.csv             (+ dualization_gap_weighted_uncond_{2022,2024}
                                            + pc_sal_temp_rate_{2022,2024})
- data/processed/typology_positions.csv  (same new columns)

Invocation
----------
python v2_prep/scripts/01c_unconditional_weighted_gap.py
"""

import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from utils import ISO2_TO_ISO3  # noqa: E402

LFSI_PT_A = ROOT / "data" / "raw" / "estat_lfsi_pt_a_en.csv"
EPL_GAP = ROOT / "data" / "processed" / "epl_gap.csv"
TYPOLOGY = ROOT / "data" / "processed" / "typology_positions.csv"

NEW_COLS = [
    "pc_sal_temp_rate_2022", "pc_sal_temp_rate_2024",
    "dualization_gap_weighted_uncond_2022", "dualization_gap_weighted_uncond_2024",
]


# ── 1. Fresh PC_SAL temporary-employment rate (temps / salaried employees) ───


def load_pc_sal_rate() -> pd.DataFrame:
    """Return (country_iso3, pc_sal_temp_rate_2022, pc_sal_temp_rate_2024).

    Filters lfsi_pt_a to the EMP_TEMP / Total / Y15-64 / PC_SAL slice — the
    salaried-employee base that composes with lfsa_etgar's PC_SAL_TEMP. This is
    NOT the contaminated PC_EMP `temp_share` already in epl_gap.csv (#18).
    """
    df = pd.read_csv(LFSI_PT_A)
    sub = df[
        (df["wstatus"] == "EMP_TEMP")
        & (df["sex"] == "T")
        & (df["age"] == "Y15-64")
        & (df["unit"] == "PC_SAL")
    ].copy()
    assert len(sub) > 0, "PC_SAL slice empty — check lfsi_pt_a unit codes"
    sub["OBS_VALUE"] = pd.to_numeric(sub["OBS_VALUE"], errors="coerce")
    sub["year"] = pd.to_numeric(sub["TIME_PERIOD"], errors="coerce").astype("Int64")
    sub["country_iso3"] = sub["geo"].map(ISO2_TO_ISO3)
    sub = sub.dropna(subset=["country_iso3", "OBS_VALUE", "year"])

    wide = sub.pivot_table(
        index="country_iso3", columns="year", values="OBS_VALUE", aggfunc="first"
    )
    out = pd.DataFrame({"country_iso3": wide.index})
    out["pc_sal_temp_rate_2022"] = wide.get(2022, pd.Series(np.nan, index=wide.index)).values
    out["pc_sal_temp_rate_2024"] = wide.get(2024, pd.Series(np.nan, index=wide.index)).values
    return out.reset_index(drop=True)


# ── 2. Add unconditional weighted columns to a gap frame ─────────────────────


def add_uncond(path: Path, rate: pd.DataFrame) -> tuple[list[str], list[str]]:
    df = pd.read_csv(path)
    # Name-drift guard: every column the construction + checks reference.
    assert "dualization_gap_raw" in df.columns, (
        f"{path.name}: expected dualization_gap_raw (run 01b first)"
    )
    for c in ("invol_temp_share_pct_2022", "invol_temp_share_pct_2024",
              "dualization_gap_weighted_2022", "dualization_gap_weighted_2024"):
        assert c in df.columns, f"{path.name}: missing required column {c} (run 01b first)"

    # Idempotent: drop any prior run's columns before re-adding
    df = df.drop(columns=[c for c in NEW_COLS if c in df.columns])
    df = df.merge(rate, on="country_iso3", how="left")

    for wave in ("2022", "2024"):
        df[f"dualization_gap_weighted_uncond_{wave}"] = (
            df["dualization_gap_raw"]
            * (df[f"pc_sal_temp_rate_{wave}"] / 100.0)
            * (df[f"invol_temp_share_pct_{wave}"] / 100.0)
        )

    # ── Defensive checks ──
    passes, failures = [], []

    def check(label, cond, detail=""):
        (passes if cond else failures).append(f"{label}: {detail}" if detail else label)

    for wave in ("2022", "2024"):
        cond = df[f"dualization_gap_weighted_{wave}"]
        uncond = df[f"dualization_gap_weighted_uncond_{wave}"]
        # (1) uncond NaN exactly where cond is NaN (PC_SAL complete for clean set)
        check(
            f"{wave}: uncond NaN-set == cond NaN-set",
            cond.isna().equals(uncond.isna()),
            f"cond NaN={sorted(set(df.loc[cond.isna(),'country_iso3']))}, "
            f"uncond NaN={sorted(set(df.loc[uncond.isna(),'country_iso3']))}",
        )
        # (2) |uncond| <= |cond| (multiplied by pc_sal_rate/100 < 1)
        both = df.dropna(subset=[f"dualization_gap_weighted_{wave}",
                                 f"dualization_gap_weighted_uncond_{wave}"])
        ok = (both[f"dualization_gap_weighted_uncond_{wave}"].abs()
              <= both[f"dualization_gap_weighted_{wave}"].abs() + 1e-12).all()
        check(f"{wave}: |uncond| <= |cond| for all non-NaN rows", ok)

    df.to_csv(path, index=False)
    return passes, failures


def main() -> int:
    print(f"Loading PC_SAL temp-employment rate from {LFSI_PT_A.name} ...")
    rate = load_pc_sal_rate()
    nn22 = rate["pc_sal_temp_rate_2022"].notna().sum()
    nn24 = rate["pc_sal_temp_rate_2024"].notna().sum()
    print(f"  PC_SAL rate available: {nn22} countries (2022), {nn24} (2024)")

    all_fail = []
    for path in (EPL_GAP, TYPOLOGY):
        print(f"\nUpdating {path.name} ...")
        p, f = add_uncond(path, rate)
        print(f"  Defensive checks: {len(p)} PASS, {len(f)} FAIL")
        for msg in p:
            print(f"    [PASS] {msg}")
        for msg in f:
            print(f"    [FAIL] {msg}", file=sys.stderr)
        all_fail += f

    # Report the clean-country uncond range and ordering
    epl = pd.read_csv(EPL_GAP)
    present = epl.dropna(subset=["dualization_gap_weighted_uncond_2024"])
    print(f"\nepl_gap.csv: uncond weighted-gap coverage = {len(present)} countries")
    if len(present):
        print(f"  dualization_gap_weighted_uncond_2024 range: "
              f"[{present['dualization_gap_weighted_uncond_2024'].min():+.4f}, "
              f"{present['dualization_gap_weighted_uncond_2024'].max():+.4f}]")
        cmp = present[["country_iso3", "dualization_gap_weighted_2024",
                       "dualization_gap_weighted_uncond_2024"]].copy()
        cmp = cmp.sort_values("dualization_gap_weighted_uncond_2024")
        print("  bottom-4 (uncond):")
        print(cmp.head(4).to_string(index=False))
        print("  top-4 (uncond):")
        print(cmp.tail(4).to_string(index=False))

    overall = "PASS" if not all_fail else "FAIL"
    print(f"\nOVERALL: {overall}")
    return 0 if overall == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
