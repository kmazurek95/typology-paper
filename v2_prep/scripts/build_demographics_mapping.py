"""Build the demographics block of variable_mapping_2022_2024.csv.

Session 05 Block A.

Maps:
- dem_sex (s2 / s2)
- dem_age (s3_age, 2022_only - 2024 dropped continuous age)
- dem_agegroup (s3_agegroup / s3_agegroup)
- dem_hh_size (s5 -> s6, shifted by s5 insertion)
- dem_n_children_hh (s19 -> s22, shifted)
- dem_age_youngest_child (s20 -> s23, shifted)
- dem_education_3cat (s6_cat3 -> s7_cat3, shifted)
- dem_income_decile (s8_dec -> s9_dec, shifted)

8 rows. Most require explicit s5-shift annotation in notes.

Source instrument: Background Questionnaire (all are s-prefixed).
"""

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "processed" / "variable_mapping_2022_2024.csv"
INSTRUMENT_TAG = " [instrument: Background]"

SHIFT_NOTE = "Name match would be INCORRECT - shifted by s5 insertion (the 'Born in country' item added in 2024). Verified by wording."

# Value-label shorthands
SEX_22 = "1:Male|2:Female|99:Other / Prefer not to answer"
SEX_24 = "1:Man|2:Woman|99:Other/Prefer not to say"

AGEGROUP = "1:18-24|2:25-34|3:35-44|4:45-54|5:55-64"

EDU_3CAT_22 = (
    "1:Below upper secondary education|"
    "2:Upper secondary education or post-secondary non-tertiary|"
    "3:Tertiary education"
)
EDU_3CAT_24 = "1:Low|2:Medium|3:High"

DECILE_22 = (
    "1:First decile|2:Second decile|3:Third decile|4:Fourth decile|5:Fifth decile|"
    "6:Sixth decile|7:Seventh decile|8:Eight decile|9:Ninth decile|10:Tenth decile"
)
DECILE_24 = (
    "1:First decile|2:Second decile|3:Third decile|4:Fourth decile|5:Fifth decile|"
    "6:Sixth decile|7:Seventh decile|8:Eighth decile|9:Ninth decile|10:Tenth decile"
)

# Wording (from BG Q-numbered items where available)
W_SEX = "What is your sex/gender?"
W_AGE_CONT = (
    "(Derived from year-of-birth item in 2022 Background Questionnaire; "
    "continuous integer age in years.)"
)
W_AGEGROUP = (
    "(Derived 5-category age group: 18-24 / 25-34 / 35-44 / 45-54 / 55-64.)"
)
W_HH_SIZE = "How many people in total live in your household, including yourself?"
W_N_CHILDREN_HH = (
    "Open numeric: number of children under 18 currently living in the household."
)
W_AGE_YOUNGEST_22 = "Age of youngest child in household."
W_AGE_YOUNGEST_24 = "Age of youngest child (under 18) in household."
W_EDU = (
    "What is the highest level of education you have completed? "
    "(Derived 3-category collapse: low / medium / high.)"
)
W_INCOME_22 = (
    "(Derived equivalised disposable household income decile, reference year 2021. "
    "Wave-relative within-country deciles based on the self-reported income items.)"
)
W_INCOME_24 = (
    "(Derived equivalised disposable household income decile, reference year 2023. "
    "Wave-relative within-country deciles based on the self-reported income items.)"
)

# Recode rules
R_NONE = "No recoding required."
R_AGE_NUMERIC = "Numeric integer; range observed 18-64. No sentinel values to recode."
R_CHILDREN_22 = (
    "2022: numeric. Codebook value-label map includes sentinel codes -99 (refusal) "
    "and -66 (filter); recode to NA. 2024: numeric, no sentinels."
)
R_NONE_BOTH = "No recoding required (both waves numeric/integer)."

