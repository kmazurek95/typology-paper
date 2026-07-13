"""
14_manuscript_tables.py — regenerate manuscript tables from persisted output CSVs.

Writes markdown tables to v2_prep/manuscript/tables/{T2..T7,TA2,TA3}.md and runs a
value-level verification against the canonical draft:
  - T6 Panel B: every value checked against m7_rs_diagnostic.csv (STOP-worthy).
  - T3/T4/T5/T7/TA3: cell-by-cell numeric diff-check vs the draft (expect 0 mismatches).
No new analysis; formatting/extraction only. Does NOT modify the draft (injection is a
separate step) and does NOT commit.
"""
import re
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT  = ROOT / "v2_prep" / "output"
PROC = ROOT / "v2_prep" / "data" / "processed"
MAN  = ROOT / "v2_prep" / "manuscript"
TBL  = MAN / "tables"; TBL.mkdir(parents=True, exist_ok=True)
DRAFT = MAN / "Mazurek_2026_canonical_draft.md"

def rd(name, base=OUT): return pd.read_csv(base / name)

# ---- formatting helpers -----------------------------------------------------
def stars(p):
    return "***" if p < .001 else "**" if p < .01 else "*" if p < .05 else ""
def es(est, se, dp, star=None):            # "-0.014 (0.004)***"
    s = f"{est:.{dp}f} ({se:.{dp}f})"
    return s + (stars(star) if star is not None else "")
def sgn(x, dp): return f"{x:+.{dp}f}"
def pct(x): return f"{x*100:.1f}"
def N(x): return f"{int(round(x)):,}"
def p3(p): return f"{p:.3f}"
def psci(p): return f"{p:.1e}"
def p_auto(p): return psci(p) if p < .001 else p3(p)          # T5/T6 2024-slope
def p_t7(p): return "<.001" if p < .001 else f"{p:.3f}"
def pdot(p):                                                   # ".101" leading-dot
    return re.sub(r"^0", "", p_auto(p)) if p >= .001 else psci(p)

def md(header_cells, rows):
    h = "| " + " | ".join(header_cells) + " |"
    sep = "|" + "|".join(["---"] * len(header_cells)) + "|"
    body = "\n".join("| " + " | ".join(r) + " |" for r in rows)
    return h + "\n" + sep + "\n" + body + "\n"

# ---- source frames ----------------------------------------------------------
t2  = rd("table2_descriptives.csv")
cr  = rd("coef_table_RD.csv"); cs = rd("coef_table_SI.csv")
mmr = rd("model_meta_RD.csv"); mms = rd("model_meta_SI.csv")
hi  = rd("headline_inference_M4.csv")
b24 = rd("batch_2024slope.csv")
di  = rd("dropitem_did.csv")
rob = rd("robustness_coefs.csv")
m7  = rd("m7_rs_diagnostic.csv")
nace = rd("nace_aiie_lookup.csv", PROC)
typ  = rd("typology_positions.csv", ROOT / "data" / "processed")
fr   = rd("frame_rosters.csv")

def t2v(frame, wave, var, stat):
    m = t2[(t2.frame==frame)&(t2.wave==wave)&(t2.variable==var)&(t2.statistic==stat)]
    return float(m.value.iloc[0])
def coef(tbl, model, term):
    m = tbl[(tbl.model==model)&(tbl.term==term)]
    r = m.iloc[0]; return float(r.estimate), float(r.se), float(r.p)
def meta(tbl, model, col):
    return float(tbl[tbl.model==model][col].iloc[0])

