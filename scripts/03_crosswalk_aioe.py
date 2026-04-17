"""
Script 03: AIOE SOC -> ISCO-08 Crosswalk

Maps Felten et al. AI Occupational Exposure (AIOE) scores from US SOC-2010
codes to ISCO-08 codes using the BLS correspondence table.

Where multiple SOC codes map to one ISCO-08, the mean AIOE is taken.
Where one SOC maps to multiple ISCO-08, the score is duplicated.

Also produces 2-digit and 1-digit ISCO aggregations.

Inputs
------
- data/raw/AIOE_DataAppendix.xlsx  (sheet "Appendix A")
- data/raw/isco_soc_crosswalk.xls  (sheet "2010 SOC to ISCO-08")

Output
------
- data/processed/aioe_isco08.csv
- data/processed/aioe_isco08_2digit.csv
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import numpy as np

from utils import RAW_DIR, PROCESSED_DIR

# ── 1. Load AIOE scores ─────────────────────────────────────────────────────
aioe = pd.read_excel(
    RAW_DIR / "AIOE_DataAppendix.xlsx",
    sheet_name="Appendix A",
)
# Standardise column names
aioe.columns = [c.strip() for c in aioe.columns]
aioe = aioe.rename(columns={"SOC Code": "soc_code",
                              "Occupation Title": "soc_title",
                              "AIOE": "aioe"})
aioe["soc_code"] = aioe["soc_code"].astype(str).str.strip()
aioe["aioe"] = pd.to_numeric(aioe["aioe"], errors="coerce")
aioe = aioe.dropna(subset=["aioe"])
print(f"AIOE: {len(aioe)} occupations loaded.")

# ── 2. Load crosswalk ───────────────────────────────────────────────────────
xwalk = pd.read_excel(
    RAW_DIR / "isco_soc_crosswalk.xls",
    sheet_name="2010 SOC to ISCO-08",
    header=6,  # Header is at row 7 (0-indexed row 6)
)
xwalk.columns = [c.strip() for c in xwalk.columns]
xwalk = xwalk.rename(columns={
    "2010 SOC Code": "soc_code",
    "2010 SOC Title": "soc_title_xwalk",
    "ISCO-08 Code": "isco08_code",
    "ISCO-08 Title EN": "isco08_title",
})
xwalk["soc_code"] = xwalk["soc_code"].astype(str).str.strip()
xwalk["isco08_code"] = xwalk["isco08_code"].astype(str).str.strip()
# Drop rows without valid codes
xwalk = xwalk[xwalk["soc_code"].str.match(r"^\d{2}-\d{4}$", na=False)]
xwalk = xwalk[xwalk["isco08_code"].str.match(r"^\d{1,4}$", na=False)]
print(f"Crosswalk: {len(xwalk)} SOC->ISCO-08 mappings loaded.")

# ── 3. Join AIOE to crosswalk ───────────────────────────────────────────────
merged = xwalk.merge(aioe[["soc_code", "aioe"]], on="soc_code", how="inner")
print(f"Matched: {len(merged)} rows ({merged['soc_code'].nunique()} SOC codes "
      f"-> {merged['isco08_code'].nunique()} ISCO-08 codes).")

# Log unmatched
unmatched_soc = set(aioe["soc_code"]) - set(merged["soc_code"])
if unmatched_soc:
    print(f"Unmatched SOC codes (in AIOE but not in crosswalk): {len(unmatched_soc)}")

# ── 4. Aggregate to ISCO-08 4-digit level ───────────────────────────────────
isco4 = (
    merged
    .groupby("isco08_code")
    .agg(
        isco08_title=("isco08_title", "first"),
        aioe_score=("aioe", "mean"),
        aioe_std=("aioe", "std"),
        n_soc_matches=("soc_code", "nunique"),
    )
    .reset_index()
)
isco4["aioe_std"] = isco4["aioe_std"].fillna(0)
isco4 = isco4.sort_values("aioe_score", ascending=False).reset_index(drop=True)

print(f"\n4-digit ISCO-08: {len(isco4)} occupations.")
print("\nTop 10 by AIOE:")
print(isco4.head(10)[["isco08_code", "isco08_title", "aioe_score"]].to_string(index=False))
print("\nBottom 10 by AIOE:")
print(isco4.tail(10)[["isco08_code", "isco08_title", "aioe_score"]].to_string(index=False))

# ── 5. 2-digit and 1-digit aggregations ─────────────────────────────────────
isco4["isco08_2d"] = isco4["isco08_code"].str[:2]
isco4["isco08_1d"] = isco4["isco08_code"].str[:1]

isco2 = (
    isco4
    .groupby("isco08_2d")
    .agg(aioe_score=("aioe_score", "mean"),
         n_4digit=("isco08_code", "count"))
    .reset_index()
    .sort_values("aioe_score", ascending=False)
    .reset_index(drop=True)
)

isco1 = (
    isco4
    .groupby("isco08_1d")
    .agg(aioe_score=("aioe_score", "mean"),
         n_4digit=("isco08_code", "count"))
    .reset_index()
    .sort_values("aioe_score", ascending=False)
    .reset_index(drop=True)
)

print(f"\n2-digit ISCO-08: {len(isco2)} groups.")
print(isco2.to_string(index=False))
print(f"\n1-digit ISCO-08: {len(isco1)} major groups.")
print(isco1.to_string(index=False))

# ── 6. Save ─────────────────────────────────────────────────────────────────
isco4[["isco08_code", "isco08_title", "aioe_score", "n_soc_matches", "aioe_std"]]\
    .to_csv(PROCESSED_DIR / "aioe_isco08.csv", index=False)
isco2.to_csv(PROCESSED_DIR / "aioe_isco08_2digit.csv", index=False)

print(f"\nSaved to {PROCESSED_DIR / 'aioe_isco08.csv'}")
print(f"Saved to {PROCESSED_DIR / 'aioe_isco08_2digit.csv'}")