ROWS = [
    (
        "dem_sex", "s2", "s2",
        W_SEX, W_SEX, SEX_22, SEX_24,
        True, "clean", R_NONE,
        "Cosmetic label change only: 'Male'/'Female' (2022) -> 'Man'/'Woman' "
        "(2024); same codes 1/2/99. The s2 variable name is identical across "
        "waves (one of the few s-prefix items NOT shifted by the s5 insertion - "
        "s5 was inserted after s4)."
    ),
    (
        "dem_age", "s3_age", "",
        W_AGE_CONT, "", "(numeric, codes 18-64; no sentinels)", "",
        False, "2022_only", R_AGE_NUMERIC,
        "*** 2024 DROPPED the continuous age variable. *** Only s3_agegroup is "
        "published in 2024 (see dem_agegroup). For any pooled spec needing "
        "continuous age, must (a) use the 5-category s3_agegroup midpoints, "
        "(b) restrict to 2022-only, or (c) request raw year-of-birth from OECD. "
        "v1 analytic list flagged this as unknown for 2024; audit confirms it's "
        "absent."
    ),
    (
        "dem_agegroup", "s3_agegroup", "s3_agegroup",
        W_AGEGROUP, W_AGEGROUP, AGEGROUP, AGEGROUP,
        True, "clean", R_NONE,
        "Identical 5-category construction in both waves: codes 1-5, same "
        "boundaries (18-24 / 25-34 / 35-44 / 45-54 / 55-64). RTM samples "
        "18-64 inclusive in both waves."
    ),
    (
        "dem_hh_size", "s5", "s6",
        W_HH_SIZE, W_HH_SIZE,
        "(numeric, no value labels)", "(numeric, no value labels)",
        True, "clean", R_NONE_BOTH,
        SHIFT_NOTE + " 2024 s5 is 'Born in country' (the new inserted item), "
        "NOT household size."
    ),
    (
        "dem_n_children_hh", "s19", "s22",
        W_N_CHILDREN_HH, W_N_CHILDREN_HH,
        "(numeric; codebook value-label set includes sentinel codes -99 and -66 plus integers 0-12)",
        "(numeric, no value labels)",
        True, "needs_recode", R_CHILDREN_22,
        SHIFT_NOTE + " 2024 s19 is 'Number of children (under 18)' WITHOUT "
        "'in household' (likely a respondent's total children regardless of "
        "co-residence); s22 is the 'in household' analogue. Mapping 2022 s19 "
        "to 2024 s22 preserves 'in household' semantics. The 2024 s19 (total "
        "children) is a separate variable not currently mapped (no 2022 "
        "analogue; not on the v1 analytic list)."
    ),
    (
        "dem_age_youngest_child", "s20", "s23",
        W_AGE_YOUNGEST_22, W_AGE_YOUNGEST_24,
        "(numeric, no value labels)", "(numeric, no value labels)",
        True, "clean", R_NONE_BOTH,
        SHIFT_NOTE + " 2024 s23 here is 'Age of youngest child (under 18) in "
        "household' - the SAME variable name as 2022 s23 (Occupation), which "
        "is the S23 TRAP documented in Session 02 for the iv_occupation_isco1 "
        "row. Here the analytic_name (dem_age_youngest_child) is what governs; "
        "the trap concerns analytic_name = iv_occupation_isco1, NOT this row. "
        "Both rows are correct as long as Script 04 matches by analytic_name, "
        "not by raw variable name."
    ),
    (
        "dem_education_3cat", "s6_cat3", "s7_cat3",
        W_EDU, W_EDU, EDU_3CAT_22, EDU_3CAT_24,
        True, "clean", R_NONE,
        SHIFT_NOTE + " Same 3-category derivation logic in both waves (OECD "
        "convention). Codes 1/2/3 identical. Value-label text differs: 2022 "
        "uses explicit ISCED-style category names ('Below upper secondary / "
        "Upper secondary or post-secondary non-tertiary / Tertiary'); 2024 "
        "abbreviates to 'Low / Medium / High'. The underlying construct is "
        "the same. 2022 ALSO publishes the 7-level continuous version (s6) "
        "and a 2-category version (s6_cat2); 2024 publishes only the 3-cat "
        "version, so only the 3-cat is pool-feasible."
    ),
    (
        "dem_income_decile", "s8_dec", "s9_dec",
        W_INCOME_22, W_INCOME_24, DECILE_22, DECILE_24,
        True, "clean", R_NONE_BOTH,
        SHIFT_NOTE + " Within-country, wave-relative income deciles. "
        "Reference income year: 2021 (2022 wave), 2023 (2024 wave) - wave-1 "
        "in each case. Because deciles are wave-relative, pooling is valid "
        "for relative-position covariates (e.g., 'bottom-quintile') but NOT "
        "for absolute-income comparisons across waves. Cosmetic typo in 2022 "
        "label: 'Eight decile' -> 2024 'Eighth decile' (same code 8 both "
        "waves). v1 analytic list flagged this caveat explicitly."
    ),
]

HEADER = [
    "analytic_name", "var_2022", "var_2024",
    "wording_2022", "wording_2024",
    "value_labels_2022", "value_labels_2024",
    "scale_compatible", "harmonization_status", "recode_rule",
    "notes", "verified_by_human",
]


def main() -> None:
    existing = []
    if OUT.exists():
        with OUT.open("r", encoding="utf-8", newline="") as f:
            existing = list(csv.DictReader(f))

    new_dicts = []
    for r in ROWS:
        d = dict(zip(HEADER[:-1], r))
        if "[instrument:" not in d["notes"]:
            d["notes"] = d["notes"].rstrip() + INSTRUMENT_TAG
        d["verified_by_human"] = "False"
        new_dicts.append(d)

    new_names = {d["analytic_name"] for d in new_dicts}
    kept = [row for row in existing if row.get("analytic_name") not in new_names]
    combined = kept + new_dicts

    with OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=HEADER, quoting=csv.QUOTE_MINIMAL)
        w.writeheader()
        w.writerows(combined)

    print(
        f"Wrote {OUT} ({len(combined)} rows total: "
        f"{len(kept)} preserved + {len(new_dicts)} new)"
    )


if __name__ == "__main__":
    main()
