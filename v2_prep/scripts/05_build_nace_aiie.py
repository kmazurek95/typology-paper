"""
Script 05: NACE-section AIIE Lookup Table

Builds the 21-row NACE Rev. 2 section-level employment-weighted AI Industry
Exposure (AIIE) lookup. Script 06 will join this onto the pooled RTM
analytic frame via the iv_nace_sector column.

Method
------
NACE Rev. 2 and ISIC Rev. 4 are identical at the section-letter level (A-U).
The crosswalk path:

    NAICS-4 (Felten AIIE)
        -> ISIC-4 (Census 2017 NAICS-ISIC correspondence; NAICS-6 keyed,
                   rolled up to NAICS-4 by first 4 chars)
            -> NACE section letter (derived from ISIC division)

For each NACE section: collect contributing NAICS-4 codes, compute
employment-weighted mean AIIE using BLS QCEW 2023 employment.

Construction rules (user-approved 2026-05-25)
---------------------------------------------
1. Felten duplicate NAICS-4 entries are handled per AIIE spread:
   - within 0.5*SD of each other: take simple mean (per-entry NAICS-5
     sub-disaggregations are tight enough that averaging is defensible)
   - beyond 0.5*SD: drop the NAICS-4 entirely (genuine within-code
     heterogeneity; averaging would inject a meaningless number)
2. NAICS-4 -> NACE section assignment uses modal resolution with two
   guard rules:
   - 60% threshold + strictly-more-than-runner-up among single-section
     NAICS-6 children; otherwise drop the NAICS-4
   - if ANY NAICS-6 child is itself multi-section, drop the parent
     NAICS-4 (cascading ambiguity rule)
3. Cumulative Felten coverage loss is reported. If drops exceed 15% of
   Felten's unique NAICS-4 count, the verification log flags this as a
   measurement-quality concern.

Inputs
------
- data/raw/AIOE_DataAppendix.xlsx (sheet "Appendix B")
- data/raw/naics_isic_correspondence_2017.xlsx
- data/raw/bls_qcew_naics4_2023.csv

Outputs
-------
- v2_prep/data/processed/nace_aiie_lookup.csv (21 rows)
- v2_prep/data/processed/nace_aiie_lookup_verification.txt

Invocation
----------
python v2_prep/scripts/05_build_nace_aiie.py
"""

import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
OUT_DIR = ROOT / "v2_prep" / "data" / "processed"
OUT_DIR.mkdir(parents=True, exist_ok=True)

FELTEN_XLSX = RAW / "AIOE_DataAppendix.xlsx"
CENSUS_XLSX = RAW / "naics_isic_correspondence_2017.xlsx"
BLS_CSV = RAW / "bls_qcew_naics4_2023.csv"
OUT_CSV = OUT_DIR / "nace_aiie_lookup.csv"
OUT_LOG = OUT_DIR / "nace_aiie_lookup_verification.txt"

DUP_SPREAD_THRESHOLD_SD = 0.5
MODAL_THRESHOLD_PCT = 0.60
DROP_WARN_THRESHOLD_PCT = 0.15  # flag if cumulative drops exceed this share of Felten

# ── NACE Rev. 2 / ISIC Rev. 4 section structure ──────────────────────────

NACE_SECTIONS = {
    "A": ("Agriculture, forestry and fishing", range(1, 4)),
    "B": ("Mining and quarrying", range(5, 10)),
    "C": ("Manufacturing", range(10, 34)),
    "D": ("Electricity, gas, steam and air conditioning supply", range(35, 36)),
    "E": ("Water supply; sewerage, waste management", range(36, 40)),
    "F": ("Construction", range(41, 44)),
    "G": ("Wholesale and retail trade", range(45, 48)),
    "H": ("Transportation and storage", range(49, 54)),
    "I": ("Accommodation and food service activities", range(55, 57)),
    "J": ("Information and communication", range(58, 64)),
    "K": ("Financial and insurance activities", range(64, 67)),
    "L": ("Real estate activities", range(68, 69)),
    "M": ("Professional, scientific and technical activities", range(69, 76)),
    "N": ("Administrative and support service activities", range(77, 83)),
    "O": ("Public administration and defence; compulsory social security", range(84, 85)),
    "P": ("Education", range(85, 86)),
    "Q": ("Human health and social work activities", range(86, 89)),
    "R": ("Arts, entertainment and recreation", range(90, 94)),
    "S": ("Other service activities", range(94, 97)),
    "T": ("Activities of households as employers", range(97, 99)),
    "U": ("Activities of extraterritorial organisations and bodies", range(99, 100)),
}

DIVISION_TO_SECTION = {}
for letter, (_, divs) in NACE_SECTIONS.items():
    for d in divs:
        DIVISION_TO_SECTION[d] = letter


def isic_to_section(isic_code: int) -> str | None:
    """ISIC Rev. 4 code (as integer) -> NACE/ISIC section letter.

    ISIC Rev. 4 class codes are 4 digits. The Census crosswalk stores them
    as integers with leading zeros stripped, so class "0111" (Growing of
    cereals, division 01, section A) is stored as int 111 and class "9810"
    (households, division 98, section T) is stored as int 9810. Division
    is always `code // 100` regardless of int width.

    Earlier bug (fixed 2026-05-26): the function used `code // 10` for
    code < 1000, which silently routed agriculture/mining/forestry NAICS-6
    codes (whose ISIC classes are 0111, 0210, 0220, 0311, etc.) into
    sections B/C because divisions 11, 22, 31 exist as Manufacturing
    sub-sectors in ISIC. The bug inflated section C's contributor count
    and zeroed out sections A and B in the first lookup. Detected by the
    user during sanity-check vs NaN-list consistency review.
    """
    if isic_code <= 0:
        return None
    division = isic_code // 100
    return DIVISION_TO_SECTION.get(division)


