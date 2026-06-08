"""Build the worry / risk-perception block of variable_mapping_2022_2024.csv.

Session 04 Block A.

Maps:
- 2022 q2a-j (short-term worries, 10 items) <-> 2024 q2a-j (same wording)
- 2024 q2k, q2l (climate, geopolitical) - 2024-only
- 2022 q3a-j (long-term worries, 10 items) <-> 2024 q3a-j (same wording)
- 2024 q3k, q3l, q3m (climate, geopolitical, population ageing) - 2024-only

25 rows total. One row per sub-item per session brief.

Source instrument: Core Questionnaire (both waves).

Verified against Core Questionnaire PDFs both waves; 2024 simply extends the
batteries with new emergent-risk items. 2022 codebook 'q3c: Own health' is a
Stata-label abbreviation; the PDF wording is 'Becoming ill or disabled' in
both waves, matching the 2024 codebook label.
"""

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "processed" / "variable_mapping_2022_2024.csv"
INSTRUMENT_TAG = " [instrument: Core]"

CONCERN_22_WITH_SENTINELS = (
    "-77:|0:|1:Not at all concerned|2:Not so concerned|"
    "3:Somewhat concerned|4:Very concerned|98:Can't choose / Not applicable"
)
CONCERN_22 = (
    "-77:|1:Not at all concerned|2:Not so concerned|"
    "3:Somewhat concerned|4:Very concerned|98:Can't choose / Not applicable"
)
CONCERN_22_NOSENT = (
    "1:Not at all concerned|2:Not so concerned|"
    "3:Somewhat concerned|4:Very concerned|98:Can't choose / Not applicable"
)
CONCERN_24 = (
    "1:Not at all concerned|2:Not so concerned|"
    "3:Somewhat concerned|4:Very concerned|98:Can't choose / Not applicable"
)

STEM_22_Q2 = (
    "Thinking about the next year or two, how concerned are you about each of "
    "the following? -- "
)
STEM_24_Q2 = STEM_22_Q2  # word-for-word identical in 2024 Core PDF
STEM_22_Q3 = (
    "Looking beyond the next ten years, how concerned are you about the following? -- "
)
STEM_24_Q3 = STEM_22_Q3  # word-for-word identical

RECODE_BOTH = "2022 -> NA on {-77, 0, 98}; 2024 -> NA on {98}"
RECODE_ONESIDED = "2024 -> NA on {98}"

# Per-item value-label strings for 2022 (some items have -77 only, some have -77+0)
VL22 = {
    "q2a": CONCERN_22, "q2b": CONCERN_22, "q2c": CONCERN_22,
    "q2d": CONCERN_22_WITH_SENTINELS,
    "q2e": CONCERN_22_NOSENT, "q2f": CONCERN_22, "q2g": CONCERN_22,
    "q2h": CONCERN_22, "q2i": CONCERN_22_NOSENT, "q2j": CONCERN_22_NOSENT,
    "q3a": "0:|" + CONCERN_22_NOSENT,
    "q3b": CONCERN_22_NOSENT, "q3c": CONCERN_22_NOSENT,
    "q3d": CONCERN_22_NOSENT, "q3e": CONCERN_22_NOSENT,
    "q3f": "0:|" + CONCERN_22_NOSENT,
    "q3g": CONCERN_22_NOSENT, "q3h": CONCERN_22_NOSENT,
    "q3i": CONCERN_22_NOSENT, "q3j": CONCERN_22_NOSENT,
}

# (analytic, 2022_var, 2024_var, item_text, status, recode, extra_note)
# item_text is appended to the stem to form full wording
Q2_ITEMS = [
    ("iv_worry_st_illness",    "q2a", "q2a", "Becoming ill or disabled", "clean", RECODE_BOTH, ""),
    ("iv_worry_st_jobloss",    "q2b", "q2b", "Losing a job or self-employment income", "clean", RECODE_BOTH, "Key candidate covariate for individual economic insecurity per v1 analytic list."),
    ("iv_worry_st_housing",    "q2c", "q2c", "Not being able to find/maintain adequate housing", "clean", RECODE_BOTH, ""),
    ("iv_worry_st_expenses",   "q2d", "q2d", "Not being able to pay all expenses and make ends meet", "clean", RECODE_BOTH, ""),
    ("iv_worry_st_childcare",  "q2e", "q2e", "Not being able to access good-quality child care or education for your children (or young members of your family)", "clean", RECODE_BOTH, ""),
    ("iv_worry_st_ltc_elder",  "q2f", "q2f", "Not being able to access good-quality long-term care for elderly family members", "clean", RECODE_BOTH, ""),
    ("iv_worry_st_ltc_young",  "q2g", "q2g", "Not being able to access good-quality long-term care for young or working-age family members with an illness or disability", "clean", RECODE_BOTH, ""),
    ("iv_worry_st_crime",      "q2h", "q2h", "Being the victim of crime or violence", "clean", RECODE_BOTH, ""),
    ("iv_worry_st_giveup_job", "q2i", "q2i", "Having to give up my job to care for children, elderly relatives, or relatives with illness or disability", "clean", RECODE_BOTH, ""),
    ("iv_worry_st_healthcare", "q2j", "q2j", "Accessing good-quality healthcare", "clean", RECODE_BOTH, ""),
    # 2024-only:
    ("iv_worry_st_climate",    "",   "q2k", "Climate change", "2024_only", RECODE_ONESIDED, "New 2024 item; no 2022 analogue in this battery."),
    ("iv_worry_st_geopol",     "",   "q2l", "Geopolitical risks (e.g. war or terrorism)", "2024_only", RECODE_ONESIDED, "New 2024 item; no 2022 analogue in this battery."),
]

