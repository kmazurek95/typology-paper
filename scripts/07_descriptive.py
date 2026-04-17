"""
Script 07: Descriptive Figures

1. Typology scatter plot (signature figure): countries on the 2D space,
   coloured by cluster, with Germany annotated as the diagnostic case.
2. Preference-by-cluster comparison: redistribution support (RTM g3-5)
   and education spending support (RTM g3-7) grouped by cluster.

Inputs
------
- data/processed/typology_positions.csv
- data/raw/2022_RTM.xlsx  (sheets g3-5, g3-7)
- data/raw/gincdif-cntry.xlsx  (ESS11 redistribution, supplementary)

Output
------
- figures/typology_scatter.png
- figures/preference_by_cluster.png
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

try:
    from adjustText import adjust_text
    HAS_ADJUST_TEXT = True
except ImportError:
    HAS_ADJUST_TEXT = False

from utils import (
    PROCESSED_DIR, RAW_DIR, FIGURES_DIR,
    CLUSTER_COLORS, CLUSTER_SHORT,
    NAME_TO_ISO3, setup_plot_style,
)

setup_plot_style()

# ── 1. Load typology positions ───────────────────────────────────────────────
typo = pd.read_csv(PROCESSED_DIR / "typology_positions.csv")
print(f"Typology: {len(typo)} countries.\n")


# ══════════════════════════════════════════════════════════════════════════════
# FIGURE 1: TYPOLOGY SCATTER PLOT
# ══════════════════════════════════════════════════════════════════════════════

fig, ax = plt.subplots(figsize=(9, 7.5))

# Draw quadrant lines at z = 0 (approximately the median)
ax.axhline(0, color="grey", linewidth=0.7, linestyle="--", alpha=0.4, zorder=1)
ax.axvline(0, color="grey", linewidth=0.7, linestyle="--", alpha=0.4, zorder=1)

# Manual label offsets (dx, dy in points) for crowded areas
MANUAL_OFFSETS = {
    "ITA": (-12, -10),
    "HUN": (-12, 5),
    "SVK": (-12, -10),
    "CHL": (12, 5),
    "LTU": (12, -10),
    "KOR": (0, -12),
    "AUT": (12, -8),
    "POL": (12, 5),
    "LVA": (12, 5),
    "SWE": (12, 5),
    "IRL": (0, 6),
    "CAN": (12, -8),
    "NLD": (0, 6),
    "GBR": (12, 5),
    "ISR": (-12, 5),
    "CZE": (-12, 5),
}

# Plot each cluster
for _, row in typo.iterrows():
    c = int(row["cluster"])
    color = CLUSTER_COLORS[c]
    marker = "D" if row["diagnostic_case"] else "o"
    size = 80 if row["diagnostic_case"] else 55
    ax.scatter(row["z_task_profile"], row["z_dualization"],
               c=color, marker=marker, s=size, edgecolors="white",
               linewidths=0.5, zorder=3)
    weight = "bold" if row["diagnostic_case"] else "normal"
    iso3 = row["country_iso3"]
    dx, dy = MANUAL_OFFSETS.get(iso3, (0, 6))
    ha = "left" if dx > 0 else ("right" if dx < 0 else "center")
    ax.annotate(
        iso3,
        (row["z_task_profile"], row["z_dualization"]),
        fontsize=7.5, fontweight=weight, ha=ha, va="center",
        xytext=(dx, dy), textcoords="offset points", zorder=4,
        arrowprops=dict(arrowstyle="-", color="grey", lw=0.3, alpha=0.3,
                        shrinkA=0, shrinkB=3)
        if iso3 in MANUAL_OFFSETS and (abs(dx) > 10 or abs(dy) > 10) else None,
    )

# Set generous axis limits so all points + labels fit inside the frame
y_vals = typo["z_dualization"].values
x_vals = typo["z_task_profile"].values
ax.set_ylim(y_vals.min() - 0.6, y_vals.max() + 0.6)
ax.set_xlim(x_vals.min() - 0.5, x_vals.max() + 0.5)

# Quadrant corner annotations
pad = 0.15
xmin, xmax = ax.get_xlim()
ymin, ymax = ax.get_ylim()
corners = [
    (xmax - pad, ymin + pad, "Compl. + Narrow gap", "right", "bottom",
     CLUSTER_COLORS[1]),
    (xmax - pad, ymax - pad, "Compl. + Deep gap", "right", "top",
     CLUSTER_COLORS[2]),
    (xmin + pad, ymin + pad, "Displ. + Narrow gap", "left", "bottom",
     CLUSTER_COLORS[3]),
    (xmin + pad, ymax - pad, "Displ. + Deep gap", "left", "top",
     CLUSTER_COLORS[4]),
]
for cx, cy, label, ha, va, color in corners:
    ax.text(cx, cy, label, fontsize=8.5, fontstyle="italic", color=color,
            ha=ha, va=va, alpha=0.8)

ax.set_xlabel("Task-Profile Composition\n(Displacement  ←  →  Complementarity)")
ax.set_ylabel("Dualization Gap\n(Narrow  ←  →  Deep)")
ax.set_title("OECD Countries: AI Task Profile × Labor Market Dualization", pad=12)

# Legend
CLUSTER_LEGEND = {
    1: "Compl. + Narrow gap",
    2: "Compl. + Deep gap",
    3: "Displ. + Narrow gap",
    4: "Displ. + Deep gap",
}
handles = [mpatches.Patch(color=CLUSTER_COLORS[c], label=CLUSTER_LEGEND[c])
           for c in [1, 2, 3, 4]]
handles.append(plt.Line2D([0], [0], marker="D", color="grey", linestyle="None",
                           markersize=6, label="Germany (diagnostic)"))
ax.legend(handles=handles, loc="upper left", frameon=True, framealpha=0.9,
          edgecolor="lightgrey")

fig.savefig(FIGURES_DIR / "figure1_typology_scatter.png")
print(f"Saved {FIGURES_DIR / 'figure1_typology_scatter.png'}")
plt.close(fig)


# ══════════════════════════════════════════════════════════════════════════════
# FIGURE 2: PREFERENCE BY CLUSTER
# ══════════════════════════════════════════════════════════════════════════════

# ── Parse RTM 2022 g3-5 (redistribution) ─────────────────────────────────────
from openpyxl import load_workbook

wb = load_workbook(RAW_DIR / "2022_RTM.xlsx", data_only=True)

def parse_rtm_sheet(ws, value_col, start_row, end_row):
    """Extract country-name → value from an RTM statlinks sheet."""
    records = {}
    for row in ws.iter_rows(min_row=start_row, max_row=end_row,
                            max_col=max(value_col, 1) + 1, values_only=False):
        name_cell = row[0].value
        val_cell = row[value_col - 1].value if value_col <= len(row) else None
        if name_cell and val_cell and name_cell != "Average":
            iso3 = NAME_TO_ISO3.get(str(name_cell).strip())
            if iso3:
                try:
                    records[iso3] = float(val_cell)
                except (ValueError, TypeError):
                    pass
    return records

# g3-5: redistribution ("Yes or definitely yes" in col B=2)
redist_data = parse_rtm_sheet(wb["g3-5"], value_col=2, start_row=25, end_row=53)

# g3-7: education spending ("Education services and supports" in col F=6)
eduspend_data = parse_rtm_sheet(wb["g3-7"], value_col=6, start_row=36, end_row=62)

print(f"\nRTM redistribution: {len(redist_data)} countries")
print(f"RTM education spending: {len(eduspend_data)} countries")

# Merge with typology
pref = typo[["country_iso3", "cluster", "cluster_label"]].copy()
pref["redist_pct"] = pref["country_iso3"].map(redist_data)
pref["eduspend_pct"] = pref["country_iso3"].map(eduspend_data)

# Drop countries without preference data
pref_valid = pref.dropna(subset=["redist_pct", "eduspend_pct"])
print(f"Countries with both preference measures: {len(pref_valid)}")

# ── Build grouped bar chart ──────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(9, 5.5))

clusters_order = [1, 2, 3, 4]
cluster_names = ["Compl. +\nNarrow", "Compl. +\nDeep", "Displ. +\nNarrow", "Displ. +\nDeep"]
x = np.arange(len(clusters_order))
width = 0.35

redist_means = []
eduspend_means = []
redist_points = {c: [] for c in clusters_order}
eduspend_points = {c: [] for c in clusters_order}

for c in clusters_order:
    grp = pref_valid[pref_valid["cluster"] == c]
    redist_means.append(grp["redist_pct"].mean() if len(grp) > 0 else 0)
    eduspend_means.append(grp["eduspend_pct"].mean() if len(grp) > 0 else 0)
    for _, row in grp.iterrows():
        redist_points[c].append(row["redist_pct"])
        eduspend_points[c].append(row["eduspend_pct"])

bars1 = ax.bar(x - width / 2, redist_means, width, label="Redistribution\n(tax the rich more)",
               color="#2166ac", alpha=0.8, edgecolor="white")
bars2 = ax.bar(x + width / 2, eduspend_means, width, label="Education spending\n(spend more on education)",
               color="#b2182b", alpha=0.8, edgecolor="white")

# Overlay individual country dots
for i, c in enumerate(clusters_order):
    for val in redist_points[c]:
        ax.scatter(i - width / 2, val, color="#2166ac", s=18, alpha=0.5,
                   edgecolors="white", linewidths=0.3, zorder=5)
    for val in eduspend_points[c]:
        ax.scatter(i + width / 2, val, color="#b2182b", s=18, alpha=0.5,
                   edgecolors="white", linewidths=0.3, zorder=5)

ax.set_xticks(x)
ax.set_xticklabels(cluster_names)
ax.set_ylabel("% of respondents")
ax.set_title("Welfare Preferences by Typology Cluster (RTM 2022)", pad=10)
ax.legend(loc="upper right", frameon=True, framealpha=0.9, edgecolor="lightgrey")
ax.set_ylim(0, 100)

fig.savefig(FIGURES_DIR / "figure2_preferences_by_cluster.png")
print(f"Saved {FIGURES_DIR / 'figure2_preferences_by_cluster.png'}")
plt.close(fig)

print("\nDone.")