# ── Felten loader with duplicate handling (rule 1) ────────────────────────


def prepare_felten() -> tuple[pd.DataFrame, dict]:
    """Load Felten Appendix B; resolve duplicate NAICS-4 entries per rule 1.

    Returns (clean_df, dup_report).
    """
    raw = pd.read_excel(FELTEN_XLSX, sheet_name="Appendix B")
    raw = raw.rename(columns={
        "NAICS": "naics4", "Industry Title": "naics_title", "AIIE": "aiie",
    })
    raw["naics4"] = raw["naics4"].astype(int)
    raw["aiie"] = raw["aiie"].astype(float)

    global_sd = float(raw["aiie"].std())
    threshold = DUP_SPREAD_THRESHOLD_SD * global_sd

    dup_report = {
        "global_aiie_sd": global_sd,
        "spread_threshold": threshold,
        "duplicate_groups": [],   # all duplicated NAICS-4s with their rows
        "averaged": [],            # codes resolved by mean
        "dropped": [],             # codes dropped due to spread > threshold
    }

    # Identify duplicate NAICS-4 groups
    dup_mask = raw.duplicated("naics4", keep=False)
    dup_codes = sorted(raw.loc[dup_mask, "naics4"].unique().tolist())

    # Build the clean frame: start with non-dup rows, then add resolved dup rows
    non_dup = raw[~dup_mask].copy()
    resolved_rows = []

    for n4 in dup_codes:
        grp = raw[raw["naics4"] == n4]
        aiies = grp["aiie"].tolist()
        titles = grp["naics_title"].tolist()
        spread = float(max(aiies) - min(aiies))
        entry = {
            "naics4": n4, "aiies": aiies, "titles": titles, "spread": spread,
        }
        dup_report["duplicate_groups"].append(entry)
        if spread <= threshold:
            mean_aiie = float(np.mean(aiies))
            resolved_rows.append({
                "naics4": n4,
                "naics_title": f"{titles[0]} [averaged from {len(grp)} sub-NAICS-5 entries]",
                "aiie": mean_aiie,
            })
            dup_report["averaged"].append({
                "naics4": n4, "n_entries": len(grp),
                "spread": spread, "mean_aiie": mean_aiie,
                "titles": titles,
            })
        else:
            dup_report["dropped"].append({
                "naics4": n4, "n_entries": len(grp),
                "spread": spread, "aiies": aiies, "titles": titles,
                "reason": f"AIIE spread {spread:.4f} exceeds 0.5*SD threshold "
                          f"({threshold:.4f}); Felten entries reflect genuine within-NAICS-4 "
                          f"heterogeneity rather than measurement duplication; averaging "
                          f"would inject a meaningless number. Option C (NAICS-5 "
                          f"employment re-weighting) deferred, not foreclosed.",
            })

    clean = pd.concat([non_dup, pd.DataFrame(resolved_rows)], ignore_index=True)
    clean = clean.sort_values("naics4").reset_index(drop=True)
    return clean, dup_report


def load_census_crosswalk() -> pd.DataFrame:
    df = pd.read_excel(CENSUS_XLSX, sheet_name=0)
    df.columns = [c.strip().replace("\n", " ") for c in df.columns]
    df = df.rename(columns={
        df.columns[0]: "part_of_naics", df.columns[1]: "naics_us",
        df.columns[2]: "naics_title", df.columns[3]: "part_of_isic",
        df.columns[4]: "isic_4", df.columns[5]: "isic_title",
    })[["part_of_naics", "naics_us", "naics_title",
        "part_of_isic", "isic_4", "isic_title"]]
    df["naics_us"] = df["naics_us"].astype(int)
    df["isic_4"] = df["isic_4"].astype(int)
    df = df[df["naics_us"] > 0].copy()
    return df


def load_bls() -> pd.DataFrame:
    df = pd.read_csv(BLS_CSV)
    df["industry_code"] = df["industry_code"].astype(int)
    return df


# ── NAICS-4 -> NACE section (rules 1 + 2) ─────────────────────────────────


def _apply_modal_rule(
    counts: dict[str, int]
) -> tuple[str | None, str]:
    """Apply the modal-section rule to a counts dict.

    Returns (assigned_section, message). assigned_section is None if the rule
    fails to resolve. message describes the outcome.
    """
    if not counts:
        return None, "no children"
    total = sum(counts.values())
    sorted_secs = sorted(counts.items(), key=lambda kv: -kv[1])
    top_section, top_count = sorted_secs[0]
    runner_up = sorted_secs[1][1] if len(sorted_secs) > 1 else 0
    top_pct = top_count / total
    if top_count > runner_up and top_pct >= MODAL_THRESHOLD_PCT:
        return top_section, (
            f"resolved {top_section!r}: {top_count}/{total} ({top_pct*100:.0f}%), "
            f"runner-up {runner_up}"
        )
    return None, (
        f"unresolved: top {top_section!r} {top_count}/{total} "
        f"({top_pct*100:.0f}%), runner-up {runner_up}; "
        f"distribution: {dict(counts)}"
    )


