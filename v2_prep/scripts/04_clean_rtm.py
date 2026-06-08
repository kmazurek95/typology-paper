"""
Script 04: RTM Pooling and Cleaning

Reads the per-wave Parquet files written by Script 00 plus the harmonization
audit's mapping CSV (variable_mapping_2022_2024.csv) and produces a single
pooled analytic Parquet ready for Script 06 (country-level merge) and
Script 08 (R-side multilevel regression).

Core principle (from audit_completion_summary.md Section 5):
**Match every variable by analytic_name. Never by raw variable name.**
The mapping CSV is the contract; this script does not contain hard-coded
variable names except where the mapping CSV explicitly names sources for
the one multi-source row (iv_suppl_work_any).

Inputs
------
- v2_prep/data/processed/rtm_2022_raw.parquet     (from Script 00)
- v2_prep/data/processed/rtm_2024_raw.parquet     (from Script 00)
- v2_prep/data/processed/variable_mapping_2022_2024.csv  (audit output)

Outputs
-------
- v2_prep/data/processed/rtm_pooled_analytic.parquet
- v2_prep/data/processed/rtm_pooled_analytic_verification.txt

Invocation
----------
python v2_prep/scripts/04_clean_rtm.py
"""

import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

sys.stdout.reconfigure(encoding="utf-8")

import numpy as np
import pandas as pd

# ── Paths ──────────────────────────────────────────────────────────────────

ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "v2_prep" / "data" / "processed"
MAPPING_CSV = PROCESSED / "variable_mapping_2022_2024.csv"
RAW_2022 = PROCESSED / "rtm_2022_raw.parquet"
RAW_2024 = PROCESSED / "rtm_2024_raw.parquet"
OUT_PARQUET = PROCESSED / "rtm_pooled_analytic.parquet"
OUT_LOG = PROCESSED / "rtm_pooled_analytic_verification.txt"

ADMIN_NAMES = {"id", "ctrcode", "ctryear", "year", "weight"}
EXPECTED_TOTAL_LOW = 53_000
EXPECTED_TOTAL_HIGH = 57_000


# ── Recode-rule interpreter ────────────────────────────────────────────────

# Per audit Section 5b: the recode_rule column is variable-specific and
# authoritative. Don't blanket-replace sentinel codes; apply only what each
# row's rule specifies.

NOOP_PREFIXES = ("No ", "Numeric integer; range")


@dataclass
class ParsedRule:
    """Machine-interpretable recode rule for a single analytic variable."""
    na_2022: set = field(default_factory=set)
    na_2024: set = field(default_factory=set)
    replace_2022: dict = field(default_factory=dict)   # {old: new}
    replace_2024: dict = field(default_factory=dict)
    special: Optional[str] = None
    raw: str = ""


