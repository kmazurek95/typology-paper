"""
Produce the AIOE validation scatter plot (Figure A1).

Reads data/processed/pca_aioe_validation.csv (produced by script 03b).
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8")

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy import stats
from utils import FIGURES_DIR, CLUSTER_COLORS, setup_plot_style

setup_plot_style()

from utils import PROCESSED_DIR
df = pd.read_csv(PROCESSED_DIR / "pca_aioe_validation.csv")

# Correlation stats
r, p = stats.pearsonr(df["task_profile_pc1"], df["mean_aioe"])
rho, p_s = stats.spearmanr(df["task_profile_pc1"], df["mean_aioe"])

fig, ax = plt.subplots(figsize=(7, 5.5))

for _, row in df.iterrows():
    c = int(row["cluster"])
    ax.scatter(row["task_profile_pc1"], row["mean_aioe"],
               c=CLUSTER_COLORS[c], s=50, edgecolors="white", linewidths=0.5, zorder=3)
    ax.annotate(row["country_iso3"],
                (row["task_profile_pc1"], row["mean_aioe"]),
                fontsize=7, ha="center", va="bottom",
                xytext=(0, 5), textcoords="offset points", zorder=4)

# Regression line
slope, intercept = np.polyfit(df["task_profile_pc1"], df["mean_aioe"], 1)
x_line = np.linspace(df["task_profile_pc1"].min() - 0.3, df["task_profile_pc1"].max() + 0.3, 100)
ax.plot(x_line, slope * x_line + intercept, color="grey", linewidth=1, linestyle="--", alpha=0.6)

ax.text(0.05, 0.95, f"r = {r:.2f} (p < .001)\nrho = {rho:.2f} (p < .001)\nN = {len(df)}",
        transform=ax.transAxes, fontsize=9, va="top",
        bbox=dict(boxstyle="round", facecolor="white", edgecolor="lightgrey", alpha=0.9))

ax.set_xlabel("PIAAC Task Complexity (PC1)")
ax.set_ylabel("Mean Felten AIOE Score\n(Eurostat employment-weighted)")
ax.set_title("Validation: PIAAC Task Complexity vs. AI Occupational Exposure", pad=10)

fig.savefig(FIGURES_DIR / "figure_a1_pca_aioe_validation.png")
print(f"Saved {FIGURES_DIR / 'figure_a1_pca_aioe_validation.png'}")
plt.close(fig)
