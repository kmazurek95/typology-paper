"""Build variable_mapping_2022_2024.csv with DV-block rows.

Session 01 of the RTM 2022/2024 harmonization audit.
Wording extracted from the OECD Core Questionnaires (verbatim);
value labels read from the codebook CSVs.
"""

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "processed" / "variable_mapping_2022_2024.csv"

SCALE_22_GEN = (
    "0:|1:Strongly oppose|2:Oppose|3:Neither support nor oppose|"
    "4:Support|5:Strongly support|98:Can't choose"
)
SCALE_22_C = (
    "-77:|1:Strongly oppose|2:Oppose|3:Neither support nor oppose|"
    "4:Support|5:Strongly support|98:Can't choose"
)
SCALE_24 = (
    "1:Strongly oppose|2:Oppose|3:Neither support nor oppose|"
    "4:Support|5:Strongly support|98:Can't choose"
)
RECODE_GEN = "2022 -> NA on {0, 98}; 2024 -> NA on {98}"
RECODE_C77 = "2022 -> NA on {-77, 98}; 2024 -> NA on {98}"

Q42_STEM = (
    "Governments can introduce measures aimed at helping workers and industries "
    "cope with the challenges created by digitalisation and technological change, "
    "such as outdated skills, skills shortages, and possible job loss. Keeping in "
    "mind how much they might cost as well as how you and your family might benefit, "
    "to what extent would you oppose or support the government taking the following "
    "actions as a response to digitalisation and technological change? -- "
)
Q19_STEM = (
    "Would you be willing to pay an additional 2% of your income in taxes/social "
    "contributions to benefit from better provision of and access to: -- "
)