# ============================================================ T2 =============
def build_T2():
    waves = ["2022","2024","pooled"]
    def row_scale(frame, var):  # mean (SD)
        return [f"{t2v(frame,w,var,'mean'):.2f} ({t2v(frame,w,var,'sd'):.2f})" for w in waves]
    def row_share(var):         # RD frame, %
        return [pct(t2v('RD',w,var,'share')) for w in waves]
    rows = [
        ["Redistribution scale, mean (SD)"] + row_scale('RD','RD_scale'),
        ["Social-investment scale, mean (SD)"] + row_scale('SI','SI_scale'),
        ["AI exposure (AIIE, raw), mean (SD)"] + row_scale('RD','aiie_score'),
        ["Education: low share (%)"] + row_share('edu2_low'),
        ["Female (%)"] + row_share('sex2_female'),
        ["Income decile, median"] + [f"{t2v('RD',w,'income_decile','median'):.0f}" for w in waves],
        ["Standard employment (%)"] + row_share('stdworker_Standard'),
        ["Non-standard employment (%)"] + row_share('stdworker_NonStandard'),
        ["Not employed (%)"] + row_share('stdworker_NotEmployed'),
        ["N (redistribution frame)"] + [N(t2v('RD',w,'RD_scale','n')) for w in waves],
        ["N (social-investment frame)"] + [N(t2v('SI',w,'SI_scale','n')) for w in waves],
    ]
    note = ("*Note:* Covariate rows on the redistribution frame; the social-investment "
            "frame differs by <450 respondents. Scales are respondent means of three "
            "five-point items (Section 3.2).")
    return "**Table 2. Sample descriptives (M4 analysis frames, by wave).**\n\n" + \
           md(["", "2022", "2024", "Pooled"], rows) + "\n" + note + "\n"

# ============================================================ T3 =============
def build_T3():
    def cell(tbl, m, term, dp=3):
        try: e,s,p = coef(tbl, m, term); return es(e,s,dp,p)
        except IndexError: return "—"
    def cellmeta(tbl, m, col, dp):
        v = meta(tbl, m, col)
        return "—" if pd.isna(v) else f"{v:.{dp}f}"
    R=lambda lbl, terms: [lbl] + terms
    rows = [
        R("Exposure (AIIE, cwc)", [cell(cr,"M1_RD","aiie_cwc"), cell(cr,"M4_RD","aiie_cwc"),
                                    cell(cs,"M1_SI","aiie_cwc"), cell(cs,"M4_SI","aiie_cwc")]),
        R("Task-profile axis", ["—", cell(cr,"M4_RD","z_task_profile"), "—", cell(cs,"M4_SI","z_task_profile")]),
        R("Dualization axis", ["—", cell(cr,"M4_RD","z_dualization"), "—", cell(cs,"M4_SI","z_dualization")]),
        R("GDP per capita (std.)", ["—", cell(cr,"M4_RD","gdp_z"), "—", cell(cs,"M4_SI","gdp_z")]),
        R("Exposure × Task", ["—", cell(cr,"M4_RD","aiie_cwc:z_task_profile"), "—", cell(cs,"M4_SI","aiie_cwc:z_task_profile")]),
        R("Exposure × Dualization", ["—", cell(cr,"M4_RD","aiie_cwc:z_dualization"), "—", cell(cs,"M4_SI","aiie_cwc:z_dualization")]),
        R("Task × Dualization", ["—", cell(cr,"M4_RD","z_task_profile:z_dualization"), "—", cell(cs,"M4_SI","z_task_profile:z_dualization")]),
        R("Country intercept var. (τ00)", [cellmeta(mmr,"M1_RD","tau00",4), cellmeta(mmr,"M4_RD","tau00",4),
                                            cellmeta(mms,"M1_SI","tau00",4), cellmeta(mms,"M4_SI","tau00",4)]),
        R("Exposure slope var. (τ11)", ["—", cellmeta(mmr,"M4_RD","tau11",5), "—", cellmeta(mms,"M4_SI","tau11",5)]),
        R("Residual var. (σ²)", [cellmeta(mmr,"M1_RD","sigma2",3), cellmeta(mmr,"M4_RD","sigma2",3),
                                  cellmeta(mms,"M1_SI","sigma2",3), cellmeta(mms,"M4_SI","sigma2",3)]),
        R("N", [N(meta(mmr,"M1_RD","n")), N(meta(mmr,"M4_RD","n")), N(meta(mms,"M1_SI","n")), N(meta(mms,"M4_SI","n"))]),
        R("Countries", [str(int(meta(mmr,"M1_RD","countries"))), str(int(meta(mmr,"M4_RD","countries"))),
                        str(int(meta(mms,"M1_SI","countries"))), str(int(meta(mms,"M4_SI","countries")))]),
    ]
    note=("*Note:* Estimates (SE); *p < .05, **p < .01, ***p < .001 (Satterthwaite). "
          "Individual controls included throughout; intermediate models and exact p-values "
          "in the replication files. Random exposure slopes from M2 onward.")
    return "**Table 3. The estimation ladder: individual-controls and headline models.**\n\n" + \
           md(["", "RD: M1", "RD: M4", "SI: M1", "SI: M4"], rows) + "\n" + note + "\n"

