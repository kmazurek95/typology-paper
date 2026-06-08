"""Build the sector / exposure-inputs block of variable_mapping_2022_2024.csv.

Session 03 of the RTM 2022/2024 harmonization audit.

Adds:
- iv_nace_sector: 2022 s24 -> 2024 s26 (NACE Rev. 2 1-letter section).
  PRIMARY exposure merge key for individual-level Felten AIOE.
- iv_suppl_platform_offline / _online / _other: individual 2024-only
  decompositions of the supplementary-work tick-list (s31a/b/c). These
  complement the Session 02 pooled binary iv_suppl_work_any, providing
  per-channel granularity for 2024 robustness specs.

Skipped (already mapped in Session 02 - intentionally NOT re-added here):
- iv_emp_self (s10/s11), iv_contract_type (s11/s12),
  iv_worker_status (s22/s25), iv_paidwork_lastweek (s9/s10),
  iv_public_employer (s27), iv_firm_size (s28),
  iv_platform_main (s29), iv_platform_online_offline (s30).
  The Session 03 brief listed these in scope, but they're identical
  to Session 02 mappings - duplicating would be redundant.

Like the prior builders, this script dedupes by analytic_name on write.

Source instrument: Background Questionnaire (per Session 02 heuristic;
s* in s2-s30 range -> BG, not Core - corrects the Session 03 brief).
"""

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "processed" / "variable_mapping_2022_2024.csv"
INSTRUMENT_TAG = " [instrument: Background]"

# ---------------------------------------------------------------------------
# Value-label shorthands
# ---------------------------------------------------------------------------
# NACE: 19 substantive sections (A-S) + 97 (never employed) + 99 (other/refuse)
NACE_22 = (
    "1:Agriculture, forestry and fishing|2:Mining and quarrying|3:Manufacturing|"
    "4:Electricity, gas, steam and air conditioning supply|"
    "5:Water supply; sewerage, waste management and remediation activities|"
    "6:Construction|"
    "7:Wholesale and retail trade (including e.g. repair of motor vehicles)|"
    "8:Transportation and storage|9:Accommodation and food service activities|"
    "10:Information and communication|11:Financial and insurance activities|"
    "12:Real estate activities|"
    "13:Professional, scientific and technical activities (including e.g. professional services like lawyers or accountants)|"
    "14:Administrative and support service activities|"
    "15:Public administration and defence (including e.g. state social security administration)|"
    "16:Education|17:Human health and social work activities|"
    "18:Arts, entertainment and recreation|19:Other service activities|"
    "97:Not applicable: Never been employed|99:Other / Prefer not to answer"
)
NACE_24 = (
    "1:Agriculture, forestry and fishing|2:Mining and quarrying|3:Manufacturing|"
    "4:Electricity, gas, steam and air conditioning supply|"
    "5:Water supply, sewerage, waste management and remediation activities|"
    "6:Construction|"
    "7:Wholesale and retail trade (including e.g. repair of motor vehicles)|"
    "8:Transportation and storage|9:Accommodation and food service activities|"
    "10:Information and communication|11:Financial and insurance activities|"
    "12:Real estate activities|"
    "13:Professional, scientific and technical activities (including e.g. professional services like lawyers or accountants)|"
    "14:Administrative and support service activities|"
    "15:Public administration and defence (including e.g. state social security administration)|"
    "16:Education|17:Human health and social work activities|"
    "18:Arts, entertainment and recreation|19:Other service activities|"
    "97:Not applicable: Have never done paid work|99:Other/Prefer not to say"
)

BINARY_TICK = "0:Not ticked|1:Ticked"

# ---------------------------------------------------------------------------
# Wordings (verbatim from Background Questionnaire PDFs)
# ---------------------------------------------------------------------------
W_NACE_22 = (
    "Which of the following categories best describes the sector you primarily "
    "work in (regardless of your actual position)? (Note: If you are retired or "
    "currently out of work, please answer for your most recent job.) "
    "[19 substantive options a-s = NACE Rev. 2 sections A-S, plus 'Other / Prefer "
    "not to answer' and 'Not applicable: Never been employed'.]"
)
W_NACE_24 = (
    "Which of the following categories best describes the sector you work in at "
    "your main job (regardless of your actual position)? (Note: If you are retired "
    "or currently out of work, please answer for your most recent job.) "
    "[19 substantive options a-s = NACE Rev. 2 sections A-S, plus 'Other / Prefer "
    "not to say' and 'Not applicable: Have never done paid work'.]"
)

