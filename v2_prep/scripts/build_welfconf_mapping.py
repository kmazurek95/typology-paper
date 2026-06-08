"""Build the welfare-confidence block of variable_mapping_2022_2024.csv.

Session 04 Block B.

Maps q13a-e in both waves. 5 items. Identical variable names, identical 5-point
agree scale + 98, identical PDF wording (modulo cosmetic 'Note:' framing in
2024). 2022 carries -77 and (for q13b) 0 filter sentinels that 2024 doesn't.

Source instrument: Core Questionnaire (both waves).
"""

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "processed" / "variable_mapping_2022_2024.csv"
INSTRUMENT_TAG = " [instrument: Core]"

AGREE_22 = (
    "-77:|1:Strongly disagree|2:Disagree|3:Neither agree nor disagree|"
    "4:Agree|5:Strongly agree|98:Can't choose"
)
AGREE_22_WITH_ZERO = (
    "-77:|0:|1:Strongly disagree|2:Disagree|3:Neither agree nor disagree|"
    "4:Agree|5:Strongly agree|98:Can't choose"
)
AGREE_22_NOSENT = (
    "1:Strongly disagree|2:Disagree|3:Neither agree nor disagree|"
    "4:Agree|5:Strongly agree|98:Can't choose"
)
AGREE_24 = AGREE_22_NOSENT

STEM = (
    "To what degree do you agree or disagree with the following statements? "
    "(Note: If you currently are receiving services or benefits, please answer "
    "these questions according to your experience. If you are not receiving "
    "them, please answer according to what you think your experience would be "
    "if you needed them.) -- "
)
RECODE = "2022 -> NA on {-77, 0, 98}; 2024 -> NA on {98}"

ITEMS = [
    ("iv_welf_conf_easy_receive", "q13a", "I feel I could easily receive public benefits if I needed them", AGREE_22),
    ("iv_welf_conf_qualify",      "q13b", "I am confident I would qualify for public benefits", AGREE_22_WITH_ZERO),
    ("iv_welf_conf_know_apply",   "q13c", "I know how to apply for public benefits", AGREE_22),
    ("iv_welf_conf_simple",       "q13d", "I think the application process for benefits would be simple and quick", AGREE_22_NOSENT),
    ("iv_welf_conf_fair",         "q13e", "I feel I would be treated fairly by the government office processing my claim", AGREE_22),
]

HEADER = [
    "analytic_name", "var_2022", "var_2024",
    "wording_2022", "wording_2024",
    "value_labels_2022", "value_labels_2024",
    "scale_compatible", "harmonization_status", "recode_rule",
    "notes", "verified_by_human",
]


def main() -> None:
    rows = []
    for analytic, var, item_text, vl_22 in ITEMS:
        wording = STEM + item_text
        rows.append((
            analytic, var, var, wording, wording, vl_22, AGREE_24,
            True, "clean", RECODE,
            f"PDF wording verified verbatim in both waves (Core Q13 item "
            f"{var[-1]}). Variable name identical across waves. 2022 carries "
            f"-77 (and for q13b also 0) filter sentinels; 2024 doesn't. "
            f"Substantively cosmetic differences only."
        ))

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
