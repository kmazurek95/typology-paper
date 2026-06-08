#!/usr/bin/env python3
"""
09_dv_factor_analysis.py

Exploratory factor analysis on candidate DV items from the q42/q27
digitalization policy battery. Produces a decision report for scale
composition.

Run from project root:
    python scripts/09_dv_factor_analysis.py

Inputs:
    - RTM 2022 .dta (q42a/b/c/d/f/g, q20, q19b/c/d/e)
    - RTM 2024 .dta (q27a/b/c/d/f/g, q20, q19b/c/d/e)

Output:
    - data/processed/dv_factor_analysis_report.md
"""

import sys
import json
import warnings
from pathlib import Path
from io import StringIO

import numpy as np
import pandas as pd
from factor_analyzer import FactorAnalyzer
from factor_analyzer.factor_analyzer import calculate_bartlett_sphericity, calculate_kmo

warnings.filterwarnings("ignore", category=FutureWarning)

# ── Paths ──
PROJECT = Path(__file__).resolve().parent.parent
DTA_2022 = PROJECT / "data" / "OECD_RTM_2022_Public_Use_Microdata" / "FinalData_dta" / "FinalData_dta" / "OECD_RTM_2022_Public_Use_Microdata.dta"
DTA_2024 = PROJECT / "data" / "OECD_RTM_2024_Public_Use_Microdata" / "OECD_RTM_2024_Public_Use_Microdata" / "OECD_RTM_2024_Public_Use_Microdata" / "OECD_RTM_2024_Public_Use_Microdata.dta"
OUTPUT = PROJECT / "data" / "processed" / "dv_factor_analysis_report.md"

# ── Variable maps ──
# 2022 vars -> harmonized concept names
VARS_2022 = {
    "q42a": "si_education",
    "q42b": "si_retraining",
    "q42c": "si_digital_infra",
    "q42d": "rd_robot_tax",
    "q42f": "rd_benefits",
    "q42g": "rd_ubi",
    "q20":  "rd_tax_rich",
    "q19b": "wtp_education",
    "q19c": "wtp_employment",
    "q19d": "wtp_unemployment",
    "q19e": "wtp_income",
}

VARS_2024 = {
    "q27a": "si_education",
    "q27b": "si_retraining",
    "q27c": "si_digital_infra",
    "q27d": "rd_robot_tax",
    "q27f": "rd_benefits",
    "q27g": "rd_ubi",
    "q20":  "rd_tax_rich",
    "q19b": "wtp_education",
    "q19c": "wtp_employment",
    "q19d": "wtp_unemployment",
    "q19e": "wtp_income",
}

# The 6-item set for the main EFA (q42/q27 battery only)
BATTERY_6 = ["si_education", "si_retraining", "si_digital_infra",
             "rd_robot_tax", "rd_benefits", "rd_ubi"]

# Sentinel/missing codes to recode to NA
# For Likert items (q42/q27/q20): 0, -77, 6, 98, 99 are all non-substantive
# For binary WTP items (q19): 0 means "not ticked" and IS a valid response
MISSING_LIKERT = {0, -77, 6, 98, 99}
MISSING_BINARY = {-77, 98, 99}  # 0 = valid "not ticked" for q19

BINARY_ITEMS = {"wtp_education", "wtp_employment", "wtp_unemployment", "wtp_income"}


def load_wave(dta_path, var_map):
    """Load a .dta, extract and rename DV variables, recode missings."""
    raw_cols = list(var_map.keys())
    df = pd.read_stata(dta_path, columns=raw_cols, convert_categoricals=False)
    df = df.rename(columns=var_map)
    # Recode missings (different rules for Likert vs binary items)
    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")
        codes = MISSING_BINARY if col in BINARY_ITEMS else MISSING_LIKERT
        df.loc[df[col].isin(codes), col] = np.nan
    return df


def descriptives(df, items, label):
    """Return a markdown table of descriptive stats."""
    rows = []
    for col in items:
        s = df[col]
        n = s.notna().sum()
        pct_na = s.isna().mean() * 100
        rows.append({
            "Variable": col,
            "N": n,
            "Mean": f"{s.mean():.3f}" if n > 0 else "—",
            "SD": f"{s.std():.3f}" if n > 0 else "—",
            "% NA": f"{pct_na:.1f}",
        })
    tbl = pd.DataFrame(rows)
    return f"### Descriptive statistics ({label})\n\n{tbl.to_markdown(index=False)}\n"


