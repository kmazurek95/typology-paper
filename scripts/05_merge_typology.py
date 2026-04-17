"""
Script 05: Merge Typology Positions

Merges the two axes (task-profile ratio and dualization gap) by country,
standardises both to z-scores, and assigns each country to one of four
cells in the 2×2 typology based on median splits.

Inputs
------
- data/processed/epl_gap.csv
- data/processed/task_profile.csv

Output
------
- data/processed/typology_positions.csv
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import numpy as np

from utils import PROCESSED_DIR, CLUSTER_LABELS, CLUSTER_SHORT

# ── 1. Load both axes ───────────────────────────────────────────────────────
epl = pd.read_csv(PROCESSED_DIR / "epl_gap.csv")
task = pd.read_csv(PROCESSED_DIR / "task_profile.csv")

print(f"EPL gap:      {len(epl)} countries")
print(f"Task profile: {len(task)} countries")

# ── 2. Merge on ISO-3 ───────────────────────────────────────────────────────
merged = pd.merge(
    task[["country_iso3", "country_name", "ict_use_work", "numeracy_use_work",
          "reading_use_work", "task_profile_ratio", "task_profile_pc1",
          "cycle", "cycle1_flag"]],
    epl[["country_iso3", "eprc", "ept", "dualization_gap", "year", "temp_share"]],
    on="country_iso3",
    how="inner",
)
print(f"Merged:       {len(merged)} countries (intersection)\n")

# Countries dropped
dropped_task = set(task["country_iso3"]) - set(merged["country_iso3"])
dropped_epl = set(epl["country_iso3"]) - set(merged["country_iso3"])
if dropped_task:
    print(f"  In task profile but not EPL: {sorted(dropped_task)}")
if dropped_epl:
    print(f"  In EPL but not task profile: {sorted(dropped_epl)}")

# ── 3. Standardise to z-scores ──────────────────────────────────────────────
# Use PC1 as primary Axis 1 measure (captures overall task complexity / skill
# intensity at work; high = complementarity-leaning, low = displacement-leaning)
merged["z_task_profile"] = (
    (merged["task_profile_pc1"] - merged["task_profile_pc1"].mean())
    / merged["task_profile_pc1"].std()
)
merged["z_dualization"] = (
    (merged["dualization_gap"] - merged["dualization_gap"].mean())
    / merged["dualization_gap"].std()
)

# ── 4. Assign 2x2 clusters via median split ─────────────────────────────────
med_task = merged["task_profile_pc1"].median()
med_dual = merged["dualization_gap"].median()

def assign_cluster(row):
    complementary = row["task_profile_pc1"] >= med_task
    deep = row["dualization_gap"] >= med_dual
    if complementary and not deep:
        return 1   # Complementary + Narrow gap
    elif complementary and deep:
        return 2   # Complementary + Deep gap
    elif not complementary and not deep:
        return 3   # Displacement + Narrow gap
    else:
        return 4   # Displacement + Deep gap

merged["cluster"] = merged.apply(assign_cluster, axis=1)
merged["cluster_label"] = merged["cluster"].map(CLUSTER_SHORT)

# ── 5. Flag Germany as diagnostic case ───────────────────────────────────────
merged["diagnostic_case"] = merged["country_iso3"] == "DEU"

# ── 6. Validate ─────────────────────────────────────────────────────────────
print(f"\nMedian task_profile_pc1:  {med_task:.4f}")
print(f"Median dualization_gap:  {med_dual:.3f}\n")

for c in sorted(merged["cluster"].unique()):
    members = merged[merged["cluster"] == c]
    codes = ", ".join(sorted(members["country_iso3"]))
    print(f"Cell {c} ({CLUSTER_SHORT[c]}): {codes}")

print(f"\nAll countries:")
display = merged.sort_values("cluster")[
    ["country_iso3", "country_name", "task_profile_pc1", "dualization_gap",
     "z_task_profile", "z_dualization", "cluster_label", "diagnostic_case"]
]
print(display.to_string(index=False))

# ── 7. Save ─────────────────────────────────────────────────────────────────
out_cols = [
    "country_iso3", "country_name",
    "task_profile_ratio", "dualization_gap",
    "z_task_profile", "z_dualization",
    "cluster", "cluster_label", "diagnostic_case",
    "ict_use_work", "numeracy_use_work", "reading_use_work",
    "task_profile_pc1", "eprc", "ept", "year", "temp_share",
    "cycle", "cycle1_flag",
]
merged[out_cols].to_csv(PROCESSED_DIR / "typology_positions.csv", index=False)
print(f"\nSaved to {PROCESSED_DIR / 'typology_positions.csv'}")