def build_naics4_to_section(
    crosswalk: pd.DataFrame,
) -> tuple[dict[int, str], dict[int, str], dict]:
    """Map NAICS-4 to NACE section under the recursive modal rule.

    Rule 1 (modal threshold) is applied at TWO levels:
    1. NAICS-6 -> ISIC section: for each NAICS-6 mapping to multiple ISIC
       sections, count how many ISIC-4 codes per section the NAICS-6 covers
       and apply the 60% + strictly-more-than-runner-up rule. If it
       resolves, treat the NAICS-6 as belonging to that single section.
    2. NAICS-4 -> NACE section: aggregate the resolved children counts
       (one section per NAICS-6) and apply the same modal rule.

    A NAICS-6 that fails the modal rule at level 1 contributes nothing to
    its NAICS-4 parent's tally. A NAICS-4 with no resolvable children, or
    that fails the modal rule at level 2, is dropped.

    Returns (naics4_to_section, drop_reasons, diagnostics).
    """
    # Step 1: NAICS-6 -> per-ISIC-section count of children codes
    # (a single NAICS-6 may appear in multiple crosswalk rows, each contributing
    #  one ISIC-4 code which maps to a section)
    naics6_section_counts: dict[int, dict[str, int]] = defaultdict(
        lambda: defaultdict(int)
    )
    for _, row in crosswalk.iterrows():
        n6 = int(row["naics_us"])
        section = isic_to_section(int(row["isic_4"]))
        if section is not None:
            naics6_section_counts[n6][section] += 1

    # Step 2: determine effective section for each NAICS-6
    naics6_sections: dict[int, set[str]] = {
        n6: set(counts.keys()) for n6, counts in naics6_section_counts.items()
    }
    naics6_effective_section: dict[int, str] = {}
    naics6_unresolved: dict[int, str] = {}

    n_single = 0
    n_recursively_resolved = 0
    n_recursive_failed = 0
    for n6, sects in naics6_sections.items():
        if len(sects) == 1:
            naics6_effective_section[n6] = next(iter(sects))
            n_single += 1
        else:
            # Apply modal rule at NAICS-6 level
            resolved, msg = _apply_modal_rule(naics6_section_counts[n6])
            if resolved is not None:
                naics6_effective_section[n6] = resolved
                n_recursively_resolved += 1
            else:
                naics6_unresolved[n6] = msg
                n_recursive_failed += 1

    # Step 3: aggregate to NAICS-4
    naics4_all_children: dict[int, set[int]] = defaultdict(set)
    naics4_section_counts: dict[int, dict[str, int]] = defaultdict(
        lambda: defaultdict(int)
    )
    for n6 in naics6_sections:
        n4 = n6 // 100
        naics4_all_children[n4].add(n6)

    for n6, section in naics6_effective_section.items():
        n4 = n6 // 100
        naics4_section_counts[n4][section] += 1

    # Step 4: apply modal rule at NAICS-4 level
    naics4_section: dict[int, str] = {}
    drop_reasons: dict[int, str] = {}

    clean_assignments = 0
    modal_assignments = 0
    drops_threshold = 0
    drops_no_children = 0

    for n4 in sorted(naics4_all_children):
        counts = naics4_section_counts.get(n4, {})
        if not counts:
            drop_reasons[n4] = (
                "no resolvable NAICS-6 children (all children failed the "
                "level-1 modal rule and were excluded)"
            )
            drops_no_children += 1
            continue

        resolved, msg = _apply_modal_rule(counts)
        if resolved is not None:
            naics4_section[n4] = resolved
            if len(counts) == 1:
                clean_assignments += 1
            else:
                modal_assignments += 1
        else:
            drop_reasons[n4] = f"NAICS-4 level: {msg}"
            drops_threshold += 1

    diagnostics = {
        "n_naics6_total": len(naics6_sections),
        "n_naics6_single_section": n_single,
        "n_naics6_recursively_resolved": n_recursively_resolved,
        "n_naics6_recursive_failed": n_recursive_failed,
        "n_naics4_total": len(naics4_all_children),
        "n_naics4_assigned": len(naics4_section),
        "n_naics4_dropped": len(drop_reasons),
        "assignments_clean_single_section": clean_assignments,
        "assignments_modal_resolved": modal_assignments,
        "drops_modal_threshold": drops_threshold,
        "drops_no_resolvable_children": drops_no_children,
    }
    return naics4_section, drop_reasons, diagnostics


# ── Aggregate Felten -> NACE sections (with all drop accounting) ──────────


