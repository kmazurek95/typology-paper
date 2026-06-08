"""Build the financial-trouble battery block.

Session 05 Block C.

Maps 2022 q6a-e <-> 2024 q4a-e. Renumbered Core battery. Skeleton CSV
fuzzy-matched these at sim=1.0; PDF spot-check confirms substantively
identical items with one nuance: 2024 wave expanded items (a) and (e) to
include "You and/or" language (the 2022 wording assumed the respondent
themselves wouldn't be the worker / loan-taker; 2024 includes the respondent
as a possible actor).

5 rows. Mix of clean and needs_recode.

Source instrument: Core Questionnaire (both waves).
"""

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "processed" / "variable_mapping_2022_2024.csv"
INSTRUMENT_TAG = " [instrument: Core]"

CONFIDENT_22 = (
    "-77:|1:Not at all confident|2:Not so confident|3:Somewhat confident|"
    "4:Very confident|98:Can't choose"
)
CONFIDENT_22_NOSENT = (
    "1:Not at all confident|2:Not so confident|3:Somewhat confident|"
    "4:Very confident|98:Can't choose"
)
CONFIDENT_22_WITH_ZERO = (
    "0:|1:Not at all confident|2:Not so confident|3:Somewhat confident|"
    "4:Very confident|98:Can't choose"
)
CONFIDENT_24 = (
    "1:Not at all confident|2:Not so confident|3:Somewhat confident|"
    "4:Very confident|98:Can't choose"
)

STEM = (
    "If you and your household were to experience financial trouble (such as "
    "not enough income or savings to pay the bills), how confident are you that: -- "
)
RECODE_22_24 = "2022 -> NA on {-77, 0, 98}; 2024 -> NA on {98}"

# Wording differences per PDF spot-check
W_22_A = "Another adult in your household could work more to bring in more money"
W_24_A = "You and/or another adult in your household could work more to bring in more money"
W_22_B = "A friend or family member would be able and willing to help out"
W_24_B = W_22_B
W_22_C = "Cash benefits and services provided by government would sufficiently support you through the financial difficulties"
W_24_C = "Cash benefits and services provided by government would sufficiently support you through financial difficulties"
W_22_D = "Cash benefits and services provided by charity or non-profit institutions would sufficiently support you through the financial difficulties"
W_24_D = "Cash benefits and services provided by charity or non-profit institutions would sufficiently support you through financial difficulties"
W_22_E = "You would apply for a loan or take on (more) debt from a bank or financial institution"
W_24_E = "You and/or another adult in your household would apply for a loan or take on (more) debt from a bank or financial institution"

ROWS = [
    (
        "iv_fin_trouble_hh_work",
        "q6a", "q4a",
        STEM + W_22_A, STEM + W_24_A, CONFIDENT_22, CONFIDENT_24,
        True, "needs_recode", RECODE_22_24,
        "Substantively similar but 2024 EXPANDED the subject scope: 2022 asks "
        "about 'another adult' (excludes respondent); 2024 asks about 'You "
        "and/or another adult' (includes respondent). A respondent confident in "
        "their OWN ability to work more would answer differently across waves. "
        "Recommend reporting both pooled and 2024-only as sensitivity. Name "
        "match (q6a vs q4a) would FAIL anyway - this is the q6/q4 Core-battery "
        "renumbering pattern. Verified by Core PDF Q6/Q4 both waves."
    ),
    (
        "iv_fin_trouble_family", "q6b", "q4b",
        STEM + W_22_B, STEM + W_24_B, CONFIDENT_22_NOSENT, CONFIDENT_24,
        True, "clean", RECODE_22_24,
        "PDF wording identical across waves. Q6 -> Q4 Core-battery renumbering."
    ),
    (
        "iv_fin_trouble_gov", "q6c", "q4c",
        STEM + W_22_C, STEM + W_24_C, CONFIDENT_22_WITH_ZERO, CONFIDENT_24,
        True, "clean", RECODE_22_24,
        "Substantively identical; the only difference between waves is the "
        "definite article 'the' before 'financial difficulties' (present in "
        "2022, absent in 2024). Cosmetic."
    ),
    (
        "iv_fin_trouble_charity", "q6d", "q4d",
        STEM + W_22_D, STEM + W_24_D, CONFIDENT_22_NOSENT, CONFIDENT_24,
        True, "clean", RECODE_22_24,
        "Substantively identical; same 'the' difference as q6c/q4c. Cosmetic."
    ),
    (
        "iv_fin_trouble_loan",
        "q6e", "q4e",
        STEM + W_22_E, STEM + W_24_E, CONFIDENT_22_NOSENT, CONFIDENT_24,
        True, "needs_recode", RECODE_22_24,
        "Same scope-expansion issue as item a: 2022 asks 'You would apply for "
        "a loan'; 2024 asks 'You and/or another adult in your household would "
        "apply for a loan'. 2024 broadens to include other household members. "
        "Respondents in single-earner households are unaffected; respondents "
        "in multi-earner households may shift answers slightly. Recommend "
        "the same pooled / 2024-only sensitivity reporting as item a."
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