# ============================================================ T4 =============
def build_T4():
    lab = {"aiie_cwc:z_task_profile":"Exposure × Task", "aiie_cwc:z_dualization":"Exposure × Dualization"}
    rows=[]
    for dv in ["RD","SI"]:
        for term in ["aiie_cwc:z_task_profile","aiie_cwc:z_dualization"]:
            r = hi[(hi.dv==dv)&(hi.term==term)].iloc[0]
            rows.append([dv, lab[term], f"{r.sat_est:.4f} ({r.sat_se:.4f})", f"{r.sat_df:.1f}",
                         p3(r.sat_p), p3(r.kr_p), p3(r.cr2_p),
                         f"[{r.boot_lo:.4f}, {r.boot_hi:.4f}]"])
    note="*Note:* Satterthwaite and Kenward–Roger df; CR2 cluster-robust SEs; parametric-bootstrap percentile CIs."
    return "**Table 4. Cross-level interactions under four inference methods (M4).**\n\n" + \
           md(["DV","Term","Estimate (SE)","df","p (Satt.)","p (KR)","p (CR2)","Bootstrap 95% CI"], rows) + "\n" + note + "\n"

# ============================================================ T5 =============
def build_T5():
    er,sr,pr = coef(cr,"M5_RD","aiie_cwc"); ew,sw,pw = coef(cr,"M5_RD","wave2024"); ei,si,pi = coef(cr,"M5_RD","aiie_cwc:wave2024")
    es_,ss,ps = coef(cs,"M6_SI","aiie_cwc"); ew2,sw2,pw2 = coef(cs,"M6_SI","wave2024"); ei2,si2,pi2 = coef(cs,"M6_SI","aiie_cwc:wave2024")
    rd_ = b24[b24.dv=="RD"].iloc[0]; si_ = b24[b24.dv=="SI"].iloc[0]
    pA = md(["","Redistribution (M5)","Social investment (M6)"], [
        ["2022 exposure slope", es(er,sr,4,pr), es(es_,ss,4,ps)],
        ["Wave 2024 (main)", es(ew,sw,4,pw), es(ew2,sw2,4,pw2)],
        ["Exposure × Wave 2024", es(ei,si,4,pi), es(ei2,si2,4,pi2)],
        ["2024 exposure slope (tested)",
         f"{rd_.slope2024_est:.4f} ({rd_.slope2024_se:.4f}), p = {p_auto(rd_.slope2024_p)}",
         f"{si_.slope2024_est:.4f} ({si_.slope2024_se:.4f}), p = {p_auto(si_.slope2024_p)}"]])
    a = di[di.frame=="a_relist_k2"].iloc[0]; b = di[di.frame=="b_held_k1"].iloc[0]
    def dcell(r, which):
        if which=="base": return es(r.base_est, r.base_se, 4, r.base_p)
        if which=="inter": return f"{r.inter_est:.4f} ({r.inter_se:.4f}), p = {p_auto(r.inter_p)}"
        return f"{r.slope2024_est:.4f} ({r.slope2024_se:.4f}), p = {p_auto(r.slope2024_p)}"
    pB = md(["","Relist frame (k ≥ 2)","Held frame (k ≥ 1)"], [
        ["N", N(a.n), N(b.n)],
        ["2022 exposure slope", dcell(a,"base"), dcell(b,"base")],
        ["Exposure × Wave 2024", dcell(a,"inter"), dcell(b,"inter")],
        ["2024 exposure slope (tested)", dcell(a,"s24"), dcell(b,"s24")]])
    note="*Note:* 2022 is the reference wave; 2024 slopes are tested linear combinations. Cross-level terms are unchanged by the temporal terms."
    return ("**Table 5. Temporal specification and pre-committed sensitivity.**\n\n"
            "**Panel A. Full three-item scales.**\n\n" + pA +
            "\n**Panel B. Drop-item sensitivity (redistribution, two materially stable items).**\n\n" + pB +
            "\n" + note + "\n")

