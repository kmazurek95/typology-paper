"""
Script 06: Country-level merge — L1 (RTM individuals) × L2 (country covariates)

Produces the analytic-ready dataset for Script 08 (R-side multilevel
regression). Joins the pooled RTM frame (Script 04) to:
  - per-respondent AI exposure (Felten AIIE via NACE sector; Script 05 lookup)
  - v1 typology axes + cluster (typology_positions.csv)
  - dualization gap: raw + conditional + unconditional weighted (Scripts 01b/01c)
  - welfare: SOCX excl. Old Age + Survivors, % GDP (primary); CWEP TOT_GEN (robust)
  - GDP per capita, PPP current international $ (development control)

Design memo: v2_prep/docs/script_06_design_memo.md
Decisions:   v2_measurement_decisions_log.md (#6, #14, #16, #17-corrected, #18,
             S2-amended, M, A)

Key construction notes
----------------------
- ALL 54,698 RTM rows are retained. L2 columns are NaN where a country lacks
  data (RTM-only GRC/SVN/TUR → NaN axes; Eurostat-excluded LVA/EST → NaN
  weighted gaps; etc.) so Script 08 decides drop-vs-impute. No row dropping.
- iv_nace_sector is NUMERIC (1..21 = NACE A..U; 97/99 = sentinels). Mapped to
  letters, then joined to the AIIE lookup. Sections L/T/U have NaN AIIE
  (structural Felten gaps, #15); 97/99 have no section → NaN. ~13.7% NaN AIIE.
- SOCX %GDP: the re-fetched OECD aggregated file publishes the BRANCH
  decomposition only through ~2021-2023 (none reach 2024); 2022-24 carry only
  the `_T` total. So the "excl. Old Age + Survivors" measure (= `_T − TP01`,
  TP01 = "Old age and survivors", verified = TP11+TP21) can only be computed on
  branch-detail years. Each wave therefore uses its own year if branch detail
  exists, else CARRIES FORWARD the latest branch-detail year; socx_estimated=1
  flags carry-forward. In practice most wave values are carried from ~2021,
  making this a slow-moving structural welfare control (cf. CWEP 2018 carry).
  EXPEND_SOURCE is restricted to ES10 (Public) at fetch (decision #6).
- CWEP TOT_GEN ends 2018 → carried forward to both waves (wave-invariant);
  covers 17 of 27 RTM countries.

Output
------
- v2_prep/data/processed/analytic_l1l2.parquet
"""

import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from utils import CNTRYID_TO_ISO3  # noqa: E402

V2_PROC = ROOT / "v2_prep" / "data" / "processed"
PROC = ROOT / "data" / "processed"
RAW = ROOT / "data" / "raw"

RTM = V2_PROC / "rtm_pooled_analytic.parquet"
NACE_AIIE = V2_PROC / "nace_aiie_lookup.csv"
TYPOLOGY = PROC / "typology_positions.csv"
EPL_GAP = PROC / "epl_gap.csv"
SOCX = RAW / "socx" / "oecd_socx_agg_pctgdp_es10_2026-05-29.csv"
CWEP = RAW / "cwep" / "cwep_2022-12.csv"
GDP = RAW / "worldbank_gdp_pcap_ppp_2026-05-29.csv"

OUT = V2_PROC / "analytic_l1l2.parquet"

WAVES = ("2022", "2024")
# NACE numeric (1..21) -> section letter (A..U). 97/99 sentinels -> no section.
NACE_NUM_TO_LETTER = {float(i + 1): chr(ord("A") + i) for i in range(21)}


# ── L1: per-respondent AIIE via NACE sector ─────────────────────────────────


def attach_aiie(rtm: pd.DataFrame) -> pd.DataFrame:
    lut = pd.read_csv(NACE_AIIE)[["nace_letter", "aiie_score"]]
    rtm = rtm.copy()
    rtm["nace_letter"] = rtm["iv_nace_sector"].map(NACE_NUM_TO_LETTER)  # 97/99/NaN -> NaN
    return rtm.merge(lut, on="nace_letter", how="left")


# ── L2: typology axes + cluster ─────────────────────────────────────────────


