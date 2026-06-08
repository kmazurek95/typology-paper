"""
Compute: among employed workers who perceive high automation risk,
% who support government retraining — by country.
Uses RTM 2022 microdata.
  q41a: "How likely: Job replaced by robot, computer, etc." (3=Likely, 4=Very likely)
  q42b: "Government action: Re-training" (4=Support, 5=Strongly support)
"""

import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings("ignore")

DTA = (
    "data/OECD_RTM_2022_Public_Use_Microdata"
    "/FinalData_dta/FinalData_dta"
    "/OECD_RTM_2022_Public_Use_Microdata.dta"
)
TYPO_CSV = "data/processed/typology_positions.csv"

TYPO_COUNTRIES = [
    "AUT","BEL","CAN","CHE","CHL","CZE","DEU","DNK","ESP","EST",
    "FIN","FRA","GBR","HUN","IRL","ISR","ITA","JPN","KOR","LTU",
    "LVA","NOR","NZL","POL","PRT","SVK","SWE","USA","NLD",
]

df = pd.read_stata(DTA, convert_categoricals=False)
typo = pd.read_csv(TYPO_CSV)[["country_iso3","country_name","z_task_profile","z_dualization","cluster_label"]]

# Employed respondents in typology countries
sub = df[df["ctrcode"].isin(TYPO_COUNTRIES) & (df["s9"] == 1)].copy()

# Valid responses only
valid = sub[sub["q41a"].isin([1,2,3,4]) & sub["q42b"].isin([1,2,3,4,5])].copy()

# High automation risk: q41a in (3,4)
high_risk = valid[valid["q41a"].isin([3,4])].copy()
high_risk["retrain_support"] = high_risk["q42b"].isin([4,5])

# Weighted % by country
result = (
    high_risk.groupby("ctrcode")
    .apply(lambda g: np.average(g["retrain_support"], weights=g["weight"]))
    .reset_index()
)
result.columns = ["country_iso3", "pct_retrain"]
result = result.merge(typo, on="country_iso3", how="left")
result = result.sort_values("pct_retrain", ascending=False)

print("% of high-automation-risk employed workers supporting gov retraining:\n")
for _, row in result.iterrows():
    print(f"  {row['country_iso3']:4s} {row['country_name']:25s}  {row['pct_retrain']:.1%}  "
          f"(z_task={row['z_task_profile']:+.2f}, {row['cluster_label']})")

# Also show N per country for the high-risk group
ns = high_risk.groupby("ctrcode").size().rename("n_high_risk")
print("\nSample sizes (unweighted):")
print(ns.to_string())

# Overall share who perceive high risk
print(f"\nShare perceiving high auto risk (q41a>=3) among employed: "
      f"{(valid['q41a'].isin([3,4])).mean():.1%}")
