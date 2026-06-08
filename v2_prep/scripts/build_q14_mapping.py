"""Build the 2024 q14 government-interaction battery block.

Session 05 Block B.

*** Q14 TRAP ***
2024 q14a-d = "Government interaction: Digital tools easy / helpful / human / paper".
2022 q14a-e = "Time spent on: filing taxes / applying for benefits / school enrolment...".
Same variable names. Completely different questions. Same gravity as the
S23 trap from Session 02 (Occupation vs Age of youngest child).

This builder maps the 2024 q14a-d items as 2024_only analytic variables. The
2022 q14a-e items are NOT given analytic_name rows because v1 has no
downstream use for them and giving them a name risks accidental future
binding (same rationale as the 2024 s23 case in Session 02).

4 rows. All 2024_only. Notes contain the explicit Q14 TRAP warning.

Source instrument: Core Questionnaire (both q14 batteries are in Core).
"""

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "processed" / "variable_mapping_2022_2024.csv"
INSTRUMENT_TAG = " [instrument: Core]"

AGREE_24 = (
    "1:Strongly disagree|2:Disagree|3:Neither agree nor disagree|"
    "4:Agree|5:Strongly agree|98:Can't choose"
)

STEM_24 = (
    "There are many ways to interact with the government when looking to access "
    "public benefits and services. To what extent do you agree or disagree with "
    "the following statements? -- "
)
RECODE = "2024 -> NA on {98}"

TRAP_NOTE = (
    "*** Q14 TRAP - 2022 q14a-e is a DIFFERENT QUESTION (time spent on filing "
    "taxes, applying for benefits, school enrolment - 7-point hours scale). "
    "DO NOT use 2022 q14 as a match for this 2024 item. *** "
    "Same gravity as the S23 trap from Session 02. Script 04 must match by "
    "analytic_name, not by raw variable name."
)

ROWS = [
    (
        "iv_dig_gov_easy", "", "q14a",
        "", STEM_24 + "Digital tools are easy to use",
        "", AGREE_24,
        True, "2024_only", RECODE,
        TRAP_NOTE + " Item: 'Digital tools are easy to use.'"
    ),
    (
        "iv_dig_gov_helpful", "", "q14b",
        "", STEM_24 + "Government is helpful and responsive",
        "", AGREE_24,
        True, "2024_only", RECODE,
        TRAP_NOTE + " Item: 'Government is helpful and responsive.'"
    ),
    (
        "iv_dig_gov_human", "", "q14c",
        "", STEM_24 + "Easy to talk to a human when I have a question",
        "", AGREE_24,
        True, "2024_only", RECODE,
        TRAP_NOTE + " Item: 'Easy to talk to a human when I have a question.'"
    ),
    (
        "iv_dig_gov_paper", "", "q14d",
        "", STEM_24 + "I prefer paper-based or in-person interactions instead of online",
        "", AGREE_24,
        True, "2024_only", RECODE,
        TRAP_NOTE + " Item: 'I prefer paper-based or in-person interactions "
        "instead of online.' Note: this item has REVERSE polarity vs the "
        "other three (high agreement = LESS comfortable with digital tools); "
        "consider reverse-coding before constructing any composite scale."
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