def parse_rule(rule: str) -> ParsedRule:
    """Parse a recode_rule cell into a ParsedRule.

    Recognized patterns (covering all 19 distinct rules in the v1.0 audit):
    1. Standard sentinel:    "{wave} -> NA on {a, b, c}"  per wave, joined by ";"
    2. No-op:                "No recoding required.", "No sentinel ...", etc.
    3. Numeric range note:   "Numeric integer; range observed 18-64. ..."
    4. iv_suppl_work_any:    "Pool to binary 'any supplementary work ..."
    5. iv_worker_status:     "recode 12 ('Other') to 96; recode 99 ('Prefer not to say') to 96"
    6. iv_partner_paidwork:  "NA on {-77, 6}; collapse {96, 98} both to 'Other/Don't know'"
    7. dem_n_children_hh:    "sentinel codes -99 (refusal) and -66 (filter)"
    8. iv_nace_sector:       "Treat codes {97, 99} as NA for substantive analyses"
                             (Script 06 concern; no-op here)
    """
    out = ParsedRule(raw=rule)

    if not isinstance(rule, str) or rule.strip() == "":
        return out

    # No-op patterns
    if any(rule.startswith(p) for p in NOOP_PREFIXES):
        return out

    # iv_suppl_work_any
    if "Pool to binary 'any supplementary work" in rule:
        out.special = "pool_suppl_work"
        return out

    # iv_worker_status
    if "recode 12 ('Other') to 96" in rule and "recode 99 ('Prefer not to say') to 96" in rule:
        out.replace_2022[12] = 96
        out.replace_2024[99] = 96
        # The trailing "both -> NA on 96 for substantive analyses" is a
        # Script 06 concern (substantive transformation), not Script 04.
        return out

    # iv_partner_paidwork
    if "collapse {96, 98} both to" in rule:
        out.na_2022 = {-77, 6}
        out.replace_2022[98] = 96   # collapse 98 -> 96 in 2022
        out.na_2024 = {99}
        return out

    # dem_n_children_hh
    if "sentinel codes -99 (refusal) and -66 (filter)" in rule:
        out.na_2022 = {-99, -66}
        return out

    # iv_nace_sector — substantive transformation, defer to Script 06
    if "Treat codes {97, 99} as NA for substantive" in rule:
        return out

    # Generic "{wave} -> NA on {a, b, c}" pattern
    for wave in (2022, 2024):
        m = re.search(rf"{wave} -> NA on \{{([^}}]+)\}}", rule)
        if m:
            codes = {int(x.strip()) for x in m.group(1).split(",")}
            if wave == 2022:
                out.na_2022 = codes
            else:
                out.na_2024 = codes

    # Sanity: if we didn't recognize anything substantive, fail loudly
    if not (out.na_2022 or out.na_2024 or out.replace_2022 or out.replace_2024
            or out.special):
        raise ValueError(
            f"Unparseable recode_rule (no known pattern matched): {rule!r}"
        )

    return out


def apply_rule_to_column(
    col: pd.Series, na_codes: set, replace: dict
) -> pd.Series:
    """Apply NA-coding and value-replacement to a single column."""
    out = col
    if replace:
        out = out.replace(replace)
    if na_codes:
        # Use isin then mask to NaN; safer than .replace which can have dtype quirks
        mask = out.isin(na_codes)
        if mask.any():
            out = out.astype("Float64")
            out[mask] = pd.NA
    return out


# ── Survey + report distinct recode_rule patterns ──────────────────────────


def survey_recode_rules(mapping: pd.DataFrame) -> list[tuple[str, int, str]]:
    """Return [(rule_text, n_rows, parsed_summary)] for every distinct rule."""
    summary = []
    for rule, n_rows in mapping["recode_rule"].fillna("").value_counts().items():
        try:
            parsed = parse_rule(rule)
            parts = []
            if parsed.special:
                parts.append(f"special={parsed.special}")
            if parsed.na_2022:
                parts.append(f"na_2022={sorted(parsed.na_2022)}")
            if parsed.na_2024:
                parts.append(f"na_2024={sorted(parsed.na_2024)}")
            if parsed.replace_2022:
                parts.append(f"replace_2022={parsed.replace_2022}")
            if parsed.replace_2024:
                parts.append(f"replace_2024={parsed.replace_2024}")
            summary_str = "; ".join(parts) if parts else "no-op"
        except ValueError as e:
            summary_str = f"UNPARSEABLE: {e}"
        summary.append((rule, int(n_rows), summary_str))
    return summary


def print_rule_survey(survey: list[tuple[str, int, str]]) -> None:
    print("=" * 70)
    print(f"recode_rule survey — {len(survey)} distinct patterns")
    print("=" * 70)
    for rule, n_rows, parsed_str in survey:
        print(f"\n  [{n_rows:3} rows] {parsed_str}")
        print(f"           rule = {rule[:120]!r}{'...' if len(rule) > 120 else ''}")
    print()


# ── Multi-source pooling: iv_suppl_work_any ────────────────────────────────