# (analytic_name, var_22, var_24, wording_22, wording_24,
#  vl_22, vl_24, scale_compatible, status, recode_rule, notes)
ROWS = [
    (
        "dv_si_education", "q42a", "q27a",
        Q42_STEM + "Investing more in university education and vocational training "
                   "opportunities for young people",
        Q42_STEM + "Investing more in university education and vocational training "
                   "opportunities for young people",
        SCALE_22_GEN, SCALE_24, True, "clean", RECODE_GEN,
        "PDF stem + item wording identical across waves. 2024 Stata label "
        "abbreviates to 'Invest in education and training' but PDF wording is "
        "verbatim identical.",
    ),
    (
        "dv_si_retraining", "q42b", "q27b",
        Q42_STEM + "Investing more in re-training opportunities for working age people",
        Q42_STEM + "Investing more in re-training opportunities for working-age people",
        SCALE_22_GEN, SCALE_24, True, "clean", RECODE_GEN,
        "Substantively identical; only difference is hyphenation "
        "'working age' -> 'working-age'.",
    ),
    (
        "dv_si_infrastructure", "q42c", "q27c",
        Q42_STEM + "Investing more in digital infrastructure, such as the broadband network",
        Q42_STEM + "Investing more in digital infrastructure, such as the broadband network",
        SCALE_22_C, SCALE_24, True, "clean", RECODE_C77,
        "Item wording identical. 2022 codebook uses -77 (not 0) as the blank "
        "sentinel for this particular item.",
    ),
    (
        "dv_rd_robottax", "q42d", "q27d",
        Q42_STEM + "Introducing (or increasing) a tax on robots and/or technology companies",
        Q42_STEM + "Introducing (or increasing) a tax on robots and/or technology companies",
        SCALE_22_GEN, SCALE_24, True, "clean", RECODE_GEN,
        "PDF item wording identical across waves. 2024 Stata label abbreviates "
        "to 'Introduce tax on robots' but PDF still includes '...and/or "
        "technology companies'.",
    ),
    (
        "dv_rd_benefits", "q42f", "q27f",
        Q42_STEM + "Making public benefits and services, such as unemployment "
                   "benefits, more generous to provide a better safety net for "
                   "workers facing possible job loss.",
        Q42_STEM + "Making public benefits and services, such as unemployment "
                   "benefits or minimum income programmes, more accessible and/or "
                   "more generous to provide a better safety net for workers facing "
                   "possible job loss",
        SCALE_22_GEN, SCALE_24, True, "open", RECODE_GEN,
        "WORDING DIVERGES. 2024 expands the example list ('or minimum income "
        "programmes') and changes the construct from 'more generous' (2022) to "
        "'more accessible and/or more generous' (2024). 2022 measures support "
        "for generosity expansion only; 2024 measures support for accessibility "
        "OR generosity. Conceptually the same DV (expand welfare in response to "
        "digitalisation) but cross-wave equivalence is imperfect. Recommend "
        "keeping in pooled scale but reporting a sensitivity analysis that drops "
        "this item.",
    ),
    (
        "dv_rd_ubi", "q42g", "q27g",
        Q42_STEM + "Introducing a universal basic income that covers essential "
                   "living costs to everyone, regardless of their financial situation.",
        Q42_STEM + "Introducing a universal and unconditional basic income that "
                   "covers essential living costs to everyone, regardless of their "
                   "financial situation",
        SCALE_22_GEN, SCALE_24, True, "clean", RECODE_GEN,
        "2024 inserts 'and unconditional'. Substantively the same construct: "
        "UBI is unconditional by definition; 2024 makes the implicit explicit.",
    ),
    (
        "dv_rd_taxrich_single", "q20", "q20",
        "Should the government tax the rich more than they currently do in "
        "order to support the poor?",
        "Should the government tax the rich more than they currently do in "
        "order to support the poor?",
        "1:Definitely no|2:No|3:Neutral|4:Yes|5:Definitely yes|98:Can't choose",
        "1:Definitely no|2:No|3:Neutral|4:Yes|5:Definitely yes|98:Can't choose",
        True, "clean", "2022 -> NA on {98}; 2024 -> NA on {98}",
        "Identical PDF wording, identical 5-point scale, identical variable name. "
        "Stata labels differ cosmetically ('Income inequality:' vs 'Income tax:'). "
        "Confirms April 8 PDF inspection.",
    ),
    (
        "dv_govrole_secondary", "q17", "q18",
        "Do you think the government should be doing less, about the same, or "
        "more to ensure your economic and social security and well-being?",
        "Do you think the government should be doing less, about the same, or "
        "more to ensure your economic and social security and well-being?",
        "0:|1:Government should be doing much less|2:Government should be doing less|"
        "3:Government should be doing about the same as now|"
        "4:Government should be doing more|5:Government should be doing much more|"
        "98:Can't choose",
        "1:Government should be doing much less|2:Government should be doing less|"
        "3:Government should be doing about the same as now|"
        "4:Government should be doing more|5:Government should be doing much more|"
        "98:Can't choose",
        True, "clean", "2022 -> NA on {0, 98}; 2024 -> NA on {98}",
        "*** Q17 TRAP - 2024 q17 is a DIFFERENT QUESTION (Public benefits: "
        "Others receive without deserving, agree/disagree scale). DO NOT use "
        "2024 q17 for this analytic variable. *** Same gravity as the S23 and "
        "Q14 traps. PDF wording for the SUBSTANTIVE item (2022 q17 / 2024 q18) "
        "is word-for-word identical, including the 5-point response set. "
        "Auxiliary robustness DV per v1 analytic list section 3 - secondary "
        "use only (the main redistribution DV is q20). 2022 codebook stores "
        "the labels as truncated ellipses ('... much less' etc.) but the PDF "
        "wording matches 2024's full labels verbatim.",
    ),
    (
        "dv_si_wtp_education", "q19b", "q19b",
        Q19_STEM + "Education services and supports (e.g. schools, universities, "
                   "adult education services, etc.)",
        Q19_STEM + "Education services and supports (e.g. schools, universities, "
                   "professional/vocational training, adult education services, etc.)",
        "0:Not ticked|1:Ticked", "0:Not ticked|1:Ticked",
        True, "clean",
        "No per-item missing-code recoding required (binary tick-box; "
        "'not willing' captured by q19m, 'don't know' by q19n).",
        "Substantively identical item; 2024 expands the parenthetical example "
        "list to add 'professional/vocational training'. Same variable name and "
        "value labels across waves.",
    ),
    (
        "dv_si_wtp_employment", "q19c", "q19c",
        Q19_STEM + "Employment supports (e.g. job-search supports, skills training "
                   "supports, better access to funds to start a business, etc.)",
        Q19_STEM + "Employment supports (e.g. job-search supports, skills training "
                   "supports, self-employment supports, etc.)",
        "0:Not ticked|1:Ticked", "0:Not ticked|1:Ticked",
        True, "clean", "No per-item missing-code recoding required (binary tick-box).",
        "Item label 'Employment supports' identical; 2024 replaces 'better access "
        "to funds to start a business' with the broader 'self-employment supports' "
        "in the example list. Same variable name across waves.",
    ),
    (
        "dv_rd_wtp_unemployment", "q19d", "q19d",
        Q19_STEM + "Unemployment supports (e.g. unemployment benefits, etc.)",
        Q19_STEM + "Unemployment supports (e.g. unemployment benefits, etc.)",
        "0:Not ticked|1:Ticked", "0:Not ticked|1:Ticked",
        True, "clean", "No per-item missing-code recoding required (binary tick-box).",
        "PDF item wording identical across waves. Same variable name and value labels.",
    ),
    (
        "dv_rd_wtp_income", "q19e", "q19e",
        Q19_STEM + "Income support (e.g. minimum-income benefits)",
        Q19_STEM + "Income supports (e.g. minimum-income benefits, etc.)",
        "0:Not ticked|1:Ticked", "0:Not ticked|1:Ticked",
        True, "clean", "No per-item missing-code recoding required (binary tick-box).",
        "Substantively identical. 2024 pluralises 'Income support' -> 'Income "
        "supports' and adds 'etc.' to the example list. Same variable name across waves.",
    ),
]

HEADER = [
    "analytic_name", "var_2022", "var_2024",
    "wording_2022", "wording_2024",
    "value_labels_2022", "value_labels_2024",
    "scale_compatible", "harmonization_status", "recode_rule",
    "notes", "verified_by_human",
]


INSTRUMENT_TAG = " [instrument: Core]"


def main() -> None:
    assert len(ROWS) == 12, f"expected 12 DV rows (11 from Session 01 + dv_govrole_secondary added in Session 05), got {len(ROWS)}"
    with OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
        w.writerow(HEADER)
        for r in ROWS:
            row = list(r)
            # Append instrument tag to notes (idempotent: only add if missing)
            if "[instrument:" not in row[-1]:
                row[-1] = row[-1].rstrip() + INSTRUMENT_TAG
            w.writerow(row + [False])
    print(f"Wrote {OUT} ({len(ROWS)} rows)")


if __name__ == "__main__":
    main()