# ============================================================ T6 =============
def build_T6():
    m7map = {("RD","fear_lin"):"M7_RD_fear_lin", ("RD","fear_bin"):"M7_RD_fear_bin",
             ("SI","fear_lin"):"M7_SI_fear_lin", ("SI","fear_bin"):"M7_SI_fear_bin"}
    def pa_cell(dv, fear, key):
        tbl = cr if dv=="RD" else cs; m = m7map[(dv,fear)]
        term = f"z_dualization:{fear}" if key=="focal" else f"socx_z:{fear}"
        e,s,p = coef(tbl, m, term); return es(e,s,4,p)
    cols = [("RD","fear_lin"),("RD","fear_bin"),("SI","fear_lin"),("SI","fear_bin")]
    pA = md(["","RD, linear","RD, binary","SI, linear","SI, binary"], [
        ["Dualization × Fear (focal)"] + [pa_cell(dv,f,"focal") for dv,f in cols],
        ["Expenditure × Fear (competing)"] + [pa_cell(dv,f,"competing") for dv,f in cols]])
    def pb_cell(dv, fear, role):
        r = m7[(m7.dv==dv)&(m7.fear_coding==fear)&(m7.role==role)].iloc[0]
        return f"{r.est:.4f} ({r.se:.4f}), p = {pdot(r.p)}"
    pB = md(["","RD, linear","RD, binary","SI, linear","SI, binary"], [
        ["Dualization × Fear (focal)"] + [pb_cell(dv,f,"focal") for dv,f in cols],
        ["Expenditure × Fear (competing)"] + [pb_cell(dv,f,"competing") for dv,f in cols]])
    # fear-slope SDs (linear coding) + mean SE inflation
    sd_rd = m7[(m7.dv=="RD")&(m7.fear_coding=="fear_lin")].fear_slope_sd.iloc[0]
    sd_si = m7[(m7.dv=="SI")&(m7.fear_coding=="fear_lin")].fear_slope_sd.iloc[0]
    mean_infl = m7.se_inflation.mean()
    note=(f"*Fear-slope SD (linear coding):* {sd_rd:.3f} (RD), {sd_si:.3f} (SI); "
          f"*mean SE inflation vs Panel A:* {mean_infl:.2f}×; all refits non-singular, 23 countries.")
    return ("**Table 6. The fear cross-section, paired reporting (2024 only).**\n\n"
            "**Panel A. Random-intercept fits (within-country df ≈ 17,600–17,800).**\n\n" + pA +
            "\n**Panel B. Random-fear-slope diagnostic (between-country df ≈ 20) (m7_rs_diagnostic.csv).**\n\n" + pB +
            "\n" + note + "\n")

