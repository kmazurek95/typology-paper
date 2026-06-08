"""Build the screener / insider-outsider block of variable_mapping_2022_2024.csv.

Session 02 of the RTM 2022/2024 harmonization audit.

Reads the existing CSV (written by build_dv_mapping.py in Session 01),
appends the screener-block rows, and writes the result back in place.
Re-runnable: dedupes by analytic_name on write.

Mappings are sourced from v2_prep/data/processed/rtm_insider_outsider_inventory.md
and v2_prep/data/processed/rtm_occupation_employment_questions.md.
Variable wordings transcribed from the Background Questionnaire PDFs
(NOT the Core Questionnaire — screener items live in the BG instrument).
"""

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "processed" / "variable_mapping_2022_2024.csv"

# ---------------------------------------------------------------------------
# Value-label shorthands
# ---------------------------------------------------------------------------
PAIDWORK_22 = (
    "-77:|0:|1:Yes, I was in paid work|"
    "2:Not in paid work but actively seeking a job|"
    "3:Not in paid work and not seeking a job|"
    "4:Temporarily away from paid job for health reasons or sick leave|"
    "5:Temporarily away from paid job for other reasons (e.g. annual or maternity leave)|"
    "6:|96:Other / Don't choose"
)
PAIDWORK_24 = (
    "1:Yes, I was in paid work|2:No, but seeking|3:No, and not seeking|"
    "4:No, temporarily away for health reasons|5:No, temporarily away for other reasons|"
    "6:|96:Other/Don't know"
)

EMPSELF_22 = "-77:|0:|1:Employee|2:Self-employed|3:Both"
EMPSELF_24 = "1:Employee|2:Self-employed|3:Both"

CONTRACT_22 = (
    "-77:|0:|1:Employed on a permanent contract|"
    "2:Employed on a temporary contract|3:Employed without a contract"
)
CONTRACT_24 = (
    "1:Employed on a permanent contract|"
    "2:Employed on a temporary contract|3:Employed without a contract"
)

STDWORKER_22 = "1:Not employed|2:Employed: Standard worker|3:Employed: Non-Standard worker"
STDWORKER_24 = "1:Not employed|2:Employed: Standard worker|3:Employed: Non-standard worker"

PARTNER_22 = (
    "-77:|1:Yes, my spouse/partner was in paid work|"
    "2:No, my spouse/partner was not in paid work but was actively seeking a job|"
    "3:No, my spouse/partner was not in paid work and was not seeking a job|"
    "4:No, my spouse/partner was temporarily away from their paid job because of health|"
    "5:No, my spouse/partner was temporarily away from their paid job for other reasons|"
    "6:|96:Other / Don't know|98:Other/don't know"
)
PARTNER_24 = (
    "1:Yes, in paid work|2:No, but seeking|3:No, and not seeking|"
    "4:No, temporarily away for health reasons|"
    "5:No, temporarily away for other reasons|"
    "96:Other/Don't know|99:Prefer not to say"
)

WORKER_STATUS_22 = (
    "1:Full-time employee|2:Full-time self-employed|3:Part-time employee|"
    "4:Part-time self-employed|5:Apprentice, intern or in government training scheme|"
    "6:Full-time student|7:In retirement or early retirement|"
    "8:Long-term illness, disability and/or inability to work|"
    "9:Military or community service|10:Caring for children or family members (unpaid)|"
    "11:Unemployed, i.e. not in work but actively seeking a job|12:Other"
)
WORKER_STATUS_24 = (
    "1:Full-time employee|2:Full-time self-employed|3:Part-time employee|"
    "4:Part-time self-employed|5:Apprentice, intern or in government training scheme|"
    "6:Student|7:In retirement or early retirement|"
    "8:Long-term illness, disability and/or inability to work|"
    "9:Military or community service|10:Caring for children or family members (unpaid)|"
    "11:Unemployed, i.e. not in work but actively seeking a job|"
    "96:Other/Don't know|99:Prefer not to say"
)

OCCUPATION_22 = (
    "1:Manager or senior official|2:Professional|"
    "3:Technician or associate professional|4:Clerical support worker|"
    "5:Service or sales worker|6:Skilled agricultural, forestry or fishery worker|"
    "7:Craft or trade worker|8:Plant and machine operator or assembly worker|"
    "9:Elementary occupation|97:Not applicable: Have never done paid work|"
    "99:Other / Prefer not to answer"
)