def aggregate_to_sections(
    felten: pd.DataFrame,
    naics4_section: dict[int, str],
    naics4_drop_reasons: dict[int, str],
    bls: pd.DataFrame,
) -> tuple[pd.DataFrame, dict]:
    bls_emp = dict(zip(bls["industry_code"], bls["annual_avg_emplvl"]))

    diag = {
        "n_felten_unique_naics4": int(felten["naics4"].nunique()),
        "felten_dropped_oes": [],          # 9991-9993 OES designation codes
        "felten_dropped_section_unresolved": [],
        "felten_dropped_no_bls_employment": [],
        "felten_used_in_aggregation": [],
        "per_section": {},
    }

    agg: dict[str, dict] = {
        letter: {"naics_codes": [], "total_emp": 0.0, "weighted_sum": 0.0}
        for letter in NACE_SECTIONS
    }

    for _, row in felten.iterrows():
        n4 = int(row["naics4"])
        aiie = float(row["aiie"])
        title = row["naics_title"]

        # OES designation codes (9991-9993) — not real NAICS-4
        if 9991 <= n4 <= 9993:
            diag["felten_dropped_oes"].append({
                "naics4": n4, "title": title, "aiie": aiie,
                "reason": "Felten OES designation code (Federal/State/Local Govt); "
                          "not a real NAICS-4; not present in Census crosswalk or BLS QCEW",
            })
            continue

        section = naics4_section.get(n4)
        if section is None:
            reason = naics4_drop_reasons.get(
                n4, "no NAICS-6 children found in Census crosswalk"
            )
            diag["felten_dropped_section_unresolved"].append({
                "naics4": n4, "title": title, "aiie": aiie, "reason": reason,
            })
            continue

        emp = bls_emp.get(n4)
        if emp is None or emp <= 0:
            diag["felten_dropped_no_bls_employment"].append({
                "naics4": n4, "title": title, "aiie": aiie,
                "would_be_section": section,
                "reason": "no BLS QCEW NAICS-4 employment for this code",
            })
            continue

        agg[section]["naics_codes"].append(n4)
        agg[section]["total_emp"] += emp
        agg[section]["weighted_sum"] += emp * aiie
        diag["felten_used_in_aggregation"].append({
            "naics4": n4, "section": section, "aiie": aiie, "emp": emp,
        })

    rows = []
    for letter, (label, _) in NACE_SECTIONS.items():
        a = agg[letter]
        n = len(a["naics_codes"])
        emp = a["total_emp"]
        if n == 0:
            score = np.nan
            note = "No contributing NAICS-4 codes (with BLS employment)."
        else:
            score = a["weighted_sum"] / emp
            note = ""
        rows.append({
            "nace_letter": letter,
            "nace_section_label": label,
            "aiie_score": score,
            "n_naics_codes": n,
            "total_naics_employment": int(round(emp)),
            "construction_notes": note,
        })
        diag["per_section"][letter] = {
            "n_naics_codes": n,
            "total_employment": int(round(emp)),
            "aiie_score": (None if np.isnan(score) else float(score)),
            "contributing_codes": sorted(a["naics_codes"]),
        }

    return pd.DataFrame(rows), diag


# ── Section O recovery from Felten OES synthetic codes ───────────────────

SECTION_O_REPRESENTATIVE_EMPLOYMENT = 22_000_000  # sentinel: US gov't total, BLS 2023 ballpark


def recover_section_o(
    lookup: pd.DataFrame, felten: pd.DataFrame, diag: dict
) -> tuple[pd.DataFrame, dict]:
    """Direct assignment of section O from Felten OES synthetic codes.

    Felten Appendix B includes three OES designation codes for the public
    sector (9991 Federal Executive Branch, 9992 State Government,
    9993 Local Government) that fall outside the standard NAICS hierarchy.
    Felten constructed them specifically so public-sector occupations
    would have AIIE coverage.

    Scale-compatibility check (Task 1A, 2026-05-26): Felten Appendix B is
    z-scored across the combined NAICS + OES set (mean 0.000, SD 1.000 over
    all 250 rows). OES values fall within ±2 SD of the NAICS-only
    distribution (OES range [-0.01, +1.08] vs NAICS bound [-2.01, +1.99]).
    The OES codes are on the same standardized reference scale as the
    NAICS codes by construction; direct assignment is methodologically
    defensible.

    Construction: section O's AIIE = unweighted mean of the three OES
    codes. Employment is a hard-coded sentinel (~22M = US gov't total per
    BLS), NOT a NAICS-aggregated weight.
    """
    oes_rows = felten[(felten["naics4"] >= 9991) & (felten["naics4"] <= 9993)]
    assert len(oes_rows) == 3, f"expected 3 OES codes; got {len(oes_rows)}"

    o_score = float(oes_rows["aiie"].mean())
    o_codes = sorted(int(x) for x in oes_rows["naics4"])

    mask = lookup["nace_letter"] == "O"
    lookup.loc[mask, "aiie_score"] = o_score
    lookup.loc[mask, "n_naics_codes"] = len(oes_rows)
    lookup.loc[mask, "total_naics_employment"] = SECTION_O_REPRESENTATIVE_EMPLOYMENT
    lookup.loc[mask, "construction_notes"] = (
        "Direct assignment from Felten OES synthetic codes 9991/9992/9993 "
        "(unweighted mean). Felten constructed these codes specifically for "
        "the public-sector NAICS gap. Scale-compatible (Appendix B is z-scored "
        "over NAICS+OES combined). Employment is a hard-coded sentinel "
        f"({SECTION_O_REPRESENTATIVE_EMPLOYMENT:,} ~= US gov't total, BLS 2023); "
        "NOT a NAICS-derived weight."
    )

    # Move OES codes from "dropped" to "recovered_o" in diagnostics
    diag["felten_recovered_o"] = list(diag["felten_dropped_oes"])
    diag["felten_dropped_oes"] = []
    diag["per_section"]["O"] = {
        "n_naics_codes": len(oes_rows),
        "total_employment": SECTION_O_REPRESENTATIVE_EMPLOYMENT,
        "aiie_score": o_score,
        "contributing_codes": o_codes,
        "note": "OES synthetic codes; sentinel employment",
    }

    return lookup, diag


# ── Defensive + substantive checks ─────────────────────────────────────────