def derive_suppl_work_any(
    df_22: pd.DataFrame, df_24: pd.DataFrame, row: pd.Series
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Derive the iv_suppl_work_any binary column in both waves.

    Source columns come from var_2022 / var_2024 in the mapping row, joined by ';'.
    2022: 1 iff any of (s26a, s26b) in {1, 2, 3}, else 0
    2024: 1 iff any of (s31a, s31b, s31c) == 1, else 0
    """
    analytic = row["analytic_name"]

    srcs_22 = [s.strip() for s in str(row["var_2022"]).split(";") if s.strip()]
    srcs_24 = [s.strip() for s in str(row["var_2024"]).split(";") if s.strip()]

    for s in srcs_22:
        assert s in df_22.columns, f"iv_suppl_work_any source {s} not in 2022 frame"
    for s in srcs_24:
        assert s in df_24.columns, f"iv_suppl_work_any source {s} not in 2024 frame"

    # 2022: frequency scale 1-4 (with sentinels -77, 0). 1/2/3 = at least
    # occasionally; 4 = Never; -77/0 = filter/unanswered (treat as 0).
    pos_22 = pd.Series(False, index=df_22.index)
    for s in srcs_22:
        pos_22 = pos_22 | df_22[s].isin([1, 2, 3])
    df_22[analytic] = pos_22.astype("Int8")

    # 2024: binary tick-list; 1 = ticked, 0 = not ticked. s31d (None) not used.
    pos_24 = pd.Series(False, index=df_24.index)
    for s in srcs_24:
        pos_24 = pos_24 | (df_24[s] == 1)
    df_24[analytic] = pos_24.astype("Int8")

    return df_22, df_24


# ── Per-wave rename + recode ───────────────────────────────────────────────


def process_wave(
    df: pd.DataFrame, mapping: pd.DataFrame, wave: int
) -> tuple[pd.DataFrame, list[str]]:
    """Rename + recode columns for one wave per the mapping CSV.

    Returns (processed_frame, list_of_analytic_names_present_this_wave).
    """
    out = df.copy()
    present: list[str] = []
    src_col = "var_2022" if wave == 2022 else "var_2024"
    na_attr = "na_2022" if wave == 2022 else "na_2024"
    rep_attr = "replace_2022" if wave == 2022 else "replace_2024"

    for _, row in mapping.iterrows():
        analytic = row["analytic_name"]
        status = row["harmonization_status"]
        raw_src = row[src_col]
        rule = parse_rule(row["recode_rule"])

        # iv_suppl_work_any was pre-derived (the analytic column already exists
        # in out under its analytic name). Don't rename, don't recode.
        if rule.special == "pool_suppl_work":
            assert analytic in out.columns, (
                f"[{wave}] iv_suppl_work_any column should already exist "
                f"(derived in pre-pass); got columns starting with iv_suppl: "
                f"{[c for c in out.columns if c.startswith('iv_suppl')]}"
            )
            present.append(analytic)
            continue

        # Empty src for this wave = wave-specific row that doesn't apply here.
        # Caller (the pool step) will add an all-NaN column.
        if not isinstance(raw_src, str) or raw_src.strip() == "":
            continue

        # Single-source rename + recode
        assert raw_src in out.columns, (
            f"[{wave}] source variable {raw_src!r} for analytic {analytic!r} "
            f"not found in raw frame. Check upstream Script 00 output."
        )

        col = out[raw_src]
        col = apply_rule_to_column(
            col,
            na_codes=getattr(rule, na_attr),
            replace=getattr(rule, rep_attr),
        )

        # Drop the raw column to avoid the trap (raw name surviving rename)
        out = out.drop(columns=[raw_src])
        out[analytic] = col
        present.append(analytic)

    return out, present


# ── Pool + verify ──────────────────────────────────────────────────────────


def pool_and_verify(
    df_22: pd.DataFrame, df_24: pd.DataFrame,
    mapping: pd.DataFrame,
    present_22: list[str], present_24: list[str],
) -> tuple[pd.DataFrame, list[str], list[str]]:
    """Pool the two waves into one frame; run defensive checks; return (frame, passes, failures)."""
    all_analytic = mapping["analytic_name"].tolist()
    expected_cols = set(all_analytic) | {"wave"}

    # Drop unmapped columns from each wave (defensive backstop against the traps).
    # Admin columns survive because they ARE mapped (their analytic_name = raw name).
    unmapped_22 = sorted(set(df_22.columns) - set(all_analytic))
    unmapped_24 = sorted(set(df_24.columns) - set(all_analytic))
    df_22 = df_22.drop(columns=unmapped_22)
    df_24 = df_24.drop(columns=unmapped_24)

    # Add missing columns (the wave-specific ones) as all-NaN per the spec
    for analytic in all_analytic:
        if analytic not in df_22.columns:
            df_22[analytic] = pd.NA
        if analytic not in df_24.columns:
            df_24[analytic] = pd.NA

    # Add wave indicator
    df_22 = df_22.copy()
    df_24 = df_24.copy()
    df_22["wave"] = "2022"
    df_24["wave"] = "2024"

    # Pool (column order matches mapping CSV)
    cols = all_analytic + ["wave"]
    pooled = pd.concat(
        [df_22[cols], df_24[cols]], axis=0, ignore_index=True
    )

    # Defensive checks
    passes: list[str] = []
    failures: list[str] = []

    def check(label: str, cond: bool, detail: str = "") -> None:
        if cond:
            passes.append(label)
        else:
            failures.append(f"{label}: {detail}" if detail else label)

    # Per-analytic coverage
    for col in all_analytic:
        check(f"column {col!r} present in pooled frame", col in pooled.columns)

    # No duplicate column names (the central trap guard)
    dupes = pooled.columns[pooled.columns.duplicated()].tolist()
    check("no duplicate column names in pooled frame", not dupes,
          f"duplicates: {dupes}")

    # wave column has exactly two distinct values
    wave_vals = sorted(pooled["wave"].dropna().unique().tolist())
    check("wave column has exactly {'2022', '2024'}",
          wave_vals == ["2022", "2024"],
          f"got {wave_vals}")

    # Total row count
    n_total = len(pooled)
    check(f"total row count in [{EXPECTED_TOTAL_LOW:,}, {EXPECTED_TOTAL_HIGH:,}]",
          EXPECTED_TOTAL_LOW <= n_total <= EXPECTED_TOTAL_HIGH,
          f"n_total = {n_total:,}")

    # Per-row coverage (uses harmonization_status)
    for _, row in mapping.iterrows():
        a = row["analytic_name"]
        if a not in pooled.columns:
            continue  # already flagged above
        status = row["harmonization_status"]
        col_22 = pooled.loc[pooled["wave"] == "2022", a]
        col_24 = pooled.loc[pooled["wave"] == "2024", a]

        if status == "2022_only":
            check(f"[{a}] 2022_only -> all-NaN in 2024 rows",
                  col_24.isna().all(),
                  f"non-NaN in 2024: {(~col_24.isna()).sum()}")
            check(f"[{a}] 2022_only -> has data in 2022 rows",
                  not col_22.isna().all())
        elif status == "2024_only":
            check(f"[{a}] 2024_only -> all-NaN in 2022 rows",
                  col_22.isna().all(),
                  f"non-NaN in 2022: {(~col_22.isna()).sum()}")
            check(f"[{a}] 2024_only -> has data in 2024 rows",
                  not col_24.isna().all())
        elif status in ("clean", "needs_recode", "open"):
            check(f"[{a}] {status} -> has data in 2022 rows",
                  not col_22.isna().all())
            check(f"[{a}] {status} -> has data in 2024 rows",
                  not col_24.isna().all())

    return pooled, passes, failures


# ── Verification log ───────────────────────────────────────────────────────


def write_verification_log(
    *,
    survey: list[tuple[str, int, str]],
    df_22_rows: int, df_24_rows: int,
    df_22_dropped: list[str], df_24_dropped: list[str],
    pooled: pd.DataFrame,
    mapping: pd.DataFrame,
    passes: list[str], failures: list[str],
) -> None:
    L: list[str] = []

    L.append("RTM Pooled Analytic Frame — Verification Log")
    L.append(f"Run: {datetime.now().isoformat(timespec='seconds')}")
    L.append(f"Source script: v2_prep/scripts/04_clean_rtm.py")
    L.append(f"Mapping CSV:   {MAPPING_CSV.name} ({len(mapping)} rows)")
    L.append(f"Input 2022:    {RAW_2022.name} ({RAW_2022.stat().st_size / 1e6:.2f} MB)")
    L.append(f"Input 2024:    {RAW_2024.name} ({RAW_2024.stat().st_size / 1e6:.2f} MB)")
    L.append(f"Output:        {OUT_PARQUET.name}")
    L.append("")

    L.append("─" * 70)
    L.append("Row counts")
    L.append("─" * 70)
    L.append(f"  2022 wave: {df_22_rows:,}")
    L.append(f"  2024 wave: {df_24_rows:,}")
    L.append(f"  Pooled:    {len(pooled):,}")
    L.append("")

    L.append("─" * 70)
    L.append(f"recode_rule survey ({len(survey)} distinct patterns)")
    L.append("─" * 70)
    for rule, n_rows, parsed_str in survey:
        L.append(f"  [{n_rows:3} rows] {parsed_str}")
        # truncate long rules
        r = rule[:160] + "..." if len(rule) > 160 else rule
        L.append(f"            rule = {r!r}")
    L.append("")

    L.append("─" * 70)
    L.append("Unmapped columns dropped (defensive backstop)")
    L.append("─" * 70)
    L.append(f"  2022: {len(df_22_dropped)} columns dropped")
    if df_22_dropped:
        L.append(f"        e.g. {df_22_dropped[:10]}")
    L.append(f"  2024: {len(df_24_dropped)} columns dropped")
    if df_24_dropped:
        L.append(f"        e.g. {df_24_dropped[:10]}")
    L.append("")

    # Per-row status table
    L.append("─" * 70)
    L.append("Per-row mapping summary")
    L.append("─" * 70)
    by_status = mapping.groupby("harmonization_status").size().to_dict()
    for status, n in sorted(by_status.items(), key=lambda kv: -kv[1]):
        L.append(f"  {status:14} {n:4}")
    L.append("")

    # Open / needs_recode rows enumerated
    flagged = mapping[mapping["harmonization_status"].isin({"open", "needs_recode"})]
    L.append("─" * 70)
    L.append(f"Flagged rows (open / needs_recode) — {len(flagged)} total")
    L.append("─" * 70)
    for _, row in flagged.iterrows():
        L.append(f"  [{row['harmonization_status']}] {row['analytic_name']:34} "
                 f"(2022={row['var_2022']}, 2024={row['var_2024']})")
        L.append(f"     rule: {row['recode_rule'][:120]}{'...' if len(str(row['recode_rule'])) > 120 else ''}")
    L.append("")

    # Defensive checks
    L.append("─" * 70)
    L.append(f"Defensive checks: {len(passes)} PASS, {len(failures)} FAIL")
    L.append("─" * 70)
    if failures:
        L.append("  FAILURES:")
        for f in failures:
            L.append(f"    [FAIL] {f}")
        L.append("")
    L.append(f"  (Pass list omitted from log for brevity; {len(passes)} checks passed.)")
    L.append("")

    # Pooled frame schema
    L.append("─" * 70)
    L.append(f"Pooled frame schema ({len(pooled.columns)} columns)")
    L.append("─" * 70)
    for col in pooled.columns:
        nn = int(pooled[col].notna().sum())
        L.append(f"  {col:36} {str(pooled[col].dtype):12} non-null={nn:6,} / {len(pooled):,}")
    L.append("")

    overall = "PASS" if not failures else "FAIL"
    L.append("=" * 70)
    L.append(f"OVERALL: {overall}")
    L.append("=" * 70)

    OUT_LOG.write_text("\n".join(L) + "\n", encoding="utf-8")


# ── Main ───────────────────────────────────────────────────────────────────


def main() -> int:
    print(f"Loading mapping CSV: {MAPPING_CSV}")
    mapping = pd.read_csv(MAPPING_CSV)
    assert len(mapping) > 0, "Empty mapping CSV"

    # Survey + print recode rules first per spec
    survey = survey_recode_rules(mapping)
    print_rule_survey(survey)

    # Confirm every rule is parseable before doing any data work
    unparseable = [r for r, _, p in survey if p.startswith("UNPARSEABLE")]
    if unparseable:
        print("FATAL: unparseable recode rules found:", file=sys.stderr)
        for r in unparseable:
            print(f"  {r!r}", file=sys.stderr)
        return 2

    print(f"Loading {RAW_2022}")
    df_22 = pd.read_parquet(RAW_2022)
    print(f"  2022: {len(df_22):,} rows × {len(df_22.columns)} cols")

    print(f"Loading {RAW_2024}")
    df_24 = pd.read_parquet(RAW_2024)
    print(f"  2024: {len(df_24):,} rows × {len(df_24.columns)} cols")

    df_22_rows = len(df_22)
    df_24_rows = len(df_24)

    # 1. Pre-derive multi-source row (iv_suppl_work_any) — must happen
    #    before the standard rename loop consumes its source columns.
    multi_source_rows = mapping[
        mapping["var_2022"].fillna("").str.contains(";", na=False)
        | mapping["var_2024"].fillna("").str.contains(";", na=False)
    ]
    print(f"\nMulti-source rows: {len(multi_source_rows)}")
    for _, row in multi_source_rows.iterrows():
        print(f"  Deriving {row['analytic_name']} from "
              f"2022={row['var_2022']!r}, 2024={row['var_2024']!r}")
        df_22, df_24 = derive_suppl_work_any(df_22, df_24, row)

    # 2. Standard per-row rename + recode pass
    print("\nProcessing 2022 wave...")
    df_22_proc, present_22 = process_wave(df_22, mapping, 2022)
    print(f"  {len(present_22)} analytic columns present in 2022")

    print("Processing 2024 wave...")
    df_24_proc, present_24 = process_wave(df_24, mapping, 2024)
    print(f"  {len(present_24)} analytic columns present in 2024")

    # Track what was dropped for the verification log
    all_analytic = set(mapping["analytic_name"])
    df_22_dropped = sorted(set(df_22_proc.columns) - all_analytic)
    df_24_dropped = sorted(set(df_24_proc.columns) - all_analytic)

    # 3. Pool + verify
    print("\nPooling waves and running defensive checks...")
    pooled, passes, failures = pool_and_verify(
        df_22_proc, df_24_proc, mapping, present_22, present_24,
    )

    # 4. Write outputs
    pooled.to_parquet(OUT_PARQUET, index=False)
    print(f"\nWrote {OUT_PARQUET} "
          f"({len(pooled):,} rows × {len(pooled.columns)} cols, "
          f"{OUT_PARQUET.stat().st_size / 1e6:.2f} MB)")

    write_verification_log(
        survey=survey,
        df_22_rows=df_22_rows, df_24_rows=df_24_rows,
        df_22_dropped=df_22_dropped, df_24_dropped=df_24_dropped,
        pooled=pooled, mapping=mapping,
        passes=passes, failures=failures,
    )
    print(f"Wrote {OUT_LOG}")

    print(f"\nDefensive checks: {len(passes)} PASS, {len(failures)} FAIL")
    if failures:
        print("\nFAILURES:")
        for f in failures[:20]:
            print(f"  [FAIL] {f}")
        if len(failures) > 20:
            print(f"  ... ({len(failures) - 20} more failures; see verification log)")
        print("\nOVERALL: FAIL", file=sys.stderr)
        return 1

    print("\nOVERALL: PASS — all defensive checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