SUPPL_FREQ_22 = (
    "-77:|0:|1:Regularly (once a month or more often)|"
    "2:Occasionally (once every few months)|3:Once or a few times|4:Never"
)
SUPPL_BIN_24 = "0:Not ticked|1:Ticked"

PUBPRIV_24 = "1:Public employer|2:Private employer"
PLATFORM_MAIN_24 = "1:Yes|2:No|3:Both"
PLATFORM_OO_24 = (
    "1:Online (e.g. translator, web developer, architect)|"
    "2:Offline (e.g. driver, cleaner, courier)|3:Both"
)
FIRMSIZE_24 = "(open numeric, no value labels; integers >= 1)"

# ---------------------------------------------------------------------------
# Wordings (verbatim from Background Questionnaire PDFs)
# ---------------------------------------------------------------------------
W_PAIDWORK = (
    "Did you do any paid work in the last week? "
    "(Note: We are referring now to your current work status, i.e. your status at the moment.)"
)
W_EMPSELF = "Are you currently working as an employee or are you self-employed?"
W_CONTRACT = (
    "What type of employee contract do you have in your current main job? "
    "Are you employed on a permanent contract (i.e. an open-ended contract without a "
    "fixed end date), a temporary contract (i.e. job contract of limited duration) or "
    "employed without a contract?"
)
W_STDWORKER = (
    "OECD-derived recode: Not employed iff S(paid work) in {b, c}; "
    "Standard worker iff S(emp/self-emp) in {a, c} AND S(contract) = a; "
    "Non-standard worker iff in paid work and not Standard."
)
W_PARTNER_22 = (
    "Did your spouse/partner do any paid work in the last week? "
    "(Note: We are referring now to your spouse's current work status.)"
)
W_PARTNER_24 = "Did your spouse or partner do any paid work in the last week?"
W_WORKER_STATUS = (
    "Please tell us which of these statements best describes your current work "
    "arrangements in your main job. (If more than one statement applies to you, "
    "please indicate the statement that best describes how you see yourself.)"
)
W_OCC_22 = (
    "Which of the following occupations best describes your role in your current main job? "
    "(Note: If you are retired or currently out of work, please answer for your most "
    "recent job.) [9 substantive categories = ISCO-08 Major Groups 1-9, plus "
    "'Not applicable: Have never done paid work' and 'Other / Prefer not to answer'.]"
)
W_SUPPL_22 = (
    "Some people work more than one job. In the past 12 months, how often - if at all - "
    "have you done any of the following kinds of paid work in addition to the main job "
    "you mentioned? -- a: A second job based on an internet platform/using an app "
    "(e.g. Uber, Task Rabbit). b: A second job not on an internet platform "
    "(e.g. babysitting, cleaning, bartending, etc). [4-point frequency scale.]"
)
W_SUPPL_24 = (
    "Some people work more than one job. In the past 12 months, have you done any of "
    "the following kinds of paid work in addition to the main job you mentioned above? "
    "-- a: Supplementary paid work through a platform or app and completed offline. "
    "b: Supplementary paid work through a platform or app and completed online. "
    "c: Supplementary paid work not based on a platform or app. "
    "d: I did not do any supplementary paid work in addition to my main job in the past "
    "12 months. [Multi-select tick-list; (d) is exclusive.]"
)
W_PUBPRIV_24 = "In your main job, do you work for a public or private employer?"
W_FIRMSIZE_24 = (
    "Including yourself, roughly how many workers in total work in your company or firm? "
    "(Open numeric, integers >= 1.)"
)
W_PLATFORM_MAIN_24 = (
    "Is your main job performed through an internet platform, such as Uber or Task Rabbit?"
)
W_PLATFORM_OO_24 = (
    "Are the jobs that you perform online executed or completed online or offline? "
    "(Filtered on S29 in {Yes, Both}.)"
)

# ---------------------------------------------------------------------------
# Recoding rules
# ---------------------------------------------------------------------------
R_SENT_22_NONE = "2022 -> NA on {-77, 0}; 2024 -> no sentinel recoding required"
R_PARTNER = (
    "2022 -> NA on {-77, 6}; collapse {96, 98} both to 'Other/Don't know'; "
    "2024 -> NA on {99} (Prefer not to say); both waves recode 96 to NA "
    "for substantive analyses or keep as 'Other' depending on spec"
)
R_WORKER_STATUS = (
    "2022 -> recode 12 ('Other') to 96; 2024 -> recode 99 ('Prefer not to say') to "
    "96 (or treat as NA); both -> NA on 96 for substantive analyses. "
    "NB: 2022 code 6 = 'Full-time student'; 2024 code 6 = 'Student' (broader)."
)
R_SUPPL = (
    "Pool to binary 'any supplementary work in past 12 months': "
    "2022 -> 1 iff (s26a in {1,2,3} OR s26b in {1,2,3}), else 0 (with -77/0/4 -> 0). "
    "2024 -> 1 iff (s31a == 1 OR s31b == 1 OR s31c == 1), else 0 (s31d not used). "
    "Frequency distinction in 2022 is NOT pool-feasible and would require wave-specific spec."
)
R_NONE = "No sentinel recoding required."