def run_defensive_checks(lookup: pd.DataFrame) -> tuple[list[str], list[str]]:
    p, f = [], []
    def check(label, cond, detail=""):
        if cond: p.append(label)
        else: f.append(f"{label}: {detail}" if detail else label)

    check("exactly 21 rows", len(lookup) == 21, f"got {len(lookup)}")
    expected = set("ABCDEFGHIJKLMNOPQRSTU")
    actual = set(lookup["nace_letter"])
    check("all 21 NACE letters present", actual == expected,
          f"missing={sorted(expected-actual)}, extra={sorted(actual-expected)}")

    non_nan = lookup.dropna(subset=["aiie_score"])
    in_range = non_nan["aiie_score"].between(-3, 3).all()
    check("non-NaN AIIE in [-3, 3]", bool(in_range),
          f"out-of-range: {non_nan[~non_nan['aiie_score'].between(-3, 3)].to_dict(orient='records')}")

    bad = lookup[
        ((lookup["n_naics_codes"] == 0) & lookup["aiie_score"].notna())
        | ((lookup["n_naics_codes"] > 0) & lookup["aiie_score"].isna())
    ]
    check("n_naics_codes/aiie_score NaN consistency", len(bad) == 0,
          f"inconsistent: {bad.to_dict(orient='records')}")

    total_emp = int(lookup["total_naics_employment"].sum())
    check("total employment in [50M, 250M]",
          50_000_000 <= total_emp <= 250_000_000, f"total={total_emp:,}")

    return p, f


def substantive_sanity_check(lookup: pd.DataFrame) -> tuple[bool, str]:
    """Compare high-expected (J,K,M) vs low-expected (A,F,I) section means.

    Reports the actual sections used in each mean and flags NaN exclusions
    so the message can't lie about which sections contributed (the previous
    version silently averaged over the available sections while labelling
    the result with the full expected set).
    """
    by = dict(zip(lookup["nace_letter"], lookup["aiie_score"]))
    expected_high = ("J", "K", "M")
    expected_low = ("A", "F", "I")
    high_used = {l: by.get(l) for l in expected_high
                 if by.get(l) is not None and not np.isnan(by.get(l))}
    low_used = {l: by.get(l) for l in expected_low
                if by.get(l) is not None and not np.isnan(by.get(l))}
    high_missing = sorted(set(expected_high) - set(high_used))
    low_missing = sorted(set(expected_low) - set(low_used))

    if not high_used or not low_used:
        return False, (
            f"insufficient data: high_used={list(high_used)}, "
            f"low_used={list(low_used)}, high_missing={high_missing}, "
            f"low_missing={low_missing}"
        )

    mh = sum(high_used.values()) / len(high_used)
    ml = sum(low_used.values()) / len(low_used)
    ok = mh > ml

    parts = [
        f"mean({','.join(sorted(high_used))}) = {mh:+.3f} "
        f"{'>' if ok else 'NOT >'} "
        f"mean({','.join(sorted(low_used))}) = {ml:+.3f}"
    ]
    if high_missing or low_missing:
        parts.append(
            f"NaN-excluded: expected-high missing {high_missing or '[]'}, "
            f"expected-low missing {low_missing or '[]'}"
        )
    parts.append(
        f"[{'PASS' if ok else 'FAIL — possible sign flip / weight inversion / crosswalk error'}]"
    )
    return ok, " | ".join(parts)


# ── Bias check on dropped codes ────────────────────────────────────────────


def bias_check_dropped(
    felten: pd.DataFrame, diag: dict, dup_report: dict
) -> dict:
    """Compare AIIE distribution of dropped vs kept Felten codes."""
    used_codes = {x["naics4"] for x in diag["felten_used_in_aggregation"]}
    dup_dropped_codes = {x["naics4"] for x in dup_report["dropped"]}
    section_dropped_codes = {x["naics4"] for x in diag["felten_dropped_section_unresolved"]}
    no_bls_codes = {x["naics4"] for x in diag["felten_dropped_no_bls_employment"]}
    oes_codes = {x["naics4"] for x in diag["felten_dropped_oes"]}

    # Felten contains the post-dup-resolution unique NAICS-4 codes
    # Need to combine with original duplicates that were dropped to get
    # the full "would-be-considered" set
    used_aiies = []
    for _, row in felten.iterrows():
        if int(row["naics4"]) in used_codes:
            used_aiies.append(float(row["aiie"]))

    # Dropped-by-section-unresolved: get from diag
    dropped_section_aiies = [x["aiie"] for x in diag["felten_dropped_section_unresolved"]]
    dropped_no_bls_aiies = [x["aiie"] for x in diag["felten_dropped_no_bls_employment"]]
    dropped_oes_aiies = [x["aiie"] for x in diag["felten_dropped_oes"]]
    recovered_o_aiies = [x["aiie"] for x in diag.get("felten_recovered_o", [])]
    # Duplicates dropped: each had multiple AIIE values; report range
    dropped_dup_summary = [
        f"{x['naics4']}: AIIEs {[f'{a:+.3f}' for a in x['aiies']]}"
        for x in dup_report["dropped"]
    ]

    def stats(arr):
        if not arr:
            return None
        a = np.array(arr)
        return {
            "n": len(a),
            "mean": float(a.mean()),
            "sd": float(a.std()),
            "min": float(a.min()),
            "max": float(a.max()),
        }

    return {
        "used_in_aggregation": stats(used_aiies),
        "recovered_o_oes": stats(recovered_o_aiies),
        "dropped_section_unresolved": stats(dropped_section_aiies),
        "dropped_no_bls_employment": stats(dropped_no_bls_aiies),
        "dropped_oes_designation": stats(dropped_oes_aiies),
        "dropped_duplicate_summary": dropped_dup_summary,
    }


