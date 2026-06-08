#!/usr/bin/env python3
"""
compare_value_labels.py

Side-by-side value label comparison for RTM variables across waves.

Usage:
    python scripts/compare_value_labels.py q11d
    python scripts/compare_value_labels.py q13a q13b q13c q13d q13e
    python scripts/compare_value_labels.py --battery q13
    python scripts/compare_value_labels.py --flagged
"""

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CODEBOOK_2022 = PROJECT_ROOT / "data" / "processed" / "rtm_2022_codebook.csv"
CODEBOOK_2024 = PROJECT_ROOT / "data" / "processed" / "rtm_2024_codebook.csv"
AUDIT_SKELETON = PROJECT_ROOT / "data" / "processed" / "rtm_harmonization_audit_skeleton.csv"


def load_codebooks():
    for path in (CODEBOOK_2022, CODEBOOK_2024):
        if not path.exists():
            sys.exit(f"ERROR: codebook not found at {path}")
    return {
        "2022": pd.read_csv(CODEBOOK_2022),
        "2024": pd.read_csv(CODEBOOK_2024),
    }


def parse_value_labels(raw):
    if pd.isna(raw) or raw == "" or raw == "{}":
        return {}
    try:
        parsed = json.loads(raw)
        return {str(k): v for k, v in parsed.items()}
    except (json.JSONDecodeError, TypeError):
        return {"<unparseable>": str(raw)[:80]}


def lookup_variable(codebooks, varname):
    result = {}
    for wave, df in codebooks.items():
        matches = df[df["variable_name"] == varname]
        if len(matches) == 0:
            result[wave] = None
        else:
            result[wave] = matches.iloc[0].to_dict()
    return result


def format_comparison(varname, lookup):
    lines = []
    lines.append("=" * 78)
    lines.append(f"  {varname}")
    lines.append("=" * 78)

    for wave in ("2022", "2024"):
        row = lookup[wave]
        lines.append(f"\n[{wave}]")
        if row is None:
            lines.append("  (variable not present in this wave)")
            continue

        label = row.get("variable_label", "") or "(no Stata label)"
        lines.append(f"  label: {label}")
        lines.append(f"  dtype: {row.get('dtype', '')}")

        vlabels = parse_value_labels(row.get("value_labels_json", ""))
        if not vlabels:
            lines.append("  value labels: (none attached)")
        else:
            lines.append("  value labels:")
            def sort_key(k):
                try:
                    return (0, float(k))
                except ValueError:
                    return (1, k)
            for code in sorted(vlabels.keys(), key=sort_key):
                lines.append(f"    {code:>4}  {vlabels[code]}")

    r22, r24 = lookup["2022"], lookup["2024"]
    if r22 is None or r24 is None:
        verdict = "WAVE-SPECIFIC (present in only one wave)"
    else:
        v22 = parse_value_labels(r22.get("value_labels_json", ""))
        v24 = parse_value_labels(r24.get("value_labels_json", ""))
        if v22 == v24:
            verdict = "IDENTICAL value labels"
        elif set(v22.keys()) == set(v24.keys()):
            verdict = "SAME CODES, different label text (likely cosmetic)"
        elif not v22 or not v24:
            verdict = "ONE WAVE HAS NO LABELS (may be unlabeled numeric)"
        else:
            only_22 = set(v22.keys()) - set(v24.keys())
            only_24 = set(v24.keys()) - set(v22.keys())
            parts = []
            if only_22:
                parts.append(f"2022-only codes: {sorted(only_22, key=lambda k: (float(k) if k.lstrip('-').isdigit() else float('inf'), k))}")
            if only_24:
                parts.append(f"2024-only codes: {sorted(only_24, key=lambda k: (float(k) if k.lstrip('-').isdigit() else float('inf'), k))}")
            verdict = "DIFFERENT CODE SETS -- " + "; ".join(parts)

    lines.append(f"\n  verdict: {verdict}")
    lines.append("")
    return "\n".join(lines)


def expand_battery(codebooks, prefix):
    names = set()
    for df in codebooks.values():
        mask = df["variable_name"].str.startswith(prefix, na=False)
        names.update(df.loc[mask, "variable_name"].tolist())
    return sorted(names)


def load_flagged_variables():
    if not AUDIT_SKELETON.exists():
        sys.exit(f"ERROR: audit skeleton not found at {AUDIT_SKELETON}")
    df = pd.read_csv(AUDIT_SKELETON)
    mask = (df["match_method"] == "exact_name") & (df["value_labels_match"].astype(str) == "FALSE")
    return df.loc[mask, "var_2024"].dropna().tolist()


def main():
    parser = argparse.ArgumentParser(description="Compare RTM value labels across waves.")
    parser.add_argument("variables", nargs="*", help="Variable names to compare.")
    parser.add_argument("--battery", metavar="PREFIX",
                        help="Expand to all variables starting with PREFIX.")
    parser.add_argument("--flagged", action="store_true",
                        help="All exact-name matches flagged as value_labels_match = FALSE.")
    args = parser.parse_args()

    codebooks = load_codebooks()

    targets = list(args.variables)
    if args.battery:
        targets.extend(expand_battery(codebooks, args.battery))
    if args.flagged:
        targets.extend(load_flagged_variables())

    if not targets:
        parser.print_help()
        sys.exit(1)

    seen = set()
    targets = [v for v in targets if not (v in seen or seen.add(v))]

    for varname in targets:
        lookup = lookup_variable(codebooks, varname)
        print(format_comparison(varname, lookup))


if __name__ == "__main__":
    main()