Q3_ITEMS = [
    ("iv_worry_lt_finances",       "q3a", "q3a", "Not being as well-off and financially secure as your parents and/or that you had hoped to be", "clean", RECODE_BOTH, ""),
    ("iv_worry_lt_children_fin",   "q3b", "q3b", "Your children (or young members of your family) not being as well-off and financially secure as you are", "clean", RECODE_BOTH, ""),
    ("iv_worry_lt_illness",        "q3c", "q3c", "Becoming ill or disabled", "clean", RECODE_BOTH, "2022 Stata label says 'Own health' but PDF wording matches 2024: 'Becoming ill or disabled'. Verified by Core PDF Q3 item c in both waves."),
    ("iv_worry_lt_skills",         "q3d", "q3d", "Not having the right skills and knowledge to work in a secure and well-paid job", "clean", RECODE_BOTH, ""),
    ("iv_worry_lt_oldage",         "q3e", "q3e", "Not being financially secure in old age", "clean", RECODE_BOTH, ""),
    ("iv_worry_lt_housing",        "q3f", "q3f", "Not being able to find/maintain adequate housing", "clean", RECODE_BOTH, ""),
    ("iv_worry_lt_ltc_self",       "q3g", "q3g", "Not being able to access good-quality long-term care for yourself", "clean", RECODE_BOTH, ""),
    ("iv_worry_lt_ltc_elder",      "q3h", "q3h", "Not being able to access good-quality long-term care for elderly family members", "clean", RECODE_BOTH, ""),
    ("iv_worry_lt_ltc_young",      "q3i", "q3i", "Not being able to access good-quality long-term care for young or working-age family members with an illness or disability", "clean", RECODE_BOTH, ""),
    ("iv_worry_lt_healthcare",     "q3j", "q3j", "Accessing good-quality healthcare", "clean", RECODE_BOTH, ""),
    # 2024-only:
    ("iv_worry_lt_climate",        "",   "q3k", "Climate change", "2024_only", RECODE_ONESIDED, "New 2024 item."),
    ("iv_worry_lt_geopol",         "",   "q3l", "Geopolitical risks (e.g. war or terrorism)", "2024_only", RECODE_ONESIDED, "New 2024 item."),
    ("iv_worry_lt_pop_ageing",     "",   "q3m", "Population ageing", "2024_only", RECODE_ONESIDED, "New 2024 item."),
]


def build_rows():
    rows = []
    for items, stem_22, stem_24, name_prefix in [
        (Q2_ITEMS, STEM_22_Q2, STEM_24_Q2, "q2"),
        (Q3_ITEMS, STEM_22_Q3, STEM_24_Q3, "q3"),
    ]:
        for analytic, v22, v24, item_text, status, recode, extra in items:
            wording_22 = (stem_22 + item_text) if v22 else ""
            wording_24 = (stem_24 + item_text) if v24 else ""
            vl_22 = VL22.get(v22, "") if v22 else ""
            vl_24 = CONCERN_24 if v24 else ""
            notes = (
                f"Wording verified verbatim against 2022 + 2024 Core Questionnaire "
                f"PDFs (Q{name_prefix[1]} item {(v24 or v22)[-1]})."
            )
            if extra:
                notes = extra + " " + notes
            rows.append((
                analytic, v22, v24, wording_22, wording_24, vl_22, vl_24,
                True, status, recode, notes
            ))
    return rows


HEADER = [
    "analytic_name", "var_2022", "var_2024",
    "wording_2022", "wording_2024",
    "value_labels_2022", "value_labels_2024",
    "scale_compatible", "harmonization_status", "recode_rule",
    "notes", "verified_by_human",
]


def main() -> None:
    rows = build_rows()
    assert len(rows) == 25, f"expected 25 worry rows, got {len(rows)}"

    existing = []
    if OUT.exists():
        with OUT.open("r", encoding="utf-8", newline="") as f:
            existing = list(csv.DictReader(f))

    new_dicts = []
    for r in rows:
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
