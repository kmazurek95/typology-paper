"""End-to-end pipeline validation: Scripts 03b, 03c, 04, 05.

One-off validation; not part of the production pipeline. Writes results to
v2_prep/data/processed/_pipeline_validation_2026-05-26.json for the markdown
report to consume.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[2]
PROC = ROOT / "data" / "processed"
V2 = ROOT / "v2_prep" / "data" / "processed"

results = {"file_checks": {}, "cross_script": {}, "warnings": []}


def check(label, cond, detail=""):
    status = "PASS" if cond else "FAIL"
    print(f"  [{status}] {label}" + (f" — {detail}" if detail else ""))
    return cond


def record(key, label, cond, detail=""):
    results["file_checks"].setdefault(key, []).append({
        "label": label, "pass": bool(cond), "detail": detail,
    })
    return check(label, cond, detail)


# ── Per-file checks ──────────────────────────────────────────────────────

print("=" * 70)
print("1. typology_positions.csv")
print("=" * 70)
p = PROC / "typology_positions.csv"
record("typology_positions", "file exists", p.exists())
tp = pd.read_csv(p)
record("typology_positions", "29 rows", len(tp) == 29, f"got {len(tp)}")
expected_cols = {"country_iso3", "task_profile_pc1", "cluster", "cluster_label"}
present = expected_cols & set(tp.columns)
missing = expected_cols - set(tp.columns)
record("typology_positions", "core columns present", not missing,
       f"present={sorted(present)}, missing={sorted(missing)}")
epl_candidates = [c for c in tp.columns if "epl" in c.lower() or "gap" in c.lower()]
record("typology_positions", "EPL gap column present", bool(epl_candidates),
       f"candidates={epl_candidates}")
record("typology_positions", "no NaN in task_profile_pc1",
       tp["task_profile_pc1"].notna().all(),
       f"NaN count: {tp['task_profile_pc1'].isna().sum()}")

print()
print("=" * 70)
print("2. pca_aioe_validation.csv")
print("=" * 70)
p = PROC / "pca_aioe_validation.csv"
record("pca_aioe_validation", "file exists", p.exists())
pv = pd.read_csv(p)
record("pca_aioe_validation", "21 rows (European subset)", len(pv) == 21,
       f"got {len(pv)}")
r, pval = stats.pearsonr(pv["task_profile_pc1"], pv["mean_aioe"])
record("pca_aioe_validation", "Pearson r = 0.7087 to 4dp",
       abs(r - 0.7087) < 5e-5, f"computed r = {r:.6f}, p = {pval:.6e}")

print()
print("=" * 70)
print("3. aioe_loo_jackknife.csv")
print("=" * 70)
p = PROC / "aioe_loo_jackknife.csv"
record("aioe_loo_jackknife", "file exists", p.exists())
loo = pd.read_csv(p)
record("aioe_loo_jackknife", "21 rows", len(loo) == 21, f"got {len(loo)}")
top = loo.iloc[0]
bot = loo.iloc[-1]
record("aioe_loo_jackknife", "ESP top with r=0.7712",
       top["dropped_country"] == "ESP" and abs(top["r_pearson"] - 0.7712) < 5e-5,
       f"top: {top['dropped_country']} r={top['r_pearson']:.4f}")
record("aioe_loo_jackknife", "HUN bottom with r=0.6684",
       bot["dropped_country"] == "HUN" and abs(bot["r_pearson"] - 0.6684) < 5e-5,
       f"bot: {bot['dropped_country']} r={bot['r_pearson']:.4f}")

print()
print("=" * 70)
print("4. rtm_pooled_analytic.parquet")
print("=" * 70)
p = V2 / "rtm_pooled_analytic.parquet"
record("rtm_pooled", "file exists", p.exists())
rtm = pd.read_parquet(p)
record("rtm_pooled", "54,698 rows by 100 cols", rtm.shape == (54698, 100),
       f"got {rtm.shape}")
record("rtm_pooled", "iv_nace_sector column present",
       "iv_nace_sector" in rtm.columns)
nace_nn = rtm["iv_nace_sector"].notna().sum()
nace_pct = nace_nn / len(rtm) * 100
record("rtm_pooled", "iv_nace_sector non-null > 95%",
       nace_pct > 95, f"{nace_pct:.2f}% non-null ({nace_nn:,}/{len(rtm):,})")

print()
print("=" * 70)
print("5. nace_aiie_lookup.csv (post-O-patch)")
print("=" * 70)
p = V2 / "nace_aiie_lookup.csv"
record("nace_aiie", "file exists", p.exists())
aiie = pd.read_csv(p)
record("nace_aiie", "21 rows", len(aiie) == 21, f"got {len(aiie)}")
o_row = aiie[aiie["nace_letter"] == "O"].iloc[0]
record("nace_aiie", "section O AIIE non-null",
       not pd.isna(o_row["aiie_score"]),
       f"O AIIE = {o_row['aiie_score']:.4f}")
nan_secs = set(aiie[aiie["aiie_score"].isna()]["nace_letter"])
expected_nan = {"L", "T", "U"}
record("nace_aiie", "L, T, U still NaN (expected)", nan_secs == expected_nan,
       f"NaN sections: {sorted(nan_secs)}")

# ── Cross-script consistency ─────────────────────────────────────────────

print()
print("=" * 70)
print("CROSS-SCRIPT CONSISTENCY")
print("=" * 70)

print("\n1. RTM countries vs typology_positions countries")
rtm_countries = set(rtm["ctrcode"].dropna().unique())
tp_countries = set(tp["country_iso3"].dropna().unique())
matched = rtm_countries & tp_countries
in_rtm_only = rtm_countries - tp_countries
in_tp_only = tp_countries - rtm_countries
print(f"  RTM unique countries: {len(rtm_countries)}")
print(f"  typology_positions unique countries: {len(tp_countries)}")
print(f"  Matched: {len(matched)}")
print(f"  In RTM only (not in typology_positions): {sorted(in_rtm_only)}")
print(f"  In typology_positions only (not in RTM): {sorted(in_tp_only)}")
results["cross_script"]["country_match"] = {
    "rtm_n": len(rtm_countries), "tp_n": len(tp_countries),
    "matched": len(matched),
    "rtm_only": sorted(in_rtm_only),
    "tp_only": sorted(in_tp_only),
}

print("\n2. RTM NACE sectors (codes 1-19) vs nace_aiie_lookup")
rtm_nace_codes = sorted(rtm["iv_nace_sector"].dropna().unique().astype(int).tolist())
rtm_to_letter = {i: l for i, l in enumerate("ABCDEFGHIJKLMNOPQRS", start=1)}
print(f"  RTM iv_nace_sector unique codes: {rtm_nace_codes}")
substantive_codes = [c for c in rtm_nace_codes if 1 <= c <= 19]
residual_codes = [c for c in rtm_nace_codes if c not in substantive_codes]
print(f"  Substantive (1-19): {substantive_codes}")
print(f"  Residual (97/99): {residual_codes}")
aiie_by_letter = dict(zip(aiie["nace_letter"], aiie["aiie_score"]))
missing_aiie = []
for c in substantive_codes:
    letter = rtm_to_letter.get(c)
    aiie_v = aiie_by_letter.get(letter)
    if aiie_v is None or pd.isna(aiie_v):
        n_rtm = int((rtm["iv_nace_sector"] == c).sum())
        missing_aiie.append((c, letter, n_rtm))
print(f"  RTM substantive codes that land on NaN AIIE in Script 06 join: {len(missing_aiie)}")
for c, l, n in missing_aiie:
    print(f"    code {c} -> letter {l}: {n:,} RTM rows")
# Residual codes (97/99) also land on NaN by design
residual_rtm_rows = int(rtm["iv_nace_sector"].isin(residual_codes).sum())
print(f"  Residual codes (97/99) contribute additional {residual_rtm_rows:,} RTM rows with NaN AIIE")
results["cross_script"]["nace_match"] = {
    "rtm_substantive_codes": substantive_codes,
    "rtm_residual_codes": residual_codes,
    "missing_aiie_substantive": [
        {"code": c, "letter": l, "rtm_rows": n} for c, l, n in missing_aiie
    ],
    "residual_rtm_rows_total": residual_rtm_rows,
}

print("\n3. RTM wave coverage")
wave_counts = rtm["wave"].value_counts().to_dict()
print(f"  Wave counts: {wave_counts}")
results["cross_script"]["wave_counts"] = {str(k): int(v) for k, v in wave_counts.items()}
expected_2022, expected_2024 = 27469, 27229
record("rtm_pooled", "2022 wave = 27,469 rows",
       wave_counts.get("2022") == expected_2022,
       f"got {wave_counts.get('2022')}")
record("rtm_pooled", "2024 wave = 27,229 rows",
       wave_counts.get("2024") == expected_2024,
       f"got {wave_counts.get('2024')}")

print("\n4. Substantive sanity: section O rank check (scale compatibility)")
valid = aiie.dropna(subset=["aiie_score"]).sort_values(
    "aiie_score", ascending=False
).reset_index(drop=True)
o_rank = int((valid["nace_letter"] == "O").idxmax()) + 1
n_valid = len(valid)
print(f"  O ranks #{o_rank} of {n_valid} valid sections by AIIE")
print(f"  O AIIE = {aiie_by_letter['O']:+.4f}")
in_top3 = o_rank <= 3
in_bot3 = o_rank > n_valid - 3
record("nace_aiie", "O NOT in top-3 / bottom-3 (scale check)",
       not (in_top3 or in_bot3), f"O rank={o_rank} of {n_valid}")
results["cross_script"]["o_rank"] = {
    "rank": o_rank, "n_valid": n_valid,
    "aiie": float(aiie_by_letter["O"]),
}

print("\n5. NaN propagation (>5% NaN in unexpected columns)")
unexpected_nan = []
for c in ["country_iso3", "task_profile_pc1", "cluster", "cluster_label"]:
    if c in tp.columns:
        nan_pct = tp[c].isna().mean() * 100
        if nan_pct > 5:
            unexpected_nan.append(("typology_positions", c, nan_pct))
for c in ["id", "ctrcode", "ctryear", "year", "weight", "wave"]:
    if c in rtm.columns:
        nan_pct = rtm[c].isna().mean() * 100
        if nan_pct > 5:
            unexpected_nan.append(("rtm_pooled", c, nan_pct))
print(f"  Columns with unexpected >5% NaN: {len(unexpected_nan)}")
for f, c, pct in unexpected_nan:
    print(f"    {f}.{c}: {pct:.1f}% NaN")
record("nan_propagation",
       "no unexpected > 5% NaN in admin/structural cols",
       not unexpected_nan, str(unexpected_nan))

with open(V2 / "_pipeline_validation_2026-05-26.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, default=str)
print(f"\nResults saved to {V2 / '_pipeline_validation_2026-05-26.json'}")
