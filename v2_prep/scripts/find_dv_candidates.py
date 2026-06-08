#!/usr/bin/env python3
"""
find_dv_candidates.py

Search both RTM codebooks for variables whose labels match DV keyword patterns.
Produces a side-by-side candidate list for redistribution and social investment items.

Usage:
    python scripts/find_dv_candidates.py
    python scripts/find_dv_candidates.py --output data/processed/dv_candidates.md

Run from the typology-paper/ project root.
"""

import argparse
import json
import re
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CODEBOOK_2022 = PROJECT_ROOT / "data" / "processed" / "rtm_2022_codebook.csv"
CODEBOOK_2024 = PROJECT_ROOT / "data" / "processed" / "rtm_2024_codebook.csv"

# Keyword patterns, grouped by target scale.
# Case-insensitive substring match on Stata variable labels.
# Designed to over-recall — it's easier to discard false positives by eye
# than to chase missing items that never got surfaced.
DV_PATTERNS = {
    "redistribution": [
        r"\btax",                  # tax, taxes, taxation, tax the rich
        r"\brich\b",
        r"wealth(y|ier)?",
        r"redistribut",
        r"inequalit",
        r"income difference",
        r"reduce.*difference",
        r"reduce.*income",
        r"progressive",
        r"top.*earner",
        r"top.*income",
        r"higher earner",
        r"fair share",
        r"pay.*more",              # "the rich should pay more"
        r"should be taxed",
    ],
    "social_investment": [
        r"\beducation\b",
        r"\btraining\b",
        r"retrain",
        r"\bskill(s|ing)?\b",
        r"invest",
        r"active labou?r",
        r"active.*market",
        r"early childhood",
        r"childcare",
        r"child care",
        r"lifelong learn",
        r"upskill",
        r"reskill",
    ],
    "general_welfare_preference": [
        # Backup / context category. Not scale items per se, but often adjacent
        # to redistribution items in the questionnaire and worth eyeballing.
        r"government.*should",
        r"government.*responsib",
        r"should be responsib",
        r"should provide",
        r"should spend",
        r"spend(ing)? more",
        r"spend(ing)? less",
        r"willing.*pay",
        r"willingness to pay",
        r"more tax",
        r"higher tax",
    ],
}


def load_codebooks():
    for path in (CODEBOOK_2022, CODEBOOK_2024):
        if not path.exists():
            sys.exit(f"ERROR: codebook not found at {path}")
    return {
        "2022": pd.read_csv(CODEBOOK_2022),
        "2024": pd.read_csv(CODEBOOK_2024),
    }


def search_codebook(df, patterns, wave_label):
    """Return a list of dicts matching any pattern in the given codebook."""
    hits = []
    compiled = [(p, re.compile(p, re.IGNORECASE)) for p in patterns]
    for _, row in df.iterrows():
        label = row.get("variable_label", "")
        if pd.isna(label) or not label:
            continue
        matched_patterns = [p for p, rx in compiled if rx.search(label)]
        if matched_patterns:
            hits.append({
                "wave": wave_label,
                "variable": row["variable_name"],
                "label": label,
                "matched_on": ", ".join(matched_patterns),
            })
    return hits


def format_value_labels(raw):
    """Short one-line summary of value labels for display."""
    if pd.isna(raw) or raw in ("", "{}"):
        return "(none)"
    try:
        parsed = json.loads(raw)
        items = sorted(parsed.items(), key=lambda kv: (0, float(kv[0])) if str(kv[0]).lstrip("-").replace(".", "").isdigit() else (1, str(kv[0])))
        preview = ", ".join(f"{k}={v}" for k, v in items[:5])
        if len(parsed) > 5:
            preview += f", ... ({len(parsed)} total)"
        return preview
    except (json.JSONDecodeError, TypeError):
        return "(unparseable)"


def attach_value_labels(hits, codebooks):
    """Add value label summary to each hit by looking up the variable in its codebook."""
    for hit in hits:
        df = codebooks[hit["wave"]]
        row = df[df["variable_name"] == hit["variable"]]
        if len(row):
            hit["value_labels"] = format_value_labels(row.iloc[0].get("value_labels_json", ""))
        else:
            hit["value_labels"] = "(not found)"
    return hits


