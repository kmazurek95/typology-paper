"""
Script 01: EPL Gap Computation (Axis 2 — Dualization)

Computes dualization_gap = EPRC - EPT for each country using OECD EPL data.

The OECD files code EPRC as MEASURE='EPL_OV' (descriptive label:
"Individual and collective dismissals (regular contracts)") and EPT as
MEASURE='EPL_T' ("Temporary contracts").

Uses Version 4 (EPLex) where available, falling back through V3 → V2 → V1.
Keeps the most recent year per country.  Supplements with Eurostat temporary
employment shares for robustness.

Inputs
------
- data/raw/oecd_epl_v4.csv                          (V4: EPRC + EPT)
- data/raw/oecd_epl_overview_all-versions_v1-v4.csv.csv  (V1-V4: EPRC only)
- data/raw/estat_lfsi_pt_a_en.csv                    (Eurostat temp share)

Output
------
- data/processed/epl_gap.csv
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import numpy as np
from utils import RAW_DIR, PROCESSED_DIR, ISO2_TO_ISO3, ISO3_TO_NAME

# ── 1. Load V4 file (has both EPRC and EPT) ─────────────────────────────────
v4 = pd.read_csv(RAW_DIR / "oecd_epl_v4.csv")
v4 = v4[["REF_AREA", "Reference area", "MEASURE", "VERSION",
          "TIME_PERIOD", "OBS_VALUE"]].copy()
v4["OBS_VALUE"] = pd.to_numeric(v4["OBS_VALUE"], errors="coerce")
v4 = v4.dropna(subset=["OBS_VALUE"])
v4 = v4[v4["REF_AREA"] != "OECD"]

# Split into EPRC (coded EPL_OV) and EPT (coded EPL_T)
eprc_v4 = v4[v4["MEASURE"] == "EPL_OV"].copy()
ept_v4 = v4[v4["MEASURE"] == "EPL_T"].copy()

# ── 2. Load overview file (EPRC across all versions, for fallback) ───────────
overview = pd.read_csv(
    RAW_DIR / "oecd_epl_overview_all-versions_v1-v4.csv.csv"
)
overview = overview[["REF_AREA", "Reference area", "MEASURE", "VERSION",
                      "TIME_PERIOD", "OBS_VALUE"]].copy()
overview["OBS_VALUE"] = pd.to_numeric(overview["OBS_VALUE"], errors="coerce")
overview = overview.dropna(subset=["OBS_VALUE"])
overview = overview[overview["REF_AREA"] != "OECD"]

# ── 3. Build EPRC series: prefer V4, fall back through V3/V2/V1 ─────────────
version_priority = {"VERSION4": 0, "VERSION3": 1, "VERSION2": 2, "VERSION1": 3}

# Combine V4 EPRC with overview (which adds V1-V3 for countries not in V4)
eprc_all = pd.concat([eprc_v4, overview], ignore_index=True)
eprc_all["v_rank"] = eprc_all["VERSION"].map(version_priority)
eprc_all = eprc_all.dropna(subset=["v_rank"])

# For each country: pick best version, then most recent year
eprc_all = eprc_all.sort_values(["REF_AREA", "v_rank", "TIME_PERIOD"],
                                 ascending=[True, True, False])
eprc_best = eprc_all.groupby("REF_AREA").first().reset_index()
eprc_best = eprc_best.rename(columns={"OBS_VALUE": "eprc",
                                       "TIME_PERIOD": "eprc_year",
                                       "VERSION": "eprc_version"})

# ── 4. Build EPT series (V4 only — that's all we have) ──────────────────────
ept_v4 = ept_v4.sort_values(["REF_AREA", "TIME_PERIOD"], ascending=[True, False])
ept_best = ept_v4.groupby("REF_AREA").first().reset_index()
ept_best = ept_best.rename(columns={"OBS_VALUE": "ept",
                                     "TIME_PERIOD": "ept_year"})

# ── 5. Merge EPRC and EPT, compute gap ──────────────────────────────────────
merged = pd.merge(
    eprc_best[["REF_AREA", "Reference area", "eprc", "eprc_year", "eprc_version"]],
    ept_best[["REF_AREA", "ept", "ept_year"]],
    on="REF_AREA",
    how="inner",
)
merged["dualization_gap"] = merged["eprc"] - merged["ept"]

# Use the later year as the reference year
merged["year"] = merged[["eprc_year", "ept_year"]].max(axis=1)

# ── 6. Eurostat temporary employment share (supplementary) ───────────────────
euro = pd.read_csv(RAW_DIR / "estat_lfsi_pt_a_en.csv")
euro = euro[
    (euro["wstatus"] == "EMP_TEMP")
    & (euro["sex"] == "T")
    & (euro["age"] == "Y15-64")
].copy()
euro["OBS_VALUE"] = pd.to_numeric(euro["OBS_VALUE"], errors="coerce")
euro = euro.dropna(subset=["OBS_VALUE"])
# Most recent year per country
euro = euro.sort_values(["geo", "TIME_PERIOD"], ascending=[True, False])
euro = euro.groupby("geo").first().reset_index()
euro["country_iso3"] = euro["geo"].map(ISO2_TO_ISO3)
euro = euro.dropna(subset=["country_iso3"])
euro = euro[["country_iso3", "OBS_VALUE"]].rename(
    columns={"OBS_VALUE": "temp_share"}
)

# ── 7. Assemble final output ────────────────────────────────────────────────
out = merged.rename(columns={"REF_AREA": "country_iso3",
                              "Reference area": "country_name"})
out = out.merge(euro, on="country_iso3", how="left")
out = out[["country_iso3", "country_name", "eprc", "ept",
           "dualization_gap", "year", "temp_share"]].copy()
out = out.sort_values("dualization_gap", ascending=False).reset_index(drop=True)

# ── 8. Validate ─────────────────────────────────────────────────────────────
print(f"EPL gap computed for {len(out)} countries.\n")
print(out[["country_iso3", "country_name", "eprc", "ept",
           "dualization_gap"]].to_string(index=False))

# Spot checks
nordic = out[out["country_iso3"].isin(["DNK", "SWE", "NOR", "FIN"])]
southern = out[out["country_iso3"].isin(["ESP", "ITA", "GRC", "PRT"])]
deu = out[out["country_iso3"] == "DEU"]
print(f"\nNordic mean gap:    {nordic['dualization_gap'].mean():.3f}")
print(f"Southern mean gap:  {southern['dualization_gap'].mean():.3f}")
print(f"Germany gap:        {deu['dualization_gap'].values[0]:.3f}")

# ── 9. Save ─────────────────────────────────────────────────────────────────
out.to_csv(PROCESSED_DIR / "epl_gap.csv", index=False)
print(f"\nSaved to {PROCESSED_DIR / 'epl_gap.csv'}")