# ============================================================ T7 =============
T7_ORDER = [
    ("M5w_cond","Weighted dualization gap (cond.)","RD"),
    ("M5w_uncond","Weighted dualization gap (uncond.)","RD"),
    ("M6w_cond","Weighted dualization gap (cond.)","SI"),
    ("M6w_uncond","Weighted dualization gap (uncond.)","SI"),
    ("welfare_SOCX_RD","+ Social expenditure (SOCX)","RD"),
    ("welfare_SOCX_SI","+ Social expenditure (SOCX)","SI"),
    ("welfare_CWEP_RD","+ CWEP generosity","RD"),
    ("welfare_CWEP_SI","+ CWEP generosity","SI"),
    ("WeMix_RD","Design weights (pseudo-ML)","RD"),
    ("WeMix_SI","Design weights (pseudo-ML)","SI"),
    ("RD WTP q19d+e","RD WTP q19d+e","RD_wtp"),
    ("RD single-item q20","RD single-item q20","RD_single"),
    ("SI WTP q19b+c","SI WTP q19b+c","SI_wtp"),
    ("SI single q42a [C7 scale-component]","SI single q42a [C7 scale-component]","SI_single"),
]
def build_T7():
    rows=[]
    for rl, disp, outcome in T7_ORDER:
        sub = rob[rob.rung_label==rl]
        a = sub[sub.term=="aiie_cwc"].iloc[0]
        spec = "Random intercept (fallback)" if bool(a.fallback) else "Random slope"
        rows.append([disp, outcome, N(a.n), str(int(a.countries)), spec,
                     f"{a.est:.4f} ({a.se:.4f})", p_t7(a.p)])
    note=("*Note:* Full per-term estimates per rung in the replication files. Cross-level "
          "interactions remain null in every rung (largest |estimate| = 0.008; smallest p = .069). "
          "Willingness-to-pay outcomes use a different response metric; magnitudes are not comparable across constructions.")
    return "**Table 7. Robustness: the focal exposure coefficient across fourteen rungs.**\n\n" + \
           md(["Rung","Outcome","N","Ctry","Specification","Exposure est (SE)","p"], rows) + "\n" + note + "\n"

# ============================================================ TA2 ============
def build_TA2():
    d = nace.copy()
    d["score"] = pd.to_numeric(d["aiie_score"], errors="coerce")
    d = d.sort_values("score", ascending=False, na_position="last")
    rows = [[r.nace_letter, str(r.nace_section_label),
             ("—" if pd.isna(r.score) else f"{r.score:+.2f}")] for r in d.itertuples()]
    note="*Note:* Employment-weighted section means from Felten NAICS-4 scores (Section A.2). Sections L, T, U have no contributing NAICS-4 codes with BLS employment."
    return "**Table A2. NACE-section AI Industry Exposure lookup (21 sections).**\n\n" + \
           md(["NACE","Section","AIIE score"], rows) + "\n" + note + "\n"

# ============================================================ TA3 ============
def build_TA3():
    med_t = typ.z_task_profile.median(); med_d = typ.z_dualization.median()
    frame_set = set(fr.country)
    qmap = {(True,True):"complementary/deep",(True,False):"complementary/narrow",
            (False,False):"displacement/narrow",(False,True):"displacement/deep"}
    rows=[]
    for r in typ.sort_values("country_iso3").itertuples():
        infr = r.country_iso3 in frame_set
        quad = qmap[(r.z_task_profile>=med_t, r.z_dualization>=med_d)]
        cfg = quad + ("" if infr else " †")
        rows.append([r.country_iso3, sgn(r.z_task_profile,2), sgn(r.z_dualization,2), cfg, "yes" if infr else "no"])
    note="† non-frame country; assignment from median splits on the 29-country base."
    return "**Table A3. Typology positions, all 29 countries.**\n\n" + \
           md(["Country","Task axis (z)","Dualization axis (z)","Configuration","In frame"], rows) + "\n" + note + "\n"

# ---- write all --------------------------------------------------------------
TABLES = {"T2":build_T2(),"T3":build_T3(),"T4":build_T4(),"T5":build_T5(),
          "T6":build_T6(),"T7":build_T7(),"TA2":build_TA2(),"TA3":build_TA3()}
for name, content in TABLES.items():
    (TBL / f"{name}.md").write_text(content, encoding="utf-8")
    print(f"wrote tables/{name}.md")