def render_category(category, hits_2022, hits_2024):
    """Render one category (redistribution, social_investment, etc.) as markdown."""
    lines = []
    lines.append(f"## {category.replace('_', ' ').title()}")
    lines.append("")
    lines.append(f"**2022:** {len(hits_2022)} candidate variables")
    lines.append(f"**2024:** {len(hits_2024)} candidate variables")
    lines.append("")

    if not hits_2022 and not hits_2024:
        lines.append("_No matches in either wave._")
        lines.append("")
        return "\n".join(lines)

    # Build a name-keyed index for quick cross-wave alignment
    by_name_2022 = {h["variable"]: h for h in hits_2022}
    by_name_2024 = {h["variable"]: h for h in hits_2024}

    # Pair by variable name where possible, then list orphans
    paired_names = sorted(set(by_name_2022.keys()) & set(by_name_2024.keys()))
    only_2022 = sorted(set(by_name_2022.keys()) - set(by_name_2024.keys()))
    only_2024 = sorted(set(by_name_2024.keys()) - set(by_name_2022.keys()))

    if paired_names:
        lines.append("### Same variable name in both waves")
        lines.append("")
        lines.append("Warning: Name-match does NOT guarantee concept-match. Verify labels.")
        lines.append("")
        for name in paired_names:
            h22 = by_name_2022[name]
            h24 = by_name_2024[name]
            lines.append(f"**`{name}`**")
            lines.append(f"- 2022 label: {h22['label']}")
            lines.append(f"- 2022 values: {h22['value_labels']}")
            lines.append(f"- 2024 label: {h24['label']}")
            lines.append(f"- 2024 values: {h24['value_labels']}")
            if h22['label'].strip() != h24['label'].strip():
                lines.append(f"- WARNING: **Labels differ.** Check for concept drift.")
            lines.append("")

    if only_2022:
        lines.append("### 2022 only")
        lines.append("")
        for name in only_2022:
            h = by_name_2022[name]
            lines.append(f"**`{name}`** -- {h['label']}")
            lines.append(f"- values: {h['value_labels']}")
            lines.append(f"- matched on: `{h['matched_on']}`")
            lines.append("")

    if only_2024:
        lines.append("### 2024 only")
        lines.append("")
        for name in only_2024:
            h = by_name_2024[name]
            lines.append(f"**`{name}`** -- {h['label']}")
            lines.append(f"- values: {h['value_labels']}")
            lines.append(f"- matched on: `{h['matched_on']}`")
            lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Search RTM codebooks for DV candidate variables.")
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Write markdown to this path instead of stdout "
             "(default: print to stdout).")
    args = parser.parse_args()

    codebooks = load_codebooks()

    output = []
    output.append("# RTM DV Candidate Search Results")
    output.append("")
    output.append(f"Codebooks searched: `{CODEBOOK_2022.name}`, `{CODEBOOK_2024.name}`")
    output.append("")
    output.append("Patterns are substring regexes run against Stata variable labels. "
                  "Over-recall by design -- filter false positives by eye.")
    output.append("")
    output.append("---")
    output.append("")

    summary_counts = {}
    for category, patterns in DV_PATTERNS.items():
        hits_2022 = search_codebook(codebooks["2022"], patterns, "2022")
        hits_2024 = search_codebook(codebooks["2024"], patterns, "2024")
        hits_2022 = attach_value_labels(hits_2022, codebooks)
        hits_2024 = attach_value_labels(hits_2024, codebooks)
        summary_counts[category] = (len(hits_2022), len(hits_2024))
        output.append(render_category(category, hits_2022, hits_2024))
        output.append("---")
        output.append("")

    # Summary at the bottom
    output.append("## Summary")
    output.append("")
    output.append("| Category | 2022 hits | 2024 hits |")
    output.append("|---|---|---|")
    for category, (n22, n24) in summary_counts.items():
        output.append(f"| {category.replace('_', ' ')} | {n22} | {n24} |")
    output.append("")
    output.append("## Next steps")
    output.append("")
    output.append("1. Scan each section above. Mark real DV candidates vs. false positives.")
    output.append("2. For real candidates, open the Core Questionnaire PDFs at the matching Q-numbers to read exact wording.")
    output.append("3. Decide the redistribution scale composition (target: 3-5 items, comparable across waves).")
    output.append("4. Decide the social investment scale composition (target: 3-5 items).")
    output.append("5. Add the chosen variables to `v1_analytic_variable_list.md` Section 3 with `verified_by_human = TRUE`.")
    output.append("6. Report Cronbach's alpha for each scale once Script 04 builds them.")
    output.append("")

    rendered = "\n".join(output)

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(rendered, encoding="utf-8")
        print(f"Wrote {out_path}")
        # Also print the summary counts to stdout so the user sees them immediately
        print("\nSummary:")
        for category, (n22, n24) in summary_counts.items():
            print(f"  {category:35s}  2022: {n22:3d}   2024: {n24:3d}")
    else:
        print(rendered)


if __name__ == "__main__":
    main()