def attach_axes(df: pd.DataFrame) -> pd.DataFrame:
    typ = pd.read_csv(TYPOLOGY)[
        ["country_iso3", "z_task_profile", "z_dualization", "cluster", "cluster_label"]
    ].rename(columns={"country_iso3": "ctrcode"})
    return df.merge(typ, on="ctrcode", how="left")


# ── L2: dualization gap (wave-specific cond + uncond) ───────────────────────


def attach_gap(df: pd.DataFrame) -> pd.DataFrame:
    epl = pd.read_csv(EPL_GAP)
    need = ["country_iso3", "dualization_gap_raw",
            "dualization_gap_weighted_2022", "dualization_gap_weighted_2024",
            "dualization_gap_weighted_uncond_2022", "dualization_gap_weighted_uncond_2024"]
    missing = [c for c in need if c not in epl.columns]
    assert not missing, f"epl_gap.csv missing {missing} — run 01b and 01c first"
    epl = epl[need].rename(columns={"country_iso3": "ctrcode"})
    df = df.merge(epl, on="ctrcode", how="left")
    is22 = df["wave"] == "2022"
    df["dualization_gap_weighted_cond"] = np.where(
        is22, df["dualization_gap_weighted_2022"], df["dualization_gap_weighted_2024"])
    df["dualization_gap_weighted_uncond"] = np.where(
        is22, df["dualization_gap_weighted_uncond_2022"], df["dualization_gap_weighted_uncond_2024"])
    return df.drop(columns=["dualization_gap_weighted_2022", "dualization_gap_weighted_2024",
                            "dualization_gap_weighted_uncond_2022", "dualization_gap_weighted_uncond_2024"])


# ── L2: SOCX excl. Old Age + Survivors, % GDP (wave-specific, carry-forward) ─


def build_socx() -> pd.DataFrame:
    s = pd.read_csv(SOCX)
    assert set(s["EXPEND_SOURCE"].unique()) == {"ES10"}, "SOCX not restricted to public (ES10)"
    assert set(s["UNIT_MEASURE"].unique()) == {"PT_B1GQ"}, "SOCX not on % GDP basis"
    tot = s[s.PROGRAMME_TYPE == "_T"][["REF_AREA", "TIME_PERIOD", "OBS_VALUE"]].rename(
        columns={"OBS_VALUE": "v_total"})
    osv = s[s.PROGRAMME_TYPE == "TP01"][["REF_AREA", "TIME_PERIOD", "OBS_VALUE"]].rename(
        columns={"OBS_VALUE": "v_oldsurv"})
    # inner merge → excl computable only on years with branch detail (TP01 present)
    m = tot.merge(osv, on=["REF_AREA", "TIME_PERIOD"], how="inner")
    m["excl"] = m["v_total"] - m["v_oldsurv"]      # = branches 3-9 (TP01 = Old age + Survivors)
    rows = []
    for iso, sub in m.groupby("REF_AREA"):
        ser = sub.set_index("TIME_PERIOD")["excl"].dropna().sort_index()
        if ser.empty:
            continue
        for wave in WAVES:
            wy = int(wave)
            if wy in ser.index:
                rows.append((iso, wave, float(ser.loc[wy]), 0))           # observed at wave year
            elif (ser.index < wy).any():
                src = int(ser.index[ser.index < wy].max())
                rows.append((iso, wave, float(ser.loc[src]), 1))          # carried forward
            # else: no branch-detail year <= wave year -> omit (left join -> NaN)
    return pd.DataFrame(rows, columns=["ctrcode", "wave",
                                       "socx_excl_oldsurv_pctgdp", "socx_estimated"])


# ── L2: GDP per capita PPP (wave-specific) ──────────────────────────────────


def build_gdp() -> pd.DataFrame:
    g = pd.read_csv(GDP)  # country_iso3, year, gdp_per_capita_ppp
    out = []
    for wave in WAVES:
        sub = g[g.year == int(wave)][["country_iso3", "gdp_per_capita_ppp"]].copy()
        sub["wave"] = wave
        out.append(sub)
    return pd.concat(out, ignore_index=True).rename(columns={"country_iso3": "ctrcode"})[
        ["ctrcode", "wave", "gdp_per_capita_ppp"]]


# ── L2: CWEP TOT_GEN (latest=2018, carried forward; wave-invariant) ─────────