# ============================================================ VERIFY =========
NUM = re.compile(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?")
def nums(cell): return [float(x) for x in NUM.findall(cell.replace(",",""))]
def close(a,b): return abs(a-b) <= max(2e-2*abs(a), 5e-4)

def extract_table(text, header_substr):
    """First contiguous |-table appearing at/after header_substr, minus separator row."""
    lines = text.splitlines()
    i = next(k for k,l in enumerate(lines) if header_substr in l)
    tbl=[]
    for l in lines[i:]:
        if l.strip().startswith("|"):
            cells=[c.strip() for c in l.strip().strip("|").split("|")]
            if not set("".join(cells)) <= set("-: "): tbl.append(cells)   # skip separator
        elif tbl: break
    return tbl

DRAFT_TXT = DRAFT.read_text(encoding="utf-8")
print("\n================ VERIFICATION ================")
mismatches=[]
def diffcheck(name, header, gen_md):
    """Positional cell-by-cell compare (row order is identical by construction)."""
    doc = extract_table(DRAFT_TXT, header); gen = extract_table(gen_md, header)
    n_ok=0; n_bad=0
    for drow, grow in zip(doc[1:], gen[1:]):                 # skip header row
        for dc, gc in zip(drow[1:], grow[1:]):
            dn, gn = nums(dc), nums(gc)
            if len(dn)!=len(gn) or not all(close(a,b) for a,b in zip(dn,gn)):
                n_bad+=1; mismatches.append(f"{name} [{drow[0]}]: doc={dc!r} gen={gc!r}")
            else: n_ok+=1
    if len(doc)-1 != len(gen)-1:
        mismatches.append(f"{name}: row count doc={len(doc)-1} gen={len(gen)-1}")
    print(f"  {name}: {n_ok} cells match, {n_bad} mismatch")

diffcheck("T3","Table 3. The estimation ladder", TABLES["T3"])
diffcheck("T4","Table 4. Cross-level interactions", TABLES["T4"])
diffcheck("T5-PanelA","Panel A. Full three-item", TABLES["T5"])
diffcheck("T5-PanelB","Panel B. Drop-item sensitivity", TABLES["T5"])
diffcheck("T7","Table 7. Robustness", TABLES["T7"])
diffcheck("TA3","Table A3", TABLES["TA3"])

# T6 Panel B: verify each documented value against the CSV directly (STOP-worthy)
print("  --- T6 Panel B vs m7_rs_diagnostic.csv ---")
docB = extract_table(DRAFT_TXT, "Panel B. Random-fear-slope diagnostic")
col_order=[("RD","fear_lin"),("RD","fear_bin"),("SI","fear_lin"),("SI","fear_bin")]
role_by_rowlabel={"Dualization × Fear (focal)":"focal","Expenditure × Fear (competing)":"competing"}
t6b_bad=0
for drow in docB[1:]:
    role = role_by_rowlabel.get(drow[0])
    if role is None: continue
    for (dv,fear), cell in zip(col_order, drow[1:]):
        r = m7[(m7.dv==dv)&(m7.fear_coding==fear)&(m7.role==role)].iloc[0]
        want = {r.est, r.p} | ({r.se} if True else set())
        got = set(nums(cell))
        # each number in the doc cell must match est, se, or p from the CSV
        for x in nums(cell):
            if not any(close(x,c) for c in (r.est, r.se, r.p)):
                t6b_bad+=1; mismatches.append(f"T6B [{drow[0]}/{dv}/{fear}]: doc value {x} not in CSV (est={r.est:.4f} se={r.se:.4f} p={r.p:.4f})")
print(f"  T6 Panel B: {t6b_bad} value mismatch(es)")
# fear-slope SD note check
print(f"  fear-slope SD (lin): RD {m7[(m7.dv=='RD')&(m7.fear_coding=='fear_lin')].fear_slope_sd.iloc[0]:.3f} "
      f"SI {m7[(m7.dv=='SI')&(m7.fear_coding=='fear_lin')].fear_slope_sd.iloc[0]:.3f}; "
      f"mean SE inflation {m7.se_inflation.mean():.2f}x")

print("\n================ RESULT ================")
if mismatches:
    print(f"*** {len(mismatches)} MISMATCH(ES) — DO NOT INJECT until resolved:")
    for m in mismatches: print("   -", m)
else:
    print("ALL CLEAR: T3/T4/T5/T7/TA3 diff-check zero mismatches; T6 Panel B verified against m7_rs_diagnostic.csv.")