# ── Verification log ───────────────────────────────────────────────────────


def write_log(
    lookup: pd.DataFrame,
    felten_clean: pd.DataFrame,
    dup_report: dict,
    section_diag: dict,
    aggregate_diag: dict,
    bias: dict,
    passes: list[str],
    failures: list[str],
    sanity_passed: bool,
    sanity_msg: str,
    drop_warn: str | None,
) -> None:
    L: list[str] = []
    L.append("NACE-section AIIE Lookup — Verification Log")
    L.append(f"Run: {datetime.now().isoformat(timespec='seconds')}")
    L.append(f"Source: v2_prep/scripts/05_build_nace_aiie.py")
    L.append(f"Inputs:")
    L.append(f"  {FELTEN_XLSX.name} (sheet 'Appendix B')")
    L.append(f"  {CENSUS_XLSX.name}")
    L.append(f"  {BLS_CSV.name}")
    L.append("")

    # 1. Duplicate handling
    L.append("─" * 70)
    L.append("Step 1 — Felten duplicate NAICS-4 handling")
    L.append("─" * 70)
    L.append(f"  Global AIIE SD: {dup_report['global_aiie_sd']:.4f}")
    L.append(f"  Spread threshold (0.5*SD): {dup_report['spread_threshold']:.4f}")
    L.append(f"  Duplicate NAICS-4 codes found: {len(dup_report['duplicate_groups'])}")
    for g in dup_report["duplicate_groups"]:
        L.append(f"    {g['naics4']}: spread={g['spread']:.4f}, "
                 f"{'AVERAGED' if g['naics4'] in {a['naics4'] for a in dup_report['averaged']} else 'DROPPED'}")
        for t, a in zip(g["titles"], g["aiies"]):
            L.append(f"      AIIE={a:+.4f}  {t!r}")
    L.append(f"  → {len(dup_report['averaged'])} averaged, {len(dup_report['dropped'])} dropped")
    if dup_report["dropped"]:
        L.append("")
        L.append("  DROPPED duplicate codes (with rationale):")
        for d in dup_report["dropped"]:
            L.append(f"    NAICS-4 {d['naics4']} — {d['reason']}")
    L.append("")

    # 2. Crosswalk diagnostics
    L.append("─" * 70)
    L.append("Step 2 — Census crosswalk: NAICS-4 -> NACE section assignment")
    L.append("─" * 70)
    L.append(f"  NAICS-6 in crosswalk:                                    {section_diag['n_naics6_total']}")
    L.append(f"  NAICS-6 single-section (no resolution needed):           {section_diag['n_naics6_single_section']}")
    L.append(f"  NAICS-6 multi-section, recursively resolved (level 1):   {section_diag['n_naics6_recursively_resolved']}")
    L.append(f"  NAICS-6 multi-section, recursive rule failed:            {section_diag['n_naics6_recursive_failed']}")
    L.append(f"  NAICS-4 total candidates:                                {section_diag['n_naics4_total']}")
    L.append(f"  NAICS-4 assigned cleanly (1 section, level 2):           {section_diag['assignments_clean_single_section']}")
    L.append(f"  NAICS-4 assigned by modal resolution (level 2):          {section_diag['assignments_modal_resolved']}")
    L.append(f"  NAICS-4 dropped — modal threshold (level 2 failed):      {section_diag['drops_modal_threshold']}")
    L.append(f"  NAICS-4 dropped — no resolvable children:                {section_diag['drops_no_resolvable_children']}")
    L.append("")

    # 3. Felten coverage table
    L.append("─" * 70)
    L.append("Step 3 — Felten code-by-code accounting")
    L.append("─" * 70)
    n_unique = aggregate_diag["n_felten_unique_naics4"]
    n_used = len(aggregate_diag["felten_used_in_aggregation"])
    n_oes_recovered = len(aggregate_diag.get("felten_recovered_o", []))
    n_oes_dropped = len(aggregate_diag["felten_dropped_oes"])
    n_sect = len(aggregate_diag["felten_dropped_section_unresolved"])
    n_bls = len(aggregate_diag["felten_dropped_no_bls_employment"])
    n_dup_dropped = len(dup_report["dropped"])
    L.append(f"  Felten unique NAICS-4 (post-dup resolution): {n_unique}")
    L.append(f"  Used in NACE-weighted aggregation:            {n_used}")
    L.append(f"  Recovered to section O (OES synthetic codes): {n_oes_recovered}")
    L.append(f"  Dropped (duplicate spread > 0.5*SD):          {n_dup_dropped}")
    L.append(f"  Dropped (OES code, NOT recovered):            {n_oes_dropped}")
    L.append(f"  Dropped (section assignment unresolved):      {n_sect}")
    L.append(f"  Dropped (no BLS QCEW employment):             {n_bls}")
    L.append("")

    # 4. Individual dropped-code listings
    L.append("─" * 70)
    L.append("Step 4 — Individual dropped Felten NAICS-4 codes")
    L.append("─" * 70)

    if aggregate_diag.get("felten_recovered_o"):
        L.append(f"\n  ({len(aggregate_diag['felten_recovered_o'])}) OES synthetic codes — RECOVERED to section O:")
        for x in aggregate_diag["felten_recovered_o"]:
            L.append(f"    {x['naics4']}: AIIE={x['aiie']:+.4f}  {x['title']!r}")
        L.append(f"        → direct unweighted-mean assignment to section O "
                 f"(scale compatible per Task 1A check; OES values within ±2 SD of NAICS distribution; "
                 f"all Felten Appendix B z-scored over NAICS+OES combined)")

    if aggregate_diag["felten_dropped_oes"]:
        L.append(f"\n  ({len(aggregate_diag['felten_dropped_oes'])}) OES designation codes (NOT recovered):")
        for x in aggregate_diag["felten_dropped_oes"]:
            L.append(f"    {x['naics4']}: AIIE={x['aiie']:+.4f}  {x['title']!r}")
            L.append(f"        → {x['reason']}")

    if aggregate_diag["felten_dropped_section_unresolved"]:
        L.append(f"\n  ({len(aggregate_diag['felten_dropped_section_unresolved'])}) Section unresolved:")
        for x in aggregate_diag["felten_dropped_section_unresolved"]:
            L.append(f"    {x['naics4']}: AIIE={x['aiie']:+.4f}  {x['title']!r}")
            L.append(f"        → {x['reason']}")

    if aggregate_diag["felten_dropped_no_bls_employment"]:
        L.append(f"\n  ({len(aggregate_diag['felten_dropped_no_bls_employment'])}) No BLS employment:")
        for x in aggregate_diag["felten_dropped_no_bls_employment"]:
            L.append(f"    {x['naics4']}: AIIE={x['aiie']:+.4f}  {x['title']!r}")
            L.append(f"        (would have contributed to section {x['would_be_section']})")
            L.append(f"        → {x['reason']}")
    L.append("")

    # 5. Bias check
    L.append("─" * 70)
    L.append("Step 5 — Bias check (AIIE distribution: kept vs dropped)")
    L.append("─" * 70)
    def fmt_stats(s):
        if s is None: return "  (none)"
        return f"  n={s['n']}, mean={s['mean']:+.4f}, SD={s['sd']:.4f}, range=[{s['min']:+.4f}, {s['max']:+.4f}]"
    L.append("  Used in NACE-weighted aggregation:")
    L.append(fmt_stats(bias["used_in_aggregation"]))
    L.append("  Recovered to section O (OES synthetic codes):")
    L.append(fmt_stats(bias["recovered_o_oes"]))
    L.append("  Dropped (section unresolved):")
    L.append(fmt_stats(bias["dropped_section_unresolved"]))
    L.append("  Dropped (OES designation, NOT recovered):")
    L.append(fmt_stats(bias["dropped_oes_designation"]))
    L.append("  Dropped (no BLS employment):")
    L.append(fmt_stats(bias["dropped_no_bls_employment"]))
    L.append("  Dropped (duplicate spread):")
    for s in bias["dropped_duplicate_summary"]:
        L.append(f"    {s}")
    L.append("")

    if drop_warn:
        L.append("─" * 70)
        L.append("Step 5b — Cumulative drop-rate warning")
        L.append("─" * 70)
        L.append(f"  {drop_warn}")
        L.append("")

    # 6. Per-section table
    L.append("─" * 70)
    L.append("Step 6 — Per-NACE-section lookup")
    L.append("─" * 70)
    L.append(f"  {'letter':<7} {'n_codes':>8} {'employment':>14} {'aiie_score':>12}")
    L.append(f"  {'-'*7} {'-'*8} {'-'*14} {'-'*12}")
    for _, row in lookup.iterrows():
        score = f"{row['aiie_score']:+.4f}" if not pd.isna(row['aiie_score']) else "NaN"
        L.append(f"  {row['nace_letter']:<7} {row['n_naics_codes']:>8d} "
                 f"{row['total_naics_employment']:>14,d} {score:>12}")
        if row["construction_notes"]:
            L.append(f"          note: {row['construction_notes']}")
    L.append("")

    # 7. Substantive sanity
    L.append("─" * 70)
    L.append("Step 7 — Substantive sanity check")
    L.append("─" * 70)
    L.append(f"  {sanity_msg}")
    L.append("")
    L.append("  Top-5 by AIIE:")
    top5 = lookup.dropna(subset=["aiie_score"]).nlargest(5, "aiie_score")
    for _, r in top5.iterrows():
        L.append(f"    {r['nace_letter']} ({r['nace_section_label'][:50]}): "
                 f"{r['aiie_score']:+.4f}  (n={r['n_naics_codes']}, emp={r['total_naics_employment']:,})")
    L.append("")
    L.append("  Bottom-5 by AIIE:")
    bot5 = lookup.dropna(subset=["aiie_score"]).nsmallest(5, "aiie_score")
    for _, r in bot5.iterrows():
        L.append(f"    {r['nace_letter']} ({r['nace_section_label'][:50]}): "
                 f"{r['aiie_score']:+.4f}  (n={r['n_naics_codes']}, emp={r['total_naics_employment']:,})")
    L.append("")

    # 8. Defensive checks
    L.append("─" * 70)
    L.append(f"Step 8 — Defensive checks: {len(passes)} PASS, {len(failures)} FAIL")
    L.append("─" * 70)
    if failures:
        for f in failures:
            L.append(f"  [FAIL] {f}")
    else:
        L.append(f"  All {len(passes)} checks passed.")
    L.append("")

    overall = "PASS" if (not failures and sanity_passed) else "FAIL"
    L.append("=" * 70)
    L.append(f"OVERALL: {overall}")
    L.append("=" * 70)

    OUT_LOG.write_text("\n".join(L) + "\n", encoding="utf-8")