def correlation_matrix(df, items, label):
    """Return a markdown-formatted correlation matrix."""
    sub = df[items].dropna()
    corr = sub.corr()
    buf = StringIO()
    buf.write(f"### Inter-item correlation matrix ({label})\n\n")
    buf.write(f"N (listwise) = {len(sub)}\n\n")
    # Format to 3 decimal places
    fmt = corr.map(lambda x: f"{x:.3f}")
    buf.write(fmt.to_markdown())
    buf.write("\n")
    return buf.getvalue()


def kmo_bartlett(df, items, label):
    """Run KMO and Bartlett's test, return markdown."""
    sub = df[items].dropna()
    X = sub.values
    chi2, p = calculate_bartlett_sphericity(X)
    _, kmo_overall = calculate_kmo(X)
    buf = StringIO()
    buf.write(f"### KMO and Bartlett's test ({label})\n\n")
    buf.write(f"- KMO overall: **{kmo_overall:.3f}**")
    if kmo_overall < 0.6:
        buf.write(" ⚠️ BELOW 0.6 THRESHOLD")
    buf.write(f"\n- Bartlett's chi²: {chi2:.1f}, p = {p:.2e}")
    if p > 0.05:
        buf.write(" ⚠️ NOT SIGNIFICANT")
    buf.write("\n\n")
    return buf.getvalue()


def run_efa(df, items, n_factors, label):
    """Run EFA with promax rotation, return markdown."""
    sub = df[items].dropna()
    fa = FactorAnalyzer(n_factors=n_factors, rotation="promax", method="minres")
    fa.fit(sub)
    loadings = pd.DataFrame(
        fa.loadings_,
        index=items,
        columns=[f"Factor {i+1}" for i in range(n_factors)],
    )
    communalities = pd.Series(fa.get_communalities(), index=items, name="Communality")
    variance = fa.get_factor_variance()

    buf = StringIO()
    buf.write(f"### EFA: {n_factors}-factor promax ({label})\n\n")
    buf.write(f"N (listwise) = {len(sub)}\n\n")
    buf.write("**Factor loadings:**\n\n")
    combined = loadings.copy()
    combined["Communality"] = communalities
    buf.write(combined.map(lambda x: f"{x:.3f}").to_markdown())
    buf.write("\n\n**Variance explained:**\n\n")
    buf.write(f"- Factor 1: {variance[1][0]*100:.1f}% of variance\n")
    if n_factors > 1:
        buf.write(f"- Factor 2: {variance[1][1]*100:.1f}% of variance\n")
    buf.write(f"- Total: {sum(variance[1])*100:.1f}% of variance\n\n")
    return buf.getvalue(), loadings


def cronbach_alpha(df, items):
    """Compute Cronbach's alpha for a set of items."""
    sub = df[items].dropna()
    if len(sub) < 10 or len(items) < 2:
        return np.nan, len(sub)
    k = len(items)
    item_vars = sub.var(ddof=1)
    total_var = sub.sum(axis=1).var(ddof=1)
    if total_var == 0:
        return np.nan, len(sub)
    alpha = (k / (k - 1)) * (1 - item_vars.sum() / total_var)
    return alpha, len(sub)


def spearman_brown(df, items):
    """Spearman-Brown prophecy coefficient for 2-item scales."""
    if len(items) != 2:
        return np.nan, 0
    sub = df[items].dropna()
    if len(sub) < 10:
        return np.nan, len(sub)
    r = sub[items[0]].corr(sub[items[1]])
    sb = (2 * r) / (1 + r)
    return sb, len(sub)


