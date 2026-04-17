"""
Script 03b: AIOE External Validation

Validates the PIAAC-derived task complexity index (Axis 1, PC1) against
country-level Felten AIOE scores aggregated using Eurostat employment shares
by ISCO-08 major group.

Steps
-----
1. Download Eurostat table lfsa_eisn2 (employment by NACE, ISCO-08, sex, age)
   or read a cached local copy.
2. Filter to: both sexes, age 15+, ISCO OC1-OC9, most recent year per country.
   Sum across all NACE sectors to get total employment by 1-digit ISCO.
3. Aggregate AIOE scores from script 03 output to 1-digit ISCO.
4. Compute employment-weighted mean AIOE per country.
5. Merge with typology positions (script 05 output) for PC1 and cluster.
6. Report Pearson r and Spearman rho.

Inputs
------
- Eurostat lfsa_eisn2 (downloaded or cached at data/raw/eurostat_lfsa_eisn2.csv)
- data/processed/aioe_isco08.csv  (4-digit AIOE from script 03)
- data/processed/typology_positions.csv  (from script 05)

Output
------
- data/raw/eurostat_lfsa_eisn2.csv  (cached download, ~18 MB)
- data/processed/eurostat_emp_by_isco.csv
- data/processed/pca_aioe_validation.csv
"""

import io
import os
import sys
import urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8")

import numpy as np
import pandas as pd
from scipy import stats

from utils import RAW_DIR, PROCESSED_DIR, ISO2_TO_ISO3, CLUSTER_SHORT

# ── 1. Download or read Eurostat lfsa_eisn2 ────────────────────────────────

# Full table download: all NACE sectors, both sexes, both age groups,
# ISCO 1-digit codes, years 2019-2023. We filter after loading.
EUROSTAT_URL = (
    "https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/"
    "lfsa_eisn2"
    "?format=SDMX-CSV"
    "&startPeriod=2019&endPeriod=2023"
)

CACHE_PATH = RAW_DIR / "eurostat_lfsa_eisn2.csv"


def download_eurostat():
    """Download Eurostat lfsa_eisn2 table."""
    print("Downloading Eurostat lfsa_eisn2 (this may take a minute) ...")
    req = urllib.request.Request(
        EUROSTAT_URL,
        headers={"Accept": "application/vnd.sdmx.data+csv;version=1.0.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            raw = resp.read()
        CACHE_PATH.write_bytes(raw)
        print(f"  Saved to {CACHE_PATH} ({len(raw):,} bytes)")
        return pd.read_csv(io.BytesIO(raw))
    except Exception as e:
        print(f"  Download failed: {e}")
        return None


if CACHE_PATH.exists():
    print(f"Using cached Eurostat data from {CACHE_PATH}")
    euro = pd.read_csv(CACHE_PATH)
else:
    euro = download_eurostat()
    if euro is None:
        print("ERROR: Cannot download Eurostat data and no cache exists.")
        print(f"  Please download Eurostat table lfsa_eisn2 manually from:")
        print(f"  https://ec.europa.eu/eurostat/databrowser/view/lfsa_eisn2/")
        print(f"  Save as: {CACHE_PATH}")
        sys.exit(1)

# ── 2. Process Eurostat data ───────────────────────────────────────────────

euro.columns = [c.strip().lower() for c in euro.columns]

# Keep only ISCO 1-digit codes (OC1 .. OC9)
euro = euro[euro["isco08"].str.match(r"^OC\d$", na=False)].copy()
euro["isco_1digit"] = euro["isco08"].str.replace("OC", "").astype(int)

# Filter: both sexes, age 15+ (broadest working-age population)
euro = euro[(euro["sex"] == "T") & (euro["age"] == "Y_GE15")]

euro["obs_value"] = pd.to_numeric(euro["obs_value"], errors="coerce")
euro = euro.dropna(subset=["obs_value"])
euro = euro[euro["obs_value"] > 0]

# Most recent year per country
euro["time_period"] = pd.to_numeric(euro["time_period"], errors="coerce")
latest_year = euro.groupby("geo")["time_period"].max().reset_index()
latest_year.columns = ["geo", "latest_year"]
euro = euro.merge(latest_year, on="geo")
euro = euro[euro["time_period"] == euro["latest_year"]]

# Sum across all NACE sectors to get total employment by ISCO per country
emp = (
    euro
    .groupby(["geo", "isco_1digit"])["obs_value"]
    .sum()
    .reset_index()
)

# Map ISO2 to ISO3
emp["country_iso3"] = emp["geo"].map(ISO2_TO_ISO3)
emp = emp.dropna(subset=["country_iso3"])

# Compute employment shares within each country
country_totals = emp.groupby("country_iso3")["obs_value"].sum().reset_index()
country_totals.columns = ["country_iso3", "total_emp"]
emp = emp.merge(country_totals, on="country_iso3")
emp["emp_share"] = emp["obs_value"] / emp["total_emp"]

# Save processed Eurostat data
emp_out = emp[["geo", "isco_1digit", "obs_value"]].copy()
emp_out.to_csv(PROCESSED_DIR / "eurostat_emp_by_isco.csv", index=False)
print(f"\nSaved {PROCESSED_DIR / 'eurostat_emp_by_isco.csv'} "
      f"({len(emp_out)} rows, {emp_out['geo'].nunique()} countries)")

# ── 3. Aggregate AIOE to 1-digit ISCO ─────────────────────────────────────

aioe4 = pd.read_csv(PROCESSED_DIR / "aioe_isco08.csv")
aioe4["isco_1digit"] = aioe4["isco08_code"].astype(str).str[:1].astype(int)

aioe1 = (
    aioe4
    .groupby("isco_1digit")
    .agg(aioe_score=("aioe_score", "mean"))
    .reset_index()
)
print(f"\nAIOE 1-digit scores:")
print(aioe1.to_string(index=False))

# ── 4. Employment-weighted mean AIOE per country ──────────────────────────

merged = emp.merge(aioe1, on="isco_1digit", how="inner")
merged["weighted_aioe"] = merged["emp_share"] * merged["aioe_score"]

country_aioe = (
    merged
    .groupby("country_iso3")
    .agg(mean_aioe=("weighted_aioe", "sum"))
    .reset_index()
)

# ── 5. Merge with typology positions ───────────────────────────────────────

typo = pd.read_csv(PROCESSED_DIR / "typology_positions.csv")
typo = typo[["country_iso3", "task_profile_pc1", "cluster", "cluster_label"]]

val = typo.merge(country_aioe, on="country_iso3", how="inner")
val = val.sort_values("country_iso3").reset_index(drop=True)

print(f"\nValidation dataset: {len(val)} countries")
print(val.to_string(index=False))

# ── 6. Compute and report correlation ──────────────────────────────────────

r, p = stats.pearsonr(val["task_profile_pc1"], val["mean_aioe"])
rho, p_s = stats.spearmanr(val["task_profile_pc1"], val["mean_aioe"])

print(f"\n{'='*50}")
print(f"Pearson  r   = {r:.4f}  (p = {p:.6f})")
print(f"Spearman rho = {rho:.4f}  (p = {p_s:.6f})")
print(f"N = {len(val)} European countries")
print(f"{'='*50}")

# ── 7. Save ────────────────────────────────────────────────────────────────

val.to_csv(PROCESSED_DIR / "pca_aioe_validation.csv", index=False)
print(f"\nSaved {PROCESSED_DIR / 'pca_aioe_validation.csv'}")
