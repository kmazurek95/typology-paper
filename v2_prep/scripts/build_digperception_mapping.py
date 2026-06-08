"""Build the digitalization-perception block of variable_mapping_2022_2024.csv.

Session 04 Block C - the judgment-call block.

The 2024 wave introduced two new attitudinal batteries (q24 government AI use;
q26 AI labour-market perceptions) and substantially expanded the 2022 q41
'digitalisation and your job' battery into 2024 q25. Comparison findings:

- q24a-c (gov digital AI trust): NEW in 2024. No 2022 analogue. -> 2024_only.
- q25a (replaced by robot) and q25c (replaced by AI/ChatGPT): 2024 SPLIT a
  single 2022 omnibus item (q41a: 'replaced by a robot, computer software, an
  algorithm, or artificial intelligence') into two separate items. The 2022
  item conflates {robot, computer, algorithm, AI}; the 2024 items separate
  them. A respondent's 'likely' answer to 2022 q41a cannot be cleanly assigned
  to either 2024 component. -> 2024_only with partial-analogue note.
- q25b (replaced by foreign worker), q25d (job moved abroad): NEW in 2024.
  -> 2024_only.
- q25e (internet platform) <-> q41b: identical PDF wording. -> clean.
- q25f (skills/tech), q25g (work-life balance), q25h (less dangerous),
  q25i (less boring) <-> q41c-f: identical PDF wording. -> clean.
- q26a-g (AI labour-market perceptions): NEW in 2024. No 2022 analogue (the
  2022 q41 battery asks ONLY about own-job impact, not labour-market-level
  perceptions, and not AI-specifically). -> 2024_only.

Source instrument: Core Questionnaire (both waves).

Total: 19 rows. 5 clean (q25e-i <-> q41b-f), 14 2024_only (3 q24 + 4 q25a-d + 7 q26).
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
LIKELY_22 = (
    "-77:|0:|1:Very unlikely|2:Unlikely|3:Likely|4:Very likely|98:Can't choose"
)
LIKELY_22_NOZERO = (
    "-77:|1:Very unlikely|2:Unlikely|3:Likely|4:Very likely|98:Can't choose"
)
LIKELY_24 = (
    "1:Very unlikely|2:Unlikely|3:Likely|4:Very likely|98:Can't choose"
)

STEM_24_Q24 = (
    "Thinking about the use of digital tools and artificial intelligence (AI) "
    "by government, to what extent do you agree or disagree with the following "
    "statements. (Note that AI means machine learning, large language models, "
    "like ChatGPT, robotics, natural language processing, and computer vision.) -- "
)
STEM_22_Q41 = (
    "How likely do you think it is that the following will happen to your job "
    "(or job opportunities) over the next five years? -- "
)
STEM_24_Q25 = STEM_22_Q41  # word-for-word identical in 2024 Core PDF
STEM_24_Q26 = (
    "Thinking about the effects of artificial intelligence (AI) in the labour "
    "market, how likely do you think the following are in [country] over the "
    "next 5 to 10 years? -- "
)

RECODE_22_24_LIKELY = "2022 -> NA on {-77, 0, 98}; 2024 -> NA on {98}"
RECODE_24_AGREE = "2024 -> NA on {98}"
RECODE_24_LIKELY = "2024 -> NA on {98}"

PARTIAL_Q41A_NOTE = (
    "Partial 2022 analogue: q41a 'My job will be replaced by a robot, computer "
    "software, an algorithm, or artificial intelligence.' 2022 conflates robot "
    "and AI (and computer/algorithm) into a single omnibus item; 2024 SPLITS "
    "this into q25a (robot only) and q25c (AI/ChatGPT only). The two cannot "
    "be cleanly mapped because a 2022 'likely' answer cannot be decomposed "
    "into robot-likelihood vs AI-likelihood. Mapped as 2024_only per the "
    "Session 04 brief's caution rule; 2022-only specifications can use q41a "
    "as a non-comparable omnibus measure."
)

# 2024 q24: government AI / digital tools (3 items, 2024_only, agree-disagree scale)
Q24 = [
    ("iv_dig_gov_ai_good",        "q24a", "Gov. use of AI is good for users"),
    ("iv_dig_gov_ai_safe",        "q24b", "Gov. will only use AI when safe & trustworthy"),
    ("iv_dig_gov_data_trust",     "q24c", "I trust gov. with the data they collect on me"),
]

# 2024 q25: digitalisation and your job (9 items). q25e-i match 2022 q41b-f
# clean; q25a/b/c/d are 2024_only (or partial).
Q25_CLEAN = [
    # (analytic, q25_letter, q41_letter, item_text)
    ("iv_dig_job_platform",   "e", "b", "My job will be replaced by a person providing a similar service on an internet platform"),
    ("iv_dig_job_skills_lose", "f", "c", "I will lose my job because I am not good enough with new technology or because I will be replaced by someone with better technological skills"),
    ("iv_dig_job_worklife",   "g", "d", "Technology will help my job and working hours become more compatible with my private life"),
    ("iv_dig_job_safer",      "h", "e", "Technology will help my job become less dangerous or physically demanding"),
    ("iv_dig_job_lessboring", "i", "f", "Technology will help my job become less boring, repetitive, stressful or mentally demanding"),
]
Q25_2024ONLY = [
    ("iv_dig_job_robot",     "a", "My job will be replaced by a robot", PARTIAL_Q41A_NOTE),
    ("iv_dig_job_foreign",   "b", "My job will be taken over by a person coming from another country",
        "New 2024 item. No 2022 analogue."),
    ("iv_dig_job_ai",        "c", "My job will be taken over by an artificial intelligence (AI) tool like ChatGPT",
        "KEY ITEM per v1 analytic variable list (Section 7) - 'closest RTM proxy to how exposed do you feel to AI'. " + PARTIAL_Q41A_NOTE),
    ("iv_dig_job_offshore",  "d", "My job will be moved to a different country",
        "New 2024 item. No 2022 analogue."),
]

# 2024 q26: AI and the labour market (7 items, all 2024_only)
Q26 = [
    ("iv_dig_ai_inequality",    "a", "AI technology will lead to a rise in income inequality"),
    ("iv_dig_ai_freetime",      "b", "AI technology will allow most people to have more free time"),
    ("iv_dig_ai_lessboring",    "c", "AI technology will allow most people to have less boring, repetitive, stressful or mentally demanding jobs"),
    ("iv_dig_ai_createjobs",    "d", "AI technology will create more jobs"),
    ("iv_dig_ai_unemployment",  "e", "AI technology will lead to higher levels of unemployment"),
    ("iv_dig_ai_surveillance",  "f", "AI technology will lead to more surveillance at work"),
    ("iv_dig_ai_retrain",       "g", "AI technology will require many people to re-train for different jobs"),
]


def build_rows():
    rows = []

    # q24 - 2024_only, agree scale
    for analytic, var, item in Q24:
        rows.append((
            analytic, "", var, "", STEM_24_Q24 + item, "", AGREE_24,
            True, "2024_only", RECODE_24_AGREE,
            f"New 2024 attitudinal item on government AI/digital tool trust. "
            f"No 2022 analogue (this construct was not asked in 2022). "
            f"PDF wording verified in 2024 Core Q24 item {var[-1]}."
        ))

    # q25 clean mappings -> 2022 q41
    for analytic, q25_letter, q41_letter, item in Q25_CLEAN:
        v22 = f"q41{q41_letter}"
        v24 = f"q25{q25_letter}"
        # value-label set for q41: q41b is _NOZERO, q41a/c/d/e/f have both
        vl22 = LIKELY_22_NOZERO if q41_letter == "b" else LIKELY_22
        rows.append((
            analytic, v22, v24, STEM_22_Q41 + item, STEM_24_Q25 + item,
            vl22, LIKELY_24,
            True, "clean", RECODE_22_24_LIKELY,
            f"PDF wording verified verbatim across both Core Questionnaires "
            f"(2022 Q41 item {q41_letter} <-> 2024 Q25 item {q25_letter}). "
            f"Identical 4-point likely scale + 98 Can't choose. Name match "
            f"({v22} == {v24}) would be INCORRECT - 2022 q25 is a "
            f"different battery (level of inequality)."
        ))

    # q25 2024_only items (a, b, c, d)
    for entry in Q25_2024ONLY:
        analytic, q25_letter, item, extra_note = entry
        v24 = f"q25{q25_letter}"
        rows.append((
            analytic, "", v24, "", STEM_24_Q25 + item, "", LIKELY_24,
            True, "2024_only", RECODE_24_LIKELY,
            extra_note
        ))

    # q26 - 2024_only AI labour market
    for analytic, q26_letter, item in Q26:
        v24 = f"q26{q26_letter}"
        rows.append((
            analytic, "", v24, "", STEM_24_Q26 + item, "", LIKELY_24,
            True, "2024_only", RECODE_24_LIKELY,
            f"New 2024 battery on AI labour-market perceptions. No 2022 "
            f"analogue: 2022 q41 asks about own-job impact only, not "
            f"labour-market-level perceptions, and not AI-specifically. PDF "
            f"wording verified in 2024 Core Q26 item {q26_letter}."
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
    assert len(rows) == 19, f"expected 19 dig-perception rows (3 q24 + 5 q25 clean + 4 q25 2024-only + 7 q26), got {len(rows)}"

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