W_SUPPL_24_STEM = (
    "Some people work more than one job. In the past 12 months, have you done any "
    "of the following kinds of paid work in addition to the main job you mentioned "
    "above? Tick all that apply. [Option (d) is exclusive.] -- "
)
W_SUPPL_OFFLINE_24 = (
    W_SUPPL_24_STEM
    + "a: Supplementary paid work through a platform or app and completed offline "
    "(such as Uber driver or delivery)"
)
W_SUPPL_ONLINE_24 = (
    W_SUPPL_24_STEM
    + "b: Supplementary paid work through a platform or app and completed online "
    "(such as translator or web developer at Upwork)"
)
W_SUPPL_OTHER_24 = (
    W_SUPPL_24_STEM
    + "c: Supplementary paid work not based on a platform or app (such as "
    "bartending or babysitting)"
)

# ---------------------------------------------------------------------------
# Recoding rules
# ---------------------------------------------------------------------------
R_NACE = (
    "No value-recoding required. Treat codes {97, 99} as NA for substantive "
    "analyses (never-employed and prefer-not-to-say). Cast both waves to a "
    "common integer dtype (Int8 sufficient). 2022 dtype is float64 (wasted bits "
    "per rtm_2022_size_diagnostic.md); 2024 is already int8."
)
R_NONE = "No sentinel recoding required (binary tick-box)."

# ---------------------------------------------------------------------------
# Rows
# ---------------------------------------------------------------------------
ROWS = [
    # ---- NACE 1-letter sector (PRIMARY exposure merge key) ------------------
    (
        "iv_nace_sector", "s24", "s26",
        W_NACE_22, W_NACE_24, NACE_22, NACE_24,
        True, "clean", R_NACE,
        "FULLY HARMONIZED across waves (verified against rtm_nace_sector_audit.md). "
        "21-for-21 category match: 19 substantive NACE Rev. 2 sections A-S in "
        "identical numeric order (codes 1-19), plus code 97 (never employed) "
        "and code 99 (other/prefer not to say). Differences are strictly "
        "cosmetic: (a) code 5 punctuation ';' (2022) -> ',' (2024); (b) code 97 "
        "wording 'Never been employed' -> 'Have never done paid work' (same "
        "construct); (c) code 99 wording 'Other / Prefer not to answer' -> "
        "'Other/Prefer not to say'; (d) question stem 'sector you primarily work "
        "in' -> 'sector you work in at your main job' (same construct + same "
        "skip rule for retirees). Name match would be INCORRECT (2024 s24 is "
        "non-existent in 2024 codebook; 2024 s26 = Industry is the analogue of "
        "2022 s24). This is the PRIMARY merge key for the individual-level "
        "Felten AIOE exposure measure - the 2022 wave can also use occupation "
        "(s23, see iv_occupation_isco1) but the 2024 wave must rely on this "
        "sector-level proxy because the occupation item was dropped (see s23 "
        "trap, Session 02)."
    ),

    # ---- Individual 2024-only platform supplementary-work indicators --------
    # These complement the pooled iv_suppl_work_any from Session 02; useful for
    # 2024 robustness specs that need per-channel decomposition.
    (
        "iv_suppl_platform_offline", "", "s31a",
        "", W_SUPPL_OFFLINE_24, "", BINARY_TICK,
        True, "2024_only", R_NONE,
        "Wave-specific. 2022 has only a 4-point frequency scale across two "
        "channels (s26a/b) that doesn't decompose cleanly into "
        "online-vs-offline platform work, so no 2022 analogue is constructible. "
        "Used jointly with iv_suppl_platform_online for 2024 robustness specs "
        "decomposing the pooled iv_suppl_work_any (Session 02)."
    ),
    (
        "iv_suppl_platform_online", "", "s31b",
        "", W_SUPPL_ONLINE_24, "", BINARY_TICK,
        True, "2024_only", R_NONE,
        "Wave-specific. Paired with iv_suppl_platform_offline. See note there "
        "for why no 2022 analogue."
    ),
    (
        "iv_suppl_nonplatform_other", "", "s31c",
        "", W_SUPPL_OTHER_24, "", BINARY_TICK,
        True, "2024_only", R_NONE,
        "Wave-specific. Non-platform supplementary work (bartending, babysitting, "
        "etc.). 2022 s26b is the closest analogue but uses a frequency scale "
        "rather than a binary tick, and is captured in the pooled "
        "iv_suppl_work_any (Session 02). 2024 s31d ('None') is the negation of "
        "(a OR b OR c) and is intentionally NOT mapped as an analytic variable."
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
    existing: list[dict] = []
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
        f"{len(kept)} preserved from prior sessions + {len(new_dicts)} new)"
    )


if __name__ == "__main__":
    main()