def alpha_table(df, label):
    """Compute alpha for all candidate scale configurations."""
    configs = {
        "3-item redistribution (rd_robot_tax + rd_benefits + rd_ubi)":
            ["rd_robot_tax", "rd_benefits", "rd_ubi"],
        "3-item social investment (si_education + si_retraining + si_digital_infra)":
            ["si_education", "si_retraining", "si_digital_infra"],
        "4-item redistribution (+ rd_tax_rich)":
            ["rd_robot_tax", "rd_benefits", "rd_ubi", "rd_tax_rich"],
        "2-item social investment (si_education + si_retraining)":
            ["si_education", "si_retraining"],
        "2-item WTP redistribution (wtp_unemployment + wtp_income)":
            ["wtp_unemployment", "wtp_income"],
        "2-item WTP social investment (wtp_education + wtp_employment)":
            ["wtp_education", "wtp_employment"],
    }

    rows = []
    for name, items in configs.items():
        a, n = cronbach_alpha(df, items)
        row = {"Scale": name, "Items": len(items), "N": n, "Alpha": f"{a:.3f}" if not np.isnan(a) else "—"}
        if len(items) == 2:
            sb, _ = spearman_brown(df, items)
            row["Spearman-Brown"] = f"{sb:.3f}" if not np.isnan(sb) else "—"
        else:
            row["Spearman-Brown"] = "—"
        rows.append(row)

    tbl = pd.DataFrame(rows)
    buf = StringIO()
    buf.write(f"### Cronbach's alpha / Spearman-Brown ({label})\n\n")
    buf.write(tbl.to_markdown(index=False))
    buf.write("\n\n")

    # Flag 4-item if alpha > 0.7
    four_item_alpha = float(rows[3]["Alpha"]) if rows[3]["Alpha"] != "—" else 0
    if four_item_alpha > 0.7:
        buf.write(f"**Note:** 4-item redistribution scale (adding q20) has alpha = {four_item_alpha:.3f} > 0.7 — viable alternative to 3-item version.\n\n")

    return buf.getvalue(), {r["Scale"]: r["Alpha"] for r in rows}


def analyze_wave(dta_path, var_map, wave_label):
    """Run the full analysis pipeline for one wave. Return markdown + key stats."""
    print(f"Loading {wave_label}...")
    df = load_wave(dta_path, var_map)
    print(f"  Loaded {len(df)} respondents, {len(df.columns)} variables")

    all_items = list(var_map.values())
    report = []
    stats = {}

    report.append(f"## {wave_label}\n")

    # 1. Descriptives
    report.append(descriptives(df, all_items, wave_label))

    # 2. Correlation matrix (6-item battery only)
    report.append(correlation_matrix(df, BATTERY_6, wave_label))

    # 3. KMO + Bartlett
    report.append(kmo_bartlett(df, BATTERY_6, wave_label))

    # 4. EFA: 2-factor on 6-item set
    efa_text, loadings = run_efa(df, BATTERY_6, 2, wave_label)
    report.append(efa_text)
    stats["loadings"] = loadings

    # 5. Alpha table
    alpha_text, alphas = alpha_table(df, wave_label)
    report.append(alpha_text)
    stats["alphas"] = alphas

    return "\n".join(report), stats


