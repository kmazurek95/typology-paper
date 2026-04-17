"""
Script 02: Task-Profile Ratio (Axis 1 -- Displacement vs. Complementarity)

Computes country-level weighted means of skill-use-at-work indices from
PIAAC Cycle 2 (and Cycle 1 for NLD) Public Use Files, then constructs a
task-profile ratio capturing the displacement–complementarity dimension.

Higher ICT use at work relative to routine numeracy/reading use indicates
complementarity; the opposite indicates displacement.

    task_profile_ratio = ict_use_work / (numeracy_use_work + reading_use_work)

Also provides a PCA-based alternative (PC1 of the three standardised indices).

Inputs
------
- data/raw/prg*p2.csv   (Cycle 2 PUFs, semicolon-delimited)
- data/raw/prgnldp1.csv (Cycle 1 PUF for Netherlands)

Output
------
- data/processed/task_profile.csv
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import glob
import warnings

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA

from utils import RAW_DIR, PROCESSED_DIR, CNTRYID_TO_ISO3, ISO3_TO_NAME

warnings.filterwarnings("ignore", category=pd.errors.DtypeWarning)

# ── Variable names by cycle ──────────────────────────────────────────────────
C2_VARS = {
    "ict": "ICTWORKC2",
    "num": "NUMWORKC2",
    "read": "READWORKC2_T1",
}
C1_VARS = {
    "ict": "ICTWORK",
    "num": "NUMWORK",
    "read": "READWORK",
}
WEIGHT = "SPFWT0"

# ── Identify PUF files ──────────────────────────────────────────────────────
cycle2_files = sorted(glob.glob(str(RAW_DIR / "prg*p2.csv")))
cycle1_files = sorted(glob.glob(str(RAW_DIR / "prg*p1.csv")))

print(f"Found {len(cycle2_files)} Cycle 2 files, {len(cycle1_files)} Cycle 1 files.\n")

# ── Process each file ───────────────────────────────────────────────────────
records = []

for fpath in cycle2_files + cycle1_files:
    fname = fpath.split("\\")[-1].split("/")[-1]
    is_cycle1 = fname.endswith("p1.csv")
    var_map = C1_VARS if is_cycle1 else C2_VARS
    cycle = 1 if is_cycle1 else 2

    # Read only needed columns (Cycle 1 uses comma delimiter, Cycle 2 uses semicolon)
    needed = ["CNTRYID", WEIGHT] + list(var_map.values())
    sep = "," if is_cycle1 else ";"
    try:
        df = pd.read_csv(fpath, sep=sep, usecols=needed, low_memory=False)
    except ValueError:
        print(f"  WARNING: {fname} -- missing expected columns, skipping.")
        continue

    # Convert to numeric
    for col in list(var_map.values()) + [WEIGHT]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Drop rows where weight is zero/missing or all skill vars are missing
    df = df[df[WEIGHT] > 0].copy()
    skill_cols = list(var_map.values())
    df = df.dropna(subset=skill_cols, how="all")

    # Compute weighted means per country (files are single-country but be safe)
    for cntryid, grp in df.groupby("CNTRYID"):
        iso3 = CNTRYID_TO_ISO3.get(int(cntryid))
        if iso3 is None:
            continue
        w = grp[WEIGHT].values
        means = {}
        for key, col in var_map.items():
            valid = grp[[col, WEIGHT]].dropna()
            if len(valid) > 0:
                means[key] = np.average(valid[col], weights=valid[WEIGHT])
            else:
                means[key] = np.nan

        records.append({
            "country_iso3": iso3,
            "ict_use_work": means["ict"],
            "numeracy_use_work": means["num"],
            "reading_use_work": means["read"],
            "n_respondents": len(grp),
            "cycle": cycle,
        })
        print(f"  {fname}: {iso3} (n={len(grp)}, cycle={cycle}) -- "
              f"ICT={means['ict']:.3f}, NUM={means['num']:.3f}, "
              f"READ={means['read']:.3f}")

# ── Assemble DataFrame ──────────────────────────────────────────────────────
out = pd.DataFrame(records)
out["country_name"] = out["country_iso3"].map(ISO3_TO_NAME)

# ── Compute task-profile ratio ───────────────────────────────────────────────
out["task_profile_ratio"] = (
    out["ict_use_work"]
    / (out["numeracy_use_work"] + out["reading_use_work"])
)

# ── PCA alternative ──────────────────────────────────────────────────────────
skill_cols = ["ict_use_work", "numeracy_use_work", "reading_use_work"]
valid_mask = out[skill_cols].notna().all(axis=1)
if valid_mask.sum() >= 3:
    X = out.loc[valid_mask, skill_cols].values
    X_z = (X - X.mean(axis=0)) / X.std(axis=0)
    pca = PCA(n_components=1)
    pc1 = pca.fit_transform(X_z).ravel()
    # Orient so higher = more complementarity (higher ICT loading)
    if pca.components_[0, 0] < 0:
        pc1 = -pc1
    out.loc[valid_mask, "task_profile_pc1"] = pc1
    print(f"\nPCA loadings: ICT={pca.components_[0,0]:.3f}, "
          f"NUM={pca.components_[0,1]:.3f}, READ={pca.components_[0,2]:.3f}")
    print(f"Variance explained: {pca.explained_variance_ratio_[0]:.1%}")

# ── Flag Cycle 1 countries ───────────────────────────────────────────────────
out["cycle1_flag"] = out["cycle"] == 1

# ── Validate ─────────────────────────────────────────────────────────────────
print(f"\nTask profile computed for {len(out)} countries.\n")
out_sorted = out.sort_values("task_profile_ratio", ascending=False)
print(out_sorted[["country_iso3", "country_name", "ict_use_work",
                   "numeracy_use_work", "reading_use_work",
                   "task_profile_ratio"]].to_string(index=False))

nordic = out[out["country_iso3"].isin(["DNK", "SWE", "NOR", "FIN"])]
southern = out[out["country_iso3"].isin(["ESP", "ITA", "PRT"])]
print(f"\nNordic mean ratio:    {nordic['task_profile_ratio'].mean():.4f}")
print(f"Southern mean ratio:  {southern['task_profile_ratio'].mean():.4f}")

# ── Save ─────────────────────────────────────────────────────────────────────
out_cols = ["country_iso3", "country_name", "ict_use_work", "numeracy_use_work",
            "reading_use_work", "task_profile_ratio", "task_profile_pc1",
            "n_respondents", "cycle", "cycle1_flag"]
out[out_cols].to_csv(PROCESSED_DIR / "task_profile.csv", index=False)
print(f"\nSaved to {PROCESSED_DIR / 'task_profile.csv'}")