def build_cwep() -> pd.DataFrame:
    c = pd.read_csv(CWEP)
    c["ctrcode"] = c["ISOCODE"].map(CNTRYID_TO_ISO3)  # ISOCODE is M49 numeric
    g = c.dropna(subset=["TOT_GEN", "ctrcode"])
    latest = g.sort_values("YEAR").groupby("ctrcode").tail(1)[["ctrcode", "TOT_GEN"]]
    return latest.rename(columns={"TOT_GEN": "cwep_tot_gen"})


def main() -> int:
    print(f"Loading RTM: {RTM.name}")
    df = pd.read_parquet(RTM)
    n0 = len(df)
    print(f"  {n0:,} rows x {df.shape[1]} cols | waves: {df['wave'].value_counts().to_dict()}")

    df = attach_aiie(df)
    df = attach_axes(df)
    df = attach_gap(df)
    df = df.merge(build_socx(), on=["ctrcode", "wave"], how="left")
    df = df.merge(build_gdp(), on=["ctrcode", "wave"], how="left")
    df = df.merge(build_cwep(), on="ctrcode", how="left")

    # ── Validation ──
    fails = []

    def chk(label, cond, detail=""):
        print(f"  [{'PASS' if cond else 'FAIL'}] {label}" + (f" — {detail}" if detail else ""))
        if not cond:
            fails.append(label)

    print("\nValidation:")
    chk("row count preserved (no L1 loss)", len(df) == n0, f"{len(df)} == {n0}")
    chk("wave split unchanged",
        df["wave"].value_counts().to_dict() == {"2022": 27469, "2024": 27229},
        str(df["wave"].value_counts().to_dict()))
    nan_aiie = int(df["aiie_score"].isna().sum())
    chk("AIIE NaN ~13.7%", abs(nan_aiie / n0 - 0.137) < 0.005, f"{nan_aiie} ({nan_aiie/n0:.3%})")
    rtm_only = df[df.ctrcode.isin(["GRC", "SVN", "TUR"])]
    chk("RTM-only (GRC/SVN/TUR): NaN axes but populated raw gap",
        rtm_only["z_task_profile"].isna().all() and rtm_only["dualization_gap_raw"].notna().all())
    le = df[df.ctrcode.isin(["LVA", "EST"])]
    chk("LVA/EST: NaN cond+uncond weighted gap but populated raw gap",
        le["dualization_gap_weighted_cond"].isna().all()
        and le["dualization_gap_weighted_uncond"].isna().all()
        and le["dualization_gap_raw"].notna().all())
    # Diagnostic SOCX check (Catch 1): DEU excl-old-age-AND-survivors must be the
    # ~17.24 value (carried from 2021), NOT ~18.93 (which is old-age-only removal,
    # i.e. Survivors wrongly left in). Band [16.5, 18.0] separates the two.
    deu = df[(df.ctrcode == "DEU") & (df.wave == "2022")]["socx_excl_oldsurv_pctgdp"].iloc[0]
    chk("SOCX DEU 2022 excl-old-age+survivors in [16.5,18.0] (excludes Survivors-left-in 18.93)",
        16.5 < deu < 18.0, f"{deu:.3f}")

    print("\nL2 coverage (distinct countries with non-NaN, by column):")
    for col in ["z_task_profile", "dualization_gap_raw", "dualization_gap_weighted_cond",
                "dualization_gap_weighted_uncond", "socx_excl_oldsurv_pctgdp",
                "cwep_tot_gen", "gdp_per_capita_ppp"]:
        print(f"    {col:38} {df.loc[df[col].notna(),'ctrcode'].nunique()} countries")
    obs = int(((df["socx_estimated"] == 0)).groupby([df.ctrcode, df.wave]).any().sum())
    cf = int(((df["socx_estimated"] == 1)).groupby([df.ctrcode, df.wave]).any().sum())
    print(f"  SOCX (country,wave) cells: observed={obs}, carried-forward={cf} "
          f"(branch detail ends ~2021-2023; see notes)")

    if fails:
        print(f"\nOVERALL: FAIL ({len(fails)} checks)")
        return 1
    df.to_parquet(OUT, index=False)
    print(f"\nWrote {OUT} ({len(df):,} rows x {df.shape[1]} cols)")
    print("OVERALL: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