# ---------------------------------------------------------------------------
# Rows
# (analytic, v22, v24, wording22, wording24, vl22, vl24,
#  scale_compat, status, recode, notes)
# ---------------------------------------------------------------------------
ROWS = [
    # ---- Core H-S inputs (concepts 1-4) -------------------------------------
    (
        "iv_paidwork_lastweek", "s9", "s10",
        W_PAIDWORK, W_PAIDWORK, PAIDWORK_22, PAIDWORK_24,
        True, "clean", R_SENT_22_NONE,
        "Name match would be INCORRECT (2024 s9 is 'Income decile'; 2024 s10 is "
        "the analogue of 2022 s9). Verified by wording per "
        "rtm_insider_outsider_inventory.md concept 1. Substantive codes 1-5 align "
        "exactly; 2024 uses abbreviated label text. 96 is shared 'Other/Don't know' "
        "residual. NB the 2022 Stata label says '(Q4 2021)' but the question stem "
        "is 'current work status (i.e. status at the moment)'.",
    ),
    (
        "iv_emp_self", "s10", "s11",
        W_EMPSELF, W_EMPSELF, EMPSELF_22, EMPSELF_24,
        True, "clean", R_SENT_22_NONE,
        "Name match would be INCORRECT - 2024 s10 is 'Paid work last week', NOT "
        "employee/self-emp. Verified by wording. Identical 3-code value labels; "
        "2022 has -77/0 filter sentinels that 2024 doesn't carry.",
    ),
    (
        "iv_contract_type", "s11", "s12",
        W_CONTRACT, W_CONTRACT, CONTRACT_22, CONTRACT_24,
        True, "clean", R_SENT_22_NONE,
        "Name match would be INCORRECT - 2024 s11 is 'Employee/self-employed', NOT "
        "contract type. Verified by wording. Identical 3-code value labels; "
        "2022 has -77/0 filter sentinels.",
    ),
    (
        "iv_standard_worker", "s10_11", "s11_12",
        W_STDWORKER, W_STDWORKER, STDWORKER_22, STDWORKER_24,
        True, "clean", R_NONE,
        "Pre-derived by OECD using the same rule in both waves. Variable name "
        "tracks the underlying components (s10/s11 -> s11/s12 across waves). "
        "Only cosmetic difference: 'Non-Standard worker' (2022 cap S) vs "
        "'Non-standard worker' (2024 lower s).",
    ),

    # ---- Worker status omnibus (concept 5) ----------------------------------
    (
        "iv_worker_status", "s22", "s25",
        W_WORKER_STATUS, W_WORKER_STATUS, WORKER_STATUS_22, WORKER_STATUS_24,
        False, "needs_recode", R_WORKER_STATUS,
        "Name match (s22 vs s22) would be INCORRECT in 2024 - 2024 s22 is "
        "'Number of children'. Verified by wording per inventory concept 5. "
        "Substantive codes 1-11 align; differences are (a) code 6 narrows from "
        "'Full-time student' to 'Student' in 2024 (a slight category broadening), "
        "(b) the 'Other' bucket has different codes: 2022 uses 12, 2024 splits "
        "into 96 (Other/Don't know) + 99 (Prefer not to say).",
    ),

    # ---- Partner status (concept 6) -----------------------------------------
    (
        "iv_partner_paidwork", "s17", "s18",
        W_PARTNER_22, W_PARTNER_24, PARTNER_22, PARTNER_24,
        True, "needs_recode", R_PARTNER,
        "Name match (s17 vs s17) would be INCORRECT in 2024 - 2024 s17 is "
        "'Living with partner' (the screener insertion shifted everything by 1). "
        "Verified by wording. Codes 1-5 are substantively identical. 2022 has "
        "redundant 'Other/Don't know' under both 96 and 98 (collapse on read); "
        "2024 introduces 99 'Prefer not to say' as a separate category.",
    ),

    # ---- Occupation (the s23 TRAP) ------------------------------------------
    (
        "iv_occupation_isco1", "s23", "",
        W_OCC_22, "",
        OCCUPATION_22, "",
        False, "2022_only", R_NONE,
        "*** S23 TRAP - DO NOT USE 2024 s23. *** "
        "2022 s23 = Occupation (ISCO-08 Major Groups 1-9, used downstream for the "
        "AIOE merge). 2024 s23 = 'Age of youngest child (under 18) in household' "
        "(numeric, no value labels) - completely different question, identical "
        "variable name. The 2024 wave DROPS the occupation item entirely (no "
        "equivalent question anywhere in the 2024 BG instrument). Script 04 must "
        "match by analytic_name, not by variable name, to avoid silently merging "
        "household composition data into the occupation column. AIOE-based AI "
        "exposure is computable only for 2022; 2024 has only NACE sector (s26), "
        "public/private (s27), firm size (s28), and platform indicators (s29-s30) "
        "as occupational proxies. See rtm_occupation_employment_questions.md.",
    ),

    # ---- Supplementary work (concept 12) ------------------------------------
    (
        "iv_suppl_work_any", "s26a;s26b", "s31a;s31b;s31c",
        W_SUPPL_22, W_SUPPL_24, SUPPL_FREQ_22, SUPPL_BIN_24,
        False, "needs_recode", R_SUPPL,
        "Multi-source mapping: composite analytic variable from 2 source vars in "
        "2022 (frequency scale) and 3 source vars in 2024 (binary tick-list). "
        "Format mismatch: 2022 records frequency, 2024 records ever/never only. "
        "Frequency distinction is NOT pool-feasible. The 2024 'None' indicator "
        "s31d is redundant and intentionally NOT used in the pooled recode. "
        "Name match would be misleading: 2024 s26a-b do not exist; 2024 s31a-d "
        "are partner-related items in 2022, so a name-based join would silently "
        "pull the wrong construct.",
    ),

    # ---- 2024-only screener items (concepts 8-11) ---------------------------
    (
        "iv_public_employer", "", "s27",
        "", W_PUBPRIV_24, "", PUBPRIV_24,
        True, "2024_only", R_NONE,
        "Wave-specific. 2022 has NO public/private employer question. Useful for "
        "extending H-S coding to a public-sector 'insider' subtype in 2024-only "
        "specifications; cannot be back-projected to 2022. Filtered on "
        "(s10 in {a,d,e}) AND (s11 in {a,c}).",
    ),
    (
        "iv_firm_size", "", "s28",
        "", W_FIRMSIZE_24, "", FIRMSIZE_24,
        True, "2024_only", R_NONE,
        "Wave-specific. 2022 has NO firm-size question. Open numeric (integers >= 1). "
        "No value labels. Filtered on s10 in {a,d,e}.",
    ),
    (
        "iv_platform_main", "", "s29",
        "", W_PLATFORM_MAIN_24, "", PLATFORM_MAIN_24,
        True, "2024_only", R_NONE,
        "Wave-specific. 2022 only asks about platform work in the SECOND-JOB "
        "context (s26a). 2024 asks about main job (s29) AND second job (s31a/b). "
        "Filtered on s10 in {a,d,e}.",
    ),
    (
        "iv_platform_online_offline", "", "s30",
        "", W_PLATFORM_OO_24, "", PLATFORM_OO_24,
        True, "2024_only", R_NONE,
        "Wave-specific. Filtered on s29 in {Yes, Both}. Distinguishes online vs "
        "offline platform work (cf. Schoukens & Pulignano typology).",
    ),
]

HEADER = [
    "analytic_name", "var_2022", "var_2024",
    "wording_2022", "wording_2024",
    "value_labels_2022", "value_labels_2024",
    "scale_compatible", "harmonization_status", "recode_rule",
    "notes", "verified_by_human",
]


INSTRUMENT_TAG = " [instrument: Background]"


def main() -> None:
    # Read existing rows (from Session 01)
    existing: list[dict] = []
    if OUT.exists():
        with OUT.open("r", encoding="utf-8", newline="") as f:
            existing = list(csv.DictReader(f))

    # Build new rows as dicts; dedupe by analytic_name (new rows win)
    new_dicts = []
    for r in ROWS:
        d = dict(zip(HEADER[:-1], r))
        # Append instrument tag to notes (idempotent: only add if missing)
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
        f"{len(kept)} preserved from prior sessions + {len(new_dicts)} new)"
    )


if __name__ == "__main__":
    main()