def write_recommendations(stats_2022, stats_2024):
    """Write the final recommendations section."""
    buf = StringIO()
    buf.write("## Scale recommendations\n\n")

    # Check 2-factor structure
    buf.write("### Does the 2-factor structure hold in both waves?\n\n")
    for label, stats in [("2022", stats_2022), ("2024", stats_2024)]:
        L = stats["loadings"]
        # Check if SI items load primarily on one factor and RD on the other
        si_items = ["si_education", "si_retraining", "si_digital_infra"]
        rd_items = ["rd_robot_tax", "rd_benefits", "rd_ubi"]

        # For each item, which factor has the higher absolute loading?
        si_primary = []
        rd_primary = []
        for item in si_items:
            vals = L.loc[item].values
            si_primary.append(np.argmax(np.abs(vals)))
        for item in rd_items:
            vals = L.loc[item].values
            rd_primary.append(np.argmax(np.abs(vals)))

        si_same = len(set(si_primary)) == 1
        rd_same = len(set(rd_primary)) == 1
        si_rd_different = si_primary[0] != rd_primary[0] if (si_same and rd_same) else False

        buf.write(f"**{label}:**\n")
        buf.write(f"- SI items load primarily on Factor {si_primary[0]+1}: {si_same}\n")
        buf.write(f"- RD items load primarily on Factor {rd_primary[0]+1}: {rd_same}\n")
        buf.write(f"- SI and RD load on different factors: {si_rd_different}\n")

        if si_same and rd_same and si_rd_different:
            buf.write(f"- **2-factor structure HOLDS in {label}.**\n")
        else:
            buf.write(f"- **⚠️ 2-factor structure DOES NOT hold cleanly in {label}.**\n")
        buf.write("\n")

    # Check q42c / q27c cross-loading
    buf.write("### Does q42c / q27c (digital infrastructure) cross-load?\n\n")
    for label, stats in [("2022", stats_2022), ("2024", stats_2024)]:
        L = stats["loadings"]
        infra = L.loc["si_digital_infra"]
        primary = np.max(np.abs(infra.values))
        secondary = np.min(np.abs(infra.values))
        buf.write(f"**{label}:** primary loading = {primary:.3f}, secondary = {secondary:.3f}")
        if secondary > 0.3:
            buf.write(f" ⚠️ cross-loads (secondary > 0.3)")
        if primary < 0.4:
            buf.write(f" ⚠️ loads weakly (primary < 0.4)")
        buf.write("\n")
    buf.write("\n")

    # Check q20 loading
    buf.write("### Does q20 (tax the rich) load with redistribution items?\n\n")
    buf.write("q20 was not included in the 6-item EFA because it uses a different response scale (5-point vs 6-point). ")
    buf.write("The alpha table shows whether adding q20 to the 3-item redistribution scale improves or degrades reliability:\n\n")
    for label, stats in [("2022", stats_2022), ("2024", stats_2024)]:
        a3 = stats["alphas"].get("3-item redistribution (rd_robot_tax + rd_benefits + rd_ubi)", "—")
        a4 = stats["alphas"].get("4-item redistribution (+ rd_tax_rich)", "—")
        buf.write(f"- **{label}:** 3-item alpha = {a3}, 4-item alpha (with q20) = {a4}\n")
    buf.write("\nIf the 4-item alpha is higher, q20 loads with the redistribution items empirically. ")
    buf.write("Even so, the measurement section may be cleaner keeping q20 as a standalone generic-redistribution robustness DV ")
    buf.write("while the main scale stays technology-framed.\n\n")

    # Consistency across waves
    buf.write("### Is factor structure consistent across waves?\n\n")
    L22 = stats_2022["loadings"]
    L24 = stats_2024["loadings"]
    # Tucker's congruence coefficient (simplified: correlation of loading vectors)
    for f in range(2):
        v22 = L22.iloc[:, f].values
        v24 = L24.iloc[:, f].values
        # Try both orderings since factor order may flip
        corr_same = np.corrcoef(v22, v24)[0, 1]
        corr_flip = np.corrcoef(v22, L24.iloc[:, 1-f].values)[0, 1]
        best = max(abs(corr_same), abs(corr_flip))
        buf.write(f"- Factor {f+1} loading correlation across waves: {best:.3f}")
        if best > 0.9:
            buf.write(" (excellent congruence)")
        elif best > 0.8:
            buf.write(" (acceptable congruence)")
        else:
            buf.write(" ⚠️ (poor congruence — discuss in measurement section)")
        buf.write("\n")
    buf.write("\n")

    return buf.getvalue()


def main():
    report_parts = []
    report_parts.append("# DV Factor Analysis Report\n")
    report_parts.append("Candidate DV items from the RTM q42/q27 digitalization policy battery.\n")
    report_parts.append("---\n")

    text_2022, stats_2022 = analyze_wave(DTA_2022, VARS_2022, "RTM 2022")
    report_parts.append(text_2022)
    report_parts.append("---\n")

    text_2024, stats_2024 = analyze_wave(DTA_2024, VARS_2024, "RTM 2024")
    report_parts.append(text_2024)
    report_parts.append("---\n")

    recs = write_recommendations(stats_2022, stats_2024)
    report_parts.append(recs)

    full_report = "\n".join(report_parts)
    OUTPUT.write_text(full_report, encoding="utf-8")
    print(f"\nReport written to {OUTPUT}")

    # Print summary to stdout
    print("\n" + "=" * 60)
    print("QUICK SUMMARY")
    print("=" * 60)
    for label, stats in [("2022", stats_2022), ("2024", stats_2024)]:
        print(f"\n{label} alphas:")
        for name, val in stats["alphas"].items():
            print(f"  {val:>6s}  {name}")


if __name__ == "__main__":
    main()