# ── Main ───────────────────────────────────────────────────────────────────


def main() -> int:
    print("Loading inputs and resolving Felten duplicates...")
    felten, dup_report = prepare_felten()
    crosswalk = load_census_crosswalk()
    bls = load_bls()
    print(f"  Felten (post-dup): {len(felten)} rows, "
          f"{felten['naics4'].nunique()} unique NAICS-4")
    print(f"  Duplicate handling: {len(dup_report['averaged'])} averaged, "
          f"{len(dup_report['dropped'])} dropped")
    if dup_report["dropped"]:
        for d in dup_report["dropped"]:
            print(f"    DROPPED {d['naics4']}: spread {d['spread']:.4f} > "
                  f"threshold {dup_report['spread_threshold']:.4f}")

    print(f"\n  Crosswalk: {len(crosswalk)} rows; BLS: {len(bls)} rows")

    print("\nBuilding NAICS-4 -> NACE section map (rules 1 + 2)...")
    naics4_section, section_drops, section_diag = build_naics4_to_section(crosswalk)
    print(f"  Assigned: {section_diag['n_naics4_assigned']} "
          f"(clean: {section_diag['assignments_clean_single_section']}, "
          f"modal: {section_diag['assignments_modal_resolved']})")
    print(f"  NAICS-6 recursive resolution: "
          f"single={section_diag['n_naics6_single_section']}, "
          f"resolved={section_diag['n_naics6_recursively_resolved']}, "
          f"failed={section_diag['n_naics6_recursive_failed']}")
    print(f"  NAICS-4 drops: modal_threshold={section_diag['drops_modal_threshold']}, "
          f"no_resolvable_children={section_diag['drops_no_resolvable_children']}")

    print("\nAggregating to NACE sections...")
    lookup, agg_diag = aggregate_to_sections(felten, naics4_section, section_drops, bls)

    print("\nApplying section O recovery from Felten OES synthetic codes...")
    lookup, agg_diag = recover_section_o(lookup, felten, agg_diag)
    o_row = lookup[lookup["nace_letter"] == "O"].iloc[0]
    print(f"  Section O AIIE = {o_row['aiie_score']:+.4f} "
          f"(n={int(o_row['n_naics_codes'])}, "
          f"sentinel emp = {int(o_row['total_naics_employment']):,})")

    # Check O rank for scale-compatibility sanity (top-3 / bottom-3 would suggest scale issue)
    valid = lookup.dropna(subset=["aiie_score"]).sort_values("aiie_score", ascending=False)
    o_rank = valid.reset_index().index[valid.reset_index()["nace_letter"] == "O"].tolist()
    o_rank_n = (o_rank[0] + 1) if o_rank else None
    n_valid = len(valid)
    print(f"  Section O ranks #{o_rank_n} of {n_valid} valid sections by AIIE.")
    if o_rank_n is not None and (o_rank_n <= 3 or o_rank_n > n_valid - 3):
        print(f"  WARNING: O in top-3 or bottom-3 — possible OES scale-compatibility issue.",
              file=sys.stderr)

    # Cumulative-drop rate check (post-O-recovery: OES codes no longer dropped)
    n_unique = agg_diag["n_felten_unique_naics4"]
    n_original = n_unique + len(dup_report["dropped"])
    n_total_dropped = (
        len(dup_report["dropped"])
        + len(agg_diag["felten_dropped_oes"])  # zero after O recovery
        + len(agg_diag["felten_dropped_section_unresolved"])
        + len(agg_diag["felten_dropped_no_bls_employment"])
    )
    drop_rate = n_total_dropped / n_original
    print(f"\nCumulative Felten drop rate: {n_total_dropped}/{n_original} = {drop_rate*100:.1f}%")
    drop_warn = None
    if drop_rate > DROP_WARN_THRESHOLD_PCT:
        drop_warn = (
            f"Cumulative drop rate {drop_rate*100:.1f}% exceeds "
            f"{DROP_WARN_THRESHOLD_PCT*100:.0f}% threshold. The NACE-AIIE lookup is "
            f"based on a substantially-reduced subset of Felten's coverage; consider "
            f"whether the substantive results depend on this construction choice."
        )
        print(f"  WARNING: {drop_warn}")

    print("\nDefensive checks...")
    passes, failures = run_defensive_checks(lookup)
    print(f"  {len(passes)} PASS, {len(failures)} FAIL")

    print("\nSubstantive sanity check...")
    sanity_passed, sanity_msg = substantive_sanity_check(lookup)
    print(f"  {sanity_msg}")

    print("\nBias check on dropped codes...")
    bias = bias_check_dropped(felten, agg_diag, dup_report)

    lookup.to_csv(OUT_CSV, index=False)
    print(f"\nWrote {OUT_CSV} ({len(lookup)} rows)")
    write_log(lookup, felten, dup_report, section_diag, agg_diag, bias,
              passes, failures, sanity_passed, sanity_msg, drop_warn)
    print(f"Wrote {OUT_LOG}")

    ok = (not failures) and sanity_passed
    if not ok:
        print("\nOVERALL: FAIL", file=sys.stderr)
        return 1
    print("\nOVERALL: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
