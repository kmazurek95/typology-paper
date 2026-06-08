# 08_multilevel_regression.R
# =============================================================================
# Script 08 — v2 multilevel regression.
#   Part A  pooled / objective AIIE   : M0 -> M6   (typology models; entries K,L,N,O,C)
#   Part B  2024 / subjective AI-fear : M7 redescription + cleavage-shape (entries U,V,W)
#
# Design memo : v2_prep/docs/script_08_design_memo.md
# Decisions   : v2_prep/docs/v2_measurement_decisions_log.md
#               (model: K,L,N,O,C,M ; measures: R,S2,#6,#20,F,G,H,I,A,T ;
#                Script-08 scrutiny: #21 weighted∩axes=15, #22 NACE-clean,
#                #23 small-cluster inference, #24 L2 collinearity, #25 dem_age,
#                #26 education coding artifact ; Chueri: U,V,W)
#
# Inference (#23): REML; Satterthwaite (lmerTest) + Kenward-Roger (pbkrtest) df;
#   parametric-bootstrap CIs for the headline cross-level terms; clubSandwich CR2
#   cluster-robust SEs; brms partial-pooling CO-PRIMARY for the variance components.
# Weighting (C4): unweighted REML primary; WeMix pseudo-ML (L1=weight, L2=1) robustness.
# Centering (C5): AIIE group-mean-centered within country (CWC).
# Education: wave-robust BINARY Low vs (Medium+High) -- the 3-cat Medium/High
#   boundary shifts across waves (#26); NEVER pool the 3-category version.
# Age: dem_agegroup everywhere (continuous dem_age is 2024-null; #25).
# Sex: 99 ("Other/Prefer not to say", 132 rows) -> NA before factor entry.
#
# Prerequisites: run 08_packages.R first. brms (co-primary) needs Rtools45.
# =============================================================================

RUN_STAGE <- "full"   # "smoke"=M0/M1; "m0_m3"=M0->M3; "m0_m4"=+M4; "m0_m6"=+M5/M6 DiD;
                      # "partB"=2024 M7 + MNAR + cleavage; "full"=EVERYTHING (M0-M6 + Part B
                      # + robustness family + brms co-primary + output writer -> v2_prep/output).

suppressPackageStartupMessages({
  library(lme4)
  library(lmerTest)   # Satterthwaite df + p-values for lmer
})

# ---- locate the analytic frame (no hard-coded absolute path) ----------------
find_parquet <- function() {
  cand <- c("v2_prep/data/processed/analytic_l1l2.parquet",
            "data/processed/analytic_l1l2.parquet",
            "../data/processed/analytic_l1l2.parquet",
            file.path(getwd(), "v2_prep/data/processed/analytic_l1l2.parquet"))
  hit <- cand[file.exists(cand)]
  if (!length(hit)) stop("Could not find analytic_l1l2.parquet; set PARQUET manually.")
  normalizePath(hit[1])
}
PARQUET <- find_parquet()
OUTDIR  <- file.path(dirname(dirname(PARQUET)), "..", "output"); dir.create(OUTDIR, showWarnings = FALSE)

read_analytic <- function(path) {
  if (requireNamespace("arrow", quietly = TRUE))       return(as.data.frame(arrow::read_parquet(path)))
  if (requireNamespace("nanoparquet", quietly = TRUE)) return(as.data.frame(nanoparquet::read_parquet(path)))
  stop("Need 'arrow' or 'nanoparquet' to read parquet -- run 08_packages.R.")
}

# ---- schema guard: raw parquet columns the script READS (derived names like RD/
# edu2/aiie_cwc are created in prep() and excluded). Verified present 2026-06-01.
# M0/M1 never touch the L2/Part-B columns, so this guard -- not the smoke test --
# is what catches a drifted L2 name (the bug class that hit temp_share/dem_age/etc.).
REQUIRED_COLS <- c(
  "dv_rd_benefits", "dv_rd_ubi", "dv_rd_robottax",
  "dv_si_education", "dv_si_retraining", "dv_si_infrastructure",
  "dem_education_3cat", "dem_sex", "dem_agegroup", "dem_income_decile", "iv_standard_worker",
  "ctrcode", "weight", "wave", "aiie_score",
  "z_task_profile", "z_dualization", "socx_excl_oldsurv_pctgdp", "gdp_per_capita_ppp",
  "dualization_gap_weighted_uncond", "dualization_gap_weighted_cond", "cwep_tot_gen",
  "dv_rd_taxrich_single", "dv_rd_wtp_unemployment", "dv_rd_wtp_income",
  "dv_si_wtp_education", "dv_si_wtp_employment",
  "iv_dig_job_ai", "cluster_label")

assert_columns <- function(df) {
  miss <- setdiff(REQUIRED_COLS, names(df))
  if (length(miss))
    stop("missing column(s) in analytic frame: ", paste(miss, collapse = ", "),
         "\n  -> frame does not match Script 08's expected schema (re-run Script 06?).",
         call. = FALSE)
  invisible(TRUE)
}

# ---- preparation (mirrors the verified Python prep) -------------------------
prep <- function(df) {
  scale3 <- function(d, items) {                 # row-mean DV scale, >=2 of 3 items
    M <- as.matrix(d[, items]); k <- rowSums(!is.na(M))
    out <- rowMeans(M, na.rm = TRUE); out[k < 2] <- NA_real_; out
  }
  df$RD <- scale3(df, c("dv_rd_benefits", "dv_rd_ubi", "dv_rd_robottax"))
  df$SI <- scale3(df, c("dv_si_education", "dv_si_retraining", "dv_si_infrastructure"))

  # Education: wave-robust BINARY (Low vs Medium+High); ref = MedHigh.  #26
  df$edu2 <- factor(ifelse(is.na(df$dem_education_3cat), NA,
                    ifelse(df$dem_education_3cat == 1, "Low", "MedHigh")),
                    levels = c("MedHigh", "Low"))
  # Sex: 99 -> NA, then factor.
  df$sex2 <- factor(ifelse(df$dem_sex %in% c(1, 2), df$dem_sex, NA),
                    levels = c(1, 2), labels = c("Male", "Female"))
  # Age: categorical (dem_age is 2024-null; #25).
  df$agegrp    <- factor(df$dem_agegroup)
  df$stdworker <- factor(df$iv_standard_worker, levels = c(1, 2, 3),
                         labels = c("NotEmployed", "Standard", "NonStandard"))
  df$wave      <- factor(df$wave, levels = c("2022", "2024"))

  # AIIE group-mean-centered within country (CWC) -- isolates within-country gradient.
  cm <- tapply(df$aiie_score, df$ctrcode, mean, na.rm = TRUE)
  df$aiie_cwc <- df$aiie_score - cm[as.character(df$ctrcode)]

  # L2 covariates standardized for interpretable cross-level interactions.
  df$socx_z <- as.numeric(scale(df$socx_excl_oldsurv_pctgdp))
  df$gdp_z  <- as.numeric(scale(df$gdp_per_capita_ppp))

  # Part B (2024) subjective AI-fear codings:
  df$fear_lin <- df$iv_dig_job_ai                                    # 1..4 linear (primary)
  df$fear_bin <- ifelse(df$iv_dig_job_ai >= 3, 1L,                  # dichotomized at 2/3
                 ifelse(df$iv_dig_job_ai <= 2, 0L, NA))
  # NB: 98 "Can't choose" was collapsed to NA upstream (Script 04); a midpoint-98
  # coding is NOT constructible here -> deferred (needs a Script 04 reopen, like q17).

  # Robustness DVs (entry F): single-item (q20 for RD; SI uses dv_si_education, a SCALE
  # COMPONENT -- C7 caveat, NOT independent) and WTP-binary 2-item means.
  df$RD_single <- df$dv_rd_taxrich_single
  df$SI_single <- df$dv_si_education
  wtp2 <- function(a, b) { M <- cbind(a, b); o <- rowMeans(M, na.rm = TRUE); o[rowSums(!is.na(M)) < 1] <- NA; o }
  df$RD_wtp <- wtp2(df$dv_rd_wtp_unemployment, df$dv_rd_wtp_income)
  df$SI_wtp <- wtp2(df$dv_si_wtp_education, df$dv_si_wtp_employment)
  # CWEP welfare control (SOCX robustness, #6), standardized.
  df$cwep_z <- as.numeric(scale(df$cwep_tot_gen))
  df
}

# ---- listwise sample per spec (country frame derived from data, never hard-coded)
build_sample <- function(df, dv, predictors, wave = NULL) {
  d <- if (is.null(wave)) df else df[df$wave == wave, , drop = FALSE]
  need <- c(dv, predictors, "ctrcode", "weight")
  d[stats::complete.cases(d[, need, drop = FALSE]), , drop = FALSE]
}

mk <- function(dv, rhs) stats::as.formula(paste(dv, "~", paste(rhs, collapse = " + ")))

icc_of <- function(m) {
  vc  <- as.data.frame(lme4::VarCorr(m))
  tau <- vc$vcov[vc$grp == "ctrcode" & is.na(vc$var2)][1]
  sig <- attr(lme4::VarCorr(m), "sc")^2
  tau / (tau + sig)
}
report_n <- function(d) {
  pw <- table(factor(d$wave, levels = c("2022", "2024")))
  cat(sprintf("   N rows=%d  countries=%d  per-wave: 2022=%d  2024=%d\n",
              nrow(d), length(unique(d$ctrcode)), pw["2022"], pw["2024"]))
}

L1 <- c("aiie_cwc", "edu2", "sex2", "agegrp", "dem_income_decile", "stdworker")

# =============================================================================
# PART A — pooled / objective AIIE.  Parsimony (#23): GDP-only in the maximal
# random-slope model; SOCX added as a separate rung. Singular fits fall back to
# random-intercept + CR2/bootstrap and the singularity is reported as a result.
# =============================================================================
fit_M0 <- function(df, dv) { d <- build_sample(df, dv, character(0))
  list(d = d, m = lmer(mk(dv, "(1|ctrcode)"), data = d, REML = TRUE)) }

fit_M1 <- function(df, dv) { d <- build_sample(df, dv, L1)
  list(d = d, m = lmer(mk(dv, c(L1, "(1|ctrcode)")), data = d, REML = TRUE)) }

fit_M2 <- function(df, dv) { d <- build_sample(df, dv, L1)        # + random slope on AIIE
  list(d = d, m = lmer(mk(dv, c(L1, "(1 + aiie_cwc|ctrcode)")), data = d, REML = TRUE)) }

L2_main <- c("z_task_profile", "z_dualization", "gdp_z")          # SOCX is a separate rung
fit_M3 <- function(df, dv) { d <- build_sample(df, dv, c(L1, L2_main))
  list(d = d, m = lmer(mk(dv, c(L1, L2_main, "(1 + aiie_cwc|ctrcode)")), data = d, REML = TRUE)) }

# M4 (headline): cross-level interactions gamma11/gamma12 + L2xL2 gamma03
fit_M4 <- function(df, dv) { d <- build_sample(df, dv, c(L1, L2_main))
  rhs <- c(L1, L2_main, "aiie_cwc:z_task_profile", "aiie_cwc:z_dualization",
           "z_task_profile:z_dualization", "(1 + aiie_cwc|ctrcode)")
  list(d = d, m = lmer(mk(dv, rhs), data = d, REML = TRUE)) }

# M5/M6 (temporal DiD, entry C): + wave + AIIE:wave   (M5=RD, M6=SI by dv arg)
fit_M5_6 <- function(df, dv) { d <- build_sample(df, dv, c(L1, L2_main))
  rhs <- c(L1, L2_main, "aiie_cwc:z_task_profile", "aiie_cwc:z_dualization",
           "z_task_profile:z_dualization", "wave", "aiie_cwc:wave",
           "(1 + aiie_cwc|ctrcode)")
  list(d = d, m = lmer(mk(dv, rhs), data = d, REML = TRUE)) }

# Robustness rungs (gated): SOCX-add, weighted-gap (cond/uncond; #21 N=15),
# CWEP welfare swap (N=17), single-item/WTP DVs, WeMix-weighted, grand-mean centering.
robust_specs <- function() list(
  socx_add      = c(L1, L2_main, "socx_z", "(1 + aiie_cwc|ctrcode)"),
  wgap_uncond   = c(L1, "z_task_profile", "dualization_gap_weighted_uncond", "gdp_z",
                    "aiie_cwc:z_task_profile", "aiie_cwc:dualization_gap_weighted_uncond",
                    "(1 + aiie_cwc|ctrcode)"),          # NOTE #21: this lists ~15 countries
  cwep_welfare  = c(L1, L2_main, "cwep_tot_gen", "(1 + aiie_cwc|ctrcode)")
)

# ---- small-cluster inference helpers (#23) ----------------------------------
inference_pack <- function(m, terms) {
  out <- list()
  out$satterthwaite <- summary(m)$coefficients                       # lmerTest default (per-coef PRIMARY)
  # Kenward-Roger per-coefficient df/SE (small-sample; #23). lmerTest dispatches to
  # pbkrtest internally and returns a per-coefficient table. (The earlier
  # get_Lb_ddf(m, fixef(m)) was WRONG: it passed the whole coefficient vector as a
  # single contrast L, giving df for the SUM of all coefficients, not per-coefficient.)
  out$kr <- tryCatch(summary(m, ddf = "Kenward-Roger")$coefficients, error = function(e) NA)
  if (requireNamespace("clubSandwich", quietly = TRUE))
    out$cr2 <- tryCatch(clubSandwich::coef_test(m, vcov = "CR2"), error = function(e) NA)
  out$boot <- tryCatch(confint(m, parm = terms, method = "boot", nsim = 1000,
                               boot.type = "perc"), error = function(e) NA)
  out
}
# brms co-primary (variance components) -- guarded by availability + Rtools.
fit_brms_coprimary <- function(d, dv, rhs_fixed) {
  if (!requireNamespace("brms", quietly = TRUE)) { message("brms not installed -- skipping co-primary."); return(NULL) }
  if (isFALSE(tryCatch(pkgbuild::has_build_tools(FALSE), error = function(e) FALSE))) {
    message("No C++ toolchain (Rtools45) -- brms cannot compile; skipping co-primary."); return(NULL) }
  f <- brms::bf(mk(dv, c(rhs_fixed, "(1 + aiie_cwc|ctrcode)")))
  brms::brm(f, data = d, chains = 4, cores = 4, iter = 2000, seed = 1,
            prior = brms::set_prior("normal(0,1)", class = "b"))   # weakly-informative
}

# =============================================================================
# PART B — 2024 cross-section / subjective AI-fear (entries U,V,W). EXPLORATORY.
# =============================================================================
# M7 redescription (entry V): single common moderator (AI-fear) on BOTH
# z_dualization:fear and socx_z:fear. Report drop-98 (default) vs dichotomized;
# midpoint-98 deferred (needs Script 04 reopen). 23 countries / ~17.1k rows.
fit_M7 <- function(df, dv, fear = c("fear_lin", "fear_bin")) {
  fear <- match.arg(fear)
  preds <- c("z_dualization", "socx_z", fear, L1[L1 != "aiie_cwc"])
  d <- build_sample(df, dv, c("z_dualization", "socx_z", fear,
                              "edu2", "sex2", "agegrp", "dem_income_decile", "stdworker"),
                    wave = "2024")
  rhs <- c("edu2", "sex2", "agegrp", "dem_income_decile", "stdworker",
           "z_dualization", "socx_z", fear,
           paste0("z_dualization:", fear), paste0("socx_z:", fear),
           "(1|ctrcode)")
  list(d = d, m = lmer(mk(dv, rhs), data = d, REML = TRUE))
}
# Missingness (MNAR) diagnostic for AI-fear, 2024 (retained-vs-dropped on observables).
mnar_diag <- function(df) {
  d <- df[df$wave == "2024", ]
  d$miss_ai <- as.integer(is.na(d$iv_dig_job_ai))
  d <- d[stats::complete.cases(d[, c("z_task_profile", "z_dualization", "RD",
                                     "dem_agegroup", "dem_income_decile")]), ]
  glm(miss_ai ~ z_task_profile + z_dualization + RD + factor(dem_agegroup) +
        dem_income_decile, data = d, family = binomial)
}

# Cleavage-shape (entry W): DESCRIPTIVE ONLY. Cell membership is a country-level
# property -> the Cell-4-vs-Cell-1 contrast is 12 countries regardless of N.
# NO inferential test, NO "significant". q17 individual decomposition is deferred.
cleavage_shape <- function(df) {
  d <- df[!is.na(df$cluster_label), ]
  d$gap <- d$dv_rd_robottax - d$dv_rd_ubi             # robot-tax minus UBI (Core)
  agg <- aggregate(gap ~ cluster_label, data = d, FUN = function(x) mean(x, na.rm = TRUE))
  ncc <- aggregate(ctrcode ~ cluster_label, data = d, FUN = function(x) length(unique(x)))
  merge(agg, ncc, by = "cluster_label")              # descriptive table, by typology cell
}

# ---- M0/M1 reporter (both stages) -------------------------------------------
report_M0M1 <- function(df, dv) {
  cat(sprintf("\n--- M0 (%s): %s ~ 1 + (1|ctrcode) ---\n", dv, dv))
  r0 <- fit_M0(df, dv); report_n(r0$d); cat(sprintf("   ICC = %.4f\n", icc_of(r0$m)))
  cat(sprintf("--- M1 (%s): + AIIE(CWC) + L1 controls + (1|ctrcode) ---\n", dv))
  r1 <- fit_M1(df, dv); report_n(r1$d)
  g <- summary(r1$m)$coefficients["aiie_cwc", ]
  cat(sprintf("   gamma10 (aiie_cwc): est=%+.4f  se=%.4f  t=%.2f  p=%.3f  [expected ~0]\n",
              g[["Estimate"]], g[["Std. Error"]], g[["t value"]], g[["Pr(>|t|)"]]))
}

# ---- variance-component + fixed-effect reporters (M2/M3) ---------------------
report_varcomp <- function(m) {
  G  <- lme4::VarCorr(m)$ctrcode
  sl <- nrow(G) > 1                                       # has a random slope?
  tau00 <- G[1, 1]; tau11 <- if (sl) G[2, 2] else NA_real_
  corr  <- if (sl) attr(G, "correlation")[1, 2] else NA_real_
  s2 <- sigma(m)^2; icc <- tau00 / (tau00 + s2)
  cat(sprintf("   VarCorr: tau00(intercept)=%.5f", tau00))
  if (sl) cat(sprintf("  tau11(aiie_cwc slope)=%.5f  corr(int,slope)=%+.3f", tau11, corr))
  cat(sprintf("\n            sigma2(resid)=%.5f  ICC=%.4f\n", s2, icc))
  invisible(list(tau00 = tau00, tau11 = tau11, corr = corr, s2 = s2, icc = icc, slope = sl))
}
report_fixef <- function(m, highlight = character(0)) {
  co <- summary(m)$coefficients                           # lmerTest Satterthwaite df
  cat("   Fixed effects (Satterthwaite df):\n")
  for (rn in rownames(co))
    cat(sprintf("     %-28s est=%+.4f  se=%.4f  df=%.1f  t=%.2f  p=%.3f%s\n",
                rn, co[rn, "Estimate"], co[rn, "Std. Error"], co[rn, "df"],
                co[rn, "t value"], co[rn, "Pr(>|t|)"], if (rn %in% highlight) "  <<" else ""))
  invisible(co)
}

# ---- M2/M3: random-slope fit with #23 singular-fit fallback ------------------
run_M2M3 <- function(df, dv, fixed, label, l2_highlight = character(0), expect_countries = NULL) {
  d  <- build_sample(df, dv, unique(c("aiie_cwc", fixed)))
  nc <- length(unique(d$ctrcode))
  cat(sprintf("\n--- %s (%s): + (1 + aiie_cwc | ctrcode) ---\n", label, dv)); report_n(d)
  if (!is.null(expect_countries) && nc != expect_countries)
    cat(sprintf("   *** FLAG: expected %d countries, got %d (axis-coverage check) ***\n",
                expect_countries, nc))
  m    <- lmer(mk(dv, c(fixed, "(1 + aiie_cwc|ctrcode)")), data = d, REML = TRUE)
  sing <- lme4::isSingular(m, tol = 1e-4)
  msgs <- m@optinfo$conv$lme4$messages
  cat(sprintf("   random-slope fit: isSingular(tol=1e-4)=%s%s\n", sing,
              if (length(msgs)) paste0("  | conv: ", paste(msgs, collapse = "; ")) else ""))
  rs  <- report_varcomp(m)                                # always show the random-slope tau11
  g10 <- summary(m)$coefficients["aiie_cwc", "Estimate"]
  if (!is.na(rs$tau11))
    cat(sprintf("   tau11 SD=%.4f vs fixed gamma10=%+.4f  (between-country slope SD = %.0f%% of |avg slope|)\n",
                sqrt(rs$tau11), g10, 100 * sqrt(rs$tau11) / abs(g10)))
  if (sing || length(msgs)) {
    cat("   ***  #23: random-slope variance NOT cleanly estimable at this cluster count  ***\n")
    cat("   -> FALLBACK to random-INTERCEPT (same fixed effects):\n")
    mf <- lmer(mk(dv, c(fixed, "(1|ctrcode)")), data = d, REML = TRUE)
    report_varcomp(mf); report_fixef(mf, highlight = l2_highlight)
    if (requireNamespace("clubSandwich", quietly = TRUE)) {
      cr <- tryCatch(clubSandwich::coef_test(mf, vcov = "CR2"), error = function(e) NULL)
      if (!is.null(cr)) { cat("   CR2 cluster-robust SEs (fallback):\n"); print(cr) }
    } else cat("   (clubSandwich not installed -> Satterthwaite only; CR2/bootstrap deferred)\n")
    cat("   [reported: random-intercept FALLBACK]\n")
  } else {
    report_fixef(m, highlight = l2_highlight)
    cat("   [reported: random-slope fit]\n")
  }
  invisible(m)
}

# ---- M4: headline cross-level interactions, with/without GDP -----------------
# Fits the (unchanged) M4 spec; with_gdp=FALSE only REMOVES gdp_z (the required
# contrast -- gdp_z correlates 0.54 with z_task_profile). #23 fallback to random
# intercept if singular/non-converged; |corr|>=0.95 flagged as strain (not refit).
run_M4 <- function(df, dv, with_gdp, expect_countries = 23) {
  l2  <- if (with_gdp) L2_main else setdiff(L2_main, "gdp_z")
  d   <- build_sample(df, dv, c(L1, l2))
  rhs <- c(L1, l2, "aiie_cwc:z_task_profile", "aiie_cwc:z_dualization",
           "z_task_profile:z_dualization", "(1 + aiie_cwc|ctrcode)")
  cat(sprintf("\n  --- M4 (%s) [%s] ---\n", dv, if (with_gdp) "with-GDP" else "no-GDP")); report_n(d)
  nc <- length(unique(d$ctrcode))
  if (nc != expect_countries)
    cat(sprintf("     *** FLAG: expected %d countries, got %d ***\n", expect_countries, nc))
  m    <- lmer(mk(dv, rhs), data = d, REML = TRUE)
  sing <- lme4::isSingular(m, tol = 1e-4)
  msgs <- m@optinfo$conv$lme4$messages
  corr <- attr(lme4::VarCorr(m)$ctrcode, "correlation")[1, 2]
  cat(sprintf("     RE: isSingular(tol=1e-4)=%s | corr(int,slope)=%+.3f%s%s\n", sing, corr,
              if (abs(corr) >= 0.95) "  [|corr|>=0.95 STRAIN]" else "",
              if (length(msgs)) paste0(" | conv: ", paste(msgs, collapse = "; ")) else ""))
  report_varcomp(m)
  reported <- m; used <- "rand-slope"
  if (sing || length(msgs)) {
    cat("     ***  #23: random-effects structure NOT cleanly estimable -- FALLBACK firing  ***\n")
    mf <- tryCatch(lmer(mk(dv, c(L1, l2, "aiie_cwc:z_task_profile", "aiie_cwc:z_dualization",
                                 "z_task_profile:z_dualization", "(1|ctrcode)")),
                        data = d, REML = TRUE),
                   error = function(e) { cat("     FALLBACK ERROR:", conditionMessage(e), "\n"); NULL })
    if (!is.null(mf)) {
      cat("     FALLBACK PRODUCED a random-intercept refit (confirmed, no error).\n"); report_varcomp(mf)
      if (requireNamespace("clubSandwich", quietly = TRUE)) {
        cr <- tryCatch(clubSandwich::coef_test(mf, vcov = "CR2"), error = function(e) NULL)
        if (!is.null(cr)) { cat("     CR2 cluster-robust (fallback fixed effects):\n"); print(cr) }
      } else cat("     (clubSandwich absent -> Satterthwaite only; CR2/bootstrap deferred)\n")
      reported <- mf; used <- "rand-INTERCEPT FALLBACK"
    }
  } else if (abs(corr) >= 0.95) {
    cat("     *** #23 NOTE: |corr(int,slope)|>=0.95 -- RE structure straining (not singular at",
        "tol=1e-4); reported as-is, not refit. A brms posterior on the RE structure is the",
        "natural tiebreaker -- NOT run here. ***\n")
  }
  list(m = reported, used = used)
}

# focal-coefficient row (tolerant of interaction-term ordering)
fc <- function(co, term) {
  cand <- term
  if (grepl(":", term)) { p <- strsplit(term, ":")[[1]]; cand <- c(term, paste(p[2], p[1], sep = ":")) }
  hit <- cand[cand %in% rownames(co)]
  if (length(hit)) as.numeric(co[hit[1], c("Estimate", "Std. Error", "df", "t value", "Pr(>|t|)")])
  else rep(NA_real_, 5)
}

# M4 reporter: both GDP variants, side-by-side focal coefficients
report_M4 <- function(df, dv) {
  cat(sprintf("\n=== M4 (%s): HEADLINE cross-level interactions (gamma11 / gamma12) ===\n", dv))
  rg <- run_M4(df, dv, with_gdp = TRUE)
  rn <- run_M4(df, dv, with_gdp = FALSE)
  cog <- summary(rg$m)$coefficients; con <- summary(rn$m)$coefficients
  foc <- list("gamma10  aiie_cwc"                = "aiie_cwc",
              "gamma11  aiie_cwc:z_task_profile" = "aiie_cwc:z_task_profile",
              "gamma12  aiie_cwc:z_dualization"  = "aiie_cwc:z_dualization",
              "gamma03  z_task:z_dualization"    = "z_task_profile:z_dualization",
              "  z_task_profile (L2 main)"       = "z_task_profile",
              "  z_dualization  (L2 main)"       = "z_dualization",
              "  gdp_z          (L2 main)"       = "gdp_z")
  cat(sprintf("\n  Focal coefficients (%s) -- with-GDP[%s] | no-GDP[%s]  (est, se, Satterthwaite df, p):\n",
              dv, rg$used, rn$used))
  for (lab in names(foc)) {
    g <- fc(cog, foc[[lab]]); n <- fc(con, foc[[lab]])
    cat(sprintf("   %-34s  G:%+.4f se%.4f df%.1f p%.3f  |  NG:%+.4f se%.4f df%.1f p%.3f\n",
                lab, g[1], g[2], g[3], g[5], n[1], n[2], n[3], n[5]))
  }
}

# ---- M5/M6: temporal DiD (wave x AIIE, entry C) ------------------------------
# M5 = RD, M6 = SI. Spec (fit_M5_6, unchanged) = M4 + wave + aiie_cwc:wave with
# (1 + aiie_cwc | ctrcode). Runs the entry-C identification check (within-country
# wave balance + interaction estimability) BEFORE reporting, then #23 strain/fallback.
run_M5_6 <- function(df, dv, label, expect_countries = 23) {
  cat(sprintf("\n=== %s (%s): temporal DiD  + wave + aiie_cwc:wave (entry C) ===\n", label, dv))
  warns <- character(0)
  r <- withCallingHandlers(fit_M5_6(df, dv),
         warning = function(w) { warns <<- c(warns, conditionMessage(w)); invokeRestart("muffleWarning") })
  m <- r$m; d <- r$d
  report_n(d); nc <- length(unique(d$ctrcode))
  if (nc != expect_countries) cat(sprintf("   *** FLAG: expected %d countries, got %d ***\n", expect_countries, nc))

  ## --- entry-C identification check (DiD only meaningful if these hold) ---
  tab <- table(d$ctrcode, d$wave); per <- apply(tab, 1, min); low <- names(per)[per < 100]
  cat(sprintf("   [ID] within-country wave balance: min cell=%d  median cell=%d (per country x wave)\n",
              min(tab), as.integer(stats::median(tab))))
  if (length(low)) cat(sprintf("   *** ID FLAG: countries with <100 rows in a wave: %s ***\n", paste(low, collapse = ", ")))
  else cat(sprintf("   [ID] all %d countries have >=100 rows in BOTH waves -> within-country temporal contrast supported\n", nc))
  w24 <- as.integer(d$wave == "2024"); ixw <- d$aiie_cwc * w24
  cat(sprintf("   [ID] cor(aiie_cwc:wave, aiie_cwc)=%+.3f  cor(aiie_cwc:wave, wave)=%+.3f (neither = 1 -> estimable)\n",
              stats::cor(ixw, d$aiie_cwc), stats::cor(ixw, w24)))
  fn <- names(lme4::fixef(m)); iname <- fn[grepl("aiie_cwc", fn) & grepl("wave", fn)]
  if (!length(iname)) cat("   *** ID FLAG: aiie_cwc:wave NOT in fixed effects (DROPPED) -- DiD term not identified ***\n")
  else cat(sprintf("   [ID] aiie_cwc:wave estimated as '%s' = %+.4f (not dropped/NA)\n", iname[1], lme4::fixef(m)[iname[1]]))
  cat(sprintf("   [ID] rank-deficiency warning: %s | fit warnings: %s\n",
              any(grepl("rank.?defic", warns, ignore.case = TRUE)),
              if (length(warns)) paste(warns, collapse = "; ") else "(none)"))

  ## --- #23 random-effects strain ---
  sing <- lme4::isSingular(m, tol = 1e-4); msgs <- m@optinfo$conv$lme4$messages
  corr <- attr(lme4::VarCorr(m)$ctrcode, "correlation")[1, 2]
  cat(sprintf("   RE: isSingular(tol=1e-4)=%s | corr(int,slope)=%+.3f%s%s\n", sing, corr,
              if (abs(corr) >= 0.95) "  [|corr|>=0.95 STRAIN]" else "",
              if (length(msgs)) paste0(" | conv: ", paste(msgs, collapse = "; ")) else ""))
  report_varcomp(m)
  reported <- m; used <- "rand-slope"
  if (sing || length(msgs)) {
    cat("   ***  #23: RE structure NOT cleanly estimable -- FALLBACK firing  ***\n")
    fx <- c(L1, L2_main, "aiie_cwc:z_task_profile", "aiie_cwc:z_dualization",
            "z_task_profile:z_dualization", "wave", "aiie_cwc:wave")
    mf <- tryCatch(lmer(mk(dv, c(fx, "(1|ctrcode)")), data = d, REML = TRUE),
                   error = function(e) { cat("   FALLBACK ERROR:", conditionMessage(e), "\n"); NULL })
    if (!is.null(mf)) {
      cat("   FALLBACK PRODUCED a random-intercept refit (confirmed, no error).\n"); report_varcomp(mf)
      if (requireNamespace("clubSandwich", quietly = TRUE)) {
        cr <- tryCatch(clubSandwich::coef_test(mf, vcov = "CR2"), error = function(e) NULL)
        if (!is.null(cr)) { cat("   CR2 (fallback fixed effects):\n"); print(cr) }
      } else cat("   (clubSandwich absent -> Satterthwaite only; CR2/bootstrap deferred)\n")
      reported <- mf; used <- "rand-INTERCEPT FALLBACK"
    }
  } else if (abs(corr) >= 0.95) {
    cat("   *** #23 NOTE: |corr|>=0.95 straining (not singular at tol=1e-4); reported as-is.",
        "brms posterior on the RE structure is the tiebreaker -- NOT run. ***\n")
  }

  ## --- focal report ---
  co <- summary(reported)$coefficients
  iname2 <- rownames(co)[grepl("aiie_cwc", rownames(co)) & grepl("wave", rownames(co))]
  cat(sprintf("\n   FOCAL (%s) [reported: %s] (est, se, Satterthwaite df, p):\n", dv, used))
  prow <- function(lab, term) { v <- fc(co, term)
    cat(sprintf("     %-32s est=%+.4f se=%.4f df=%.1f p=%.3f\n", lab, v[1], v[2], v[3], v[5])) }
  if (length(iname2)) prow("aiie_cwc:wave (DiD HEADLINE)", iname2[1]) else cat("     aiie_cwc:wave -- NOT ESTIMATED\n")
  if ("wave2024" %in% rownames(co)) prow("wave (avg 2022->2024 shift)", "wave2024")
  prow("gamma10  aiie_cwc", "aiie_cwc")
  prow("gamma11  aiie_cwc:z_task_profile", "aiie_cwc:z_task_profile")
  prow("gamma12  aiie_cwc:z_dualization", "aiie_cwc:z_dualization")
  prow("gamma03  z_task:z_dualization", "z_task_profile:z_dualization")
  invisible(reported)
}

# ---- PART B orchestration (2024 cross-section, EXPLORATORY; entries U/V/W) ---
run_partB <- function(df) {
  cat("\n===== PART B (2024 cross-section, EXPLORATORY -- entries U/V/W) =====\n")
  cat("  iv_dig_job_ai is 2024-only -> M7 on the 2024 cross-section, random-INTERCEPT only.\n")

  ## --- M7 redescription: z_dualization:fear vs socx_z:fear (COMMON moderator) ---
  for (dv in c("RD", "SI")) {
    cat(sprintf("\n=== M7 (%s): redescription -- does z_dualization:fear survive net of socx_z:fear? ===\n", dv))
    for (fear in c("fear_lin", "fear_bin")) {
      r <- fit_M7(df, dv, fear); m <- r$m; d <- r$d
      co <- summary(m)$coefficients; nc <- length(unique(d$ctrcode))
      sing <- lme4::isSingular(m, tol = 1e-4); msgs <- m@optinfo$conv$lme4$messages
      cat(sprintf("\n  [%s]  N=%d  countries=%d  isSingular=%s%s\n", fear, nrow(d), nc, sing,
                  if (length(msgs)) paste0("  conv: ", paste(msgs, collapse = "; ")) else ""))
      if (nc != 23) cat(sprintf("     *** FLAG: expected 23 countries, got %d ***\n", nc))
      zd <- fc(co, paste0("z_dualization:", fear)); sx <- fc(co, paste0("socx_z:", fear))
      cat(sprintf("     z_dualization:%-8s (FOCAL)      est=%+.4f se=%.4f df=%.1f p=%.3f\n",
                  fear, zd[1], zd[2], zd[3], zd[5]))
      cat(sprintf("     socx_z:%-8s       (competing)   est=%+.4f se=%.4f df=%.1f p=%.3f\n",
                  fear, sx[1], sx[2], sx[3], sx[5]))
      for (t in c("z_dualization", "socx_z", fear)) { v <- fc(co, t)
        cat(sprintf("       %-16s (main)            est=%+.4f se=%.4f df=%.1f p=%.3f\n", t, v[1], v[2], v[3], v[5])) }
    }
  }

  ## --- MNAR diagnostic (for the record) ---
  cat("\n=== MNAR diagnostic: 2024 AI-fear missingness logit on observables ===\n")
  mm <- mnar_diag(df)
  cat(sprintf("  N=%d  McFadden pseudo-R2 = %.4f  (low -> missingness largely NOT explained by observables)\n",
              stats::nobs(mm), 1 - mm$deviance / mm$null.deviance))
  sm <- summary(mm)$coefficients
  for (rn in rownames(sm)) if (rn != "(Intercept)")
    cat(sprintf("    %-26s b=%+.3f  p=%.3f%s\n", rn, sm[rn, 1], sm[rn, 4], if (sm[rn, 4] < .05) "  *" else ""))

  ## --- Cleavage-shape (entry W) -- DESCRIPTIVE ONLY ---
  cat("\n=== Cleavage-shape (entry W) -- DESCRIPTIVE ONLY (no test, no p-value) ===\n")
  cat("  Operationalizes v1 §4.3 P2 (theory-first). Cell membership is country-level; the\n")
  cat("  Cell-4-vs-Cell-1 contrast rests on ~6 vs ~6 countries regardless of respondent N.\n")
  cs <- cleavage_shape(df)
  cat("  cleavage_shape(): cluster_label | gap (mean robottax-UBI) | ctrcode (= country count):\n")
  print(cs, row.names = FALSE)
  dd <- df[!is.na(df$cluster_label), ]
  brk <- aggregate(cbind(dv_rd_robottax, dv_rd_ubi, z_task_profile, z_dualization) ~ cluster_label,
                   data = dd, FUN = function(x) mean(x, na.rm = TRUE))
  brk$gap <- brk$dv_rd_robottax - brk$dv_rd_ubi; brk <- brk[order(-brk$gap), ]
  cat("\n  Direction check (descriptive, sorted by gap desc; axis means locate each cell in the 2x2):\n")
  cat(sprintf("    %-12s %9s %8s %8s | %8s %8s\n", "cluster", "robottax", "UBI", "gap", "zTask", "zDual"))
  for (i in seq_len(nrow(brk)))
    cat(sprintf("    %-12s %9.3f %8.3f %+8.3f | %+8.3f %+8.3f\n",
                brk$cluster_label[i], brk$dv_rd_robottax[i], brk$dv_rd_ubi[i], brk$gap[i],
                brk$z_task_profile[i], brk$z_dualization[i]))
  cat("  (No inference. q17 individual-mechanism decomposition is the deferred powered test -- needs Script 04 reopen.)\n")
}

# =============================================================================
# FULL-STAGE robustness family (#6 welfare / #21+S2 weighted gap / F alt-DVs / C4 WeMix).
# Each lmer rung: random-slope fit with the #23 singular-fit fallback. EXPECTED singular
# at 15 clusters (weighted gap) -> first real fallback firing. WeMix guarded (C4).
# =============================================================================
M4_FIXED <- function() c(L1, L2_main, "aiie_cwc:z_task_profile", "aiie_cwc:z_dualization",
                         "z_task_profile:z_dualization")

fit_robust <- function(df, dv, fixed, need, label, expect, weighted = FALSE) {
  d <- build_sample(df, dv, need); nc <- length(unique(d$ctrcode))
  rec <- list(label = label, dv = dv, n = nrow(d), countries = nc, expect = expect,
              flag_n = (nc != expect), isSingular = NA, fallback = FALSE, used = NA,
              model = NULL, cr2 = NULL, conv = character(0))
  if (weighted) {                                   # WeMix pseudo-ML (L1=weight, L2=1), C4
    if (!requireNamespace("WeMix", quietly = TRUE)) { rec$used <- "SKIP: WeMix not loadable"; return(rec) }
    d$.l2w <- 1
    m <- tryCatch(WeMix::mix(mk(dv, c(fixed, "(1|ctrcode)")), data = d, weights = c("weight", ".l2w")),
                  error = function(e) NULL)
    if (is.null(m)) rec$used <- "WeMix ERROR" else { rec$model <- m; rec$used <- "WeMix pseudo-ML (L1=weight,L2=1)" }
    return(rec)
  }
  cv <- character(0)
  m <- withCallingHandlers(lmer(mk(dv, c(fixed, "(1 + aiie_cwc|ctrcode)")), data = d, REML = TRUE),
         warning = function(w) { cv <<- c(cv, conditionMessage(w)); invokeRestart("muffleWarning") })
  rec$isSingular <- lme4::isSingular(m, tol = 1e-4); rec$model <- m; rec$used <- "rand-slope"
  rec$conv <- m@optinfo$conv$lme4$messages
  if (rec$isSingular || length(rec$conv)) {         # #23 fallback -> random intercept
    mf <- tryCatch(lmer(mk(dv, c(fixed, "(1|ctrcode)")), data = d, REML = TRUE), error = function(e) NULL)
    if (!is.null(mf)) {
      rec$fallback <- TRUE; rec$model <- mf; rec$used <- "rand-INTERCEPT fallback (#23)"
      if (requireNamespace("clubSandwich", quietly = TRUE))
        rec$cr2 <- tryCatch(clubSandwich::coef_test(mf, vcov = "CR2"), error = function(e) NULL)
    } else rec$used <- "rand-slope (singular; fallback ERRORED)"
  }
  rec
}

run_robustness <- function(df) {
  recs <- list(); add <- function(r) recs[[length(recs) + 1]] <<- r
  for (dv in c("RD", "SI")) {
    for (wg in c("cond", "uncond")) {               # M5w/M6w weighted-gap DiD, 15 ctry (#21/S2)
      wgap <- paste0("dualization_gap_weighted_", wg)
      fx <- c(L1, "z_task_profile", wgap, "gdp_z", "aiie_cwc:z_task_profile",
              paste0("aiie_cwc:", wgap), paste0("z_task_profile:", wgap), "wave", "aiie_cwc:wave")
      add(fit_robust(df, dv, fx, c(L1, "z_task_profile", wgap, "gdp_z"),
                     sprintf("%sw_%s", ifelse(dv == "RD", "M5", "M6"), wg), expect = 15))
    }
    add(fit_robust(df, dv, c(M4_FIXED(), "socx_z"), c(L1, L2_main, "socx_z"),
                   sprintf("welfare_SOCX_%s", dv), expect = 23))            # #6 SOCX rung, 23 ctry
    add(fit_robust(df, dv, c(M4_FIXED(), "cwep_z"), c(L1, L2_main, "cwep_z"),
                   sprintf("welfare_CWEP_%s", dv), expect = 17))            # #6 CWEP swap, 17 ctry
    add(fit_robust(df, dv, M4_FIXED(), c(L1, L2_main), sprintf("WeMix_%s", dv), expect = 23, weighted = TRUE))
  }
  for (a in list(c("RD_single", "RD single-item q20"), c("RD_wtp", "RD WTP q19d+e"),
                 c("SI_single", "SI single q42a [C7 scale-component]"), c("SI_wtp", "SI WTP q19b+c")))
    add(fit_robust(df, a[1], M4_FIXED(), c(L1, L2_main), a[2], expect = 23))  # entry F alt-DVs, 23 ctry
  recs
}

# =============================================================================
# OUTPUT WRITER + brms co-primary + run_full orchestration
# =============================================================================
vc_row <- function(m) {
  G <- tryCatch(lme4::VarCorr(m)$ctrcode, error = function(e) NULL)
  if (is.null(G)) return(list(tau00 = NA, tau11 = NA, tau01 = NA, sigma2 = NA, icc = NA))
  sl <- nrow(G) > 1; s2 <- sigma(m)^2; t00 <- G[1, 1]
  list(tau00 = t00, tau11 = if (sl) G[2, 2] else NA, tau01 = if (sl) G[1, 2] else NA,
       sigma2 = s2, icc = t00 / (t00 + s2))
}
tidy_fixed <- function(m) {
  co <- tryCatch(summary(m)$coefficients, error = function(e) NULL); if (is.null(co)) return(NULL)
  data.frame(term = rownames(co), estimate = co[, "Estimate"], se = co[, "Std. Error"],
             df = if ("df" %in% colnames(co)) co[, "df"] else NA_real_, p = co[, ncol(co)], row.names = NULL)
}
nwave <- function(d) { t <- table(factor(d$wave, levels = c("2022", "2024"))); sprintf("%d/%d", t["2022"], t["2024"]) }

# brms co-primary -- adjudicates the SI random-effects structure (#23)
report_brms <- function(df) {
  ok <- requireNamespace("brms", quietly = TRUE) &&
        isTRUE(tryCatch(pkgbuild::has_build_tools(FALSE), error = function(e) FALSE))
  if (!ok) { cat("  brms NOT available -> co-primary SKIPPED (frequentist stands).\n"); return(NULL) }
  fits <- list()
  for (dv in c("RD", "SI")) {
    d <- build_sample(df, dv, c(L1, L2_main))
    cat(sprintf("  brms %s (M4 structure, 4 chains x 2000) -- compiling + sampling ...\n", dv))
    m <- tryCatch(brms::brm(brms::bf(mk(dv, c(M4_FIXED(), "(1 + aiie_cwc|ctrcode)"))), data = d,
                            chains = 4, cores = 4, iter = 2000, seed = 1,
                            prior = brms::set_prior("normal(0,1)", class = "b"), refresh = 0, silent = 2),
                  error = function(e) { cat("    brms", dv, "ERROR:", conditionMessage(e), "\n"); NULL })
    if (is.null(m)) next
    fits[[dv]] <- m
    vars <- c("sd_ctrcode__Intercept", "sd_ctrcode__aiie_cwc", "cor_ctrcode__Intercept__aiie_cwc")
    sm <- tryCatch(posterior::summarise_draws(posterior::subset_draws(posterior::as_draws_df(m), variable = vars)),
                   error = function(e) NULL)
    np <- tryCatch(brms::nuts_params(m), error = function(e) NULL)
    ndiv <- if (!is.null(np)) sum(np$Value[np$Parameter == "divergent__"]) else NA
    cat(sprintf("  brms %s RE posterior (median [q5,q95] Rhat ess):\n", dv))
    if (!is.null(sm)) for (i in seq_len(nrow(sm)))
      cat(sprintf("    %-34s %+.3f [%+.3f,%+.3f] Rhat=%.3f ess=%.0f\n",
          sm$variable[i], sm$median[i], sm$q5[i], sm$q95[i], sm$rhat[i], sm$ess_bulk[i]))
    cat(sprintf("    divergent transitions: %s\n", ndiv))
  }
  fits
}

write_outputs <- function(df, models, rob, brms_fits, cs) {
  ROOT <- normalizePath(file.path(dirname(PARQUET), "..", "..", ".."))
  OUT <- file.path(ROOT, "v2_prep", "output"); FIG <- file.path(ROOT, "figures")
  dir.create(OUT, showWarnings = FALSE, recursive = TRUE); dir.create(FIG, showWarnings = FALSE, recursive = TRUE)
  V <- character(0); LOG <- function(...) V <<- c(V, sprintf(...))
  LOG("Script 08 verification log -- %s", as.character(Sys.time()))
  wr <- function(obj, file) tryCatch({ write.csv(obj, file.path(OUT, file), row.names = FALSE); LOG("wrote %s", file) },
                                     error = function(e) LOG("ERROR writing %s: %s", file, conditionMessage(e)))

  ## 1. coefficient tables + model meta (M0-M7) per DV
  for (DV in c("RD", "SI")) tryCatch({
    keys <- grep(sprintf("_%s($|_)", DV), names(models), value = TRUE)
    rows <- list(); meta <- list()
    for (k in keys) { m <- models[[k]]$m; d <- models[[k]]$d
      tf <- tidy_fixed(m); if (!is.null(tf)) { tf$model <- k; rows[[length(rows) + 1]] <- tf }
      v <- vc_row(m)
      meta[[length(meta) + 1]] <- data.frame(model = k, n = nrow(d), countries = length(unique(d$ctrcode)),
        per_wave = nwave(d), tau00 = v$tau00, tau11 = v$tau11, tau01 = v$tau01, sigma2 = v$sigma2, icc = v$icc,
        isSingular = lme4::isSingular(m, tol = 1e-4))
    }
    if (length(rows)) wr(do.call(rbind, rows), sprintf("coef_table_%s.csv", DV))
    if (length(meta)) wr(do.call(rbind, meta), sprintf("model_meta_%s.csv", DV))
  }, error = function(e) LOG("ERROR coef table %s: %s", DV, conditionMessage(e)))

  ## 2. headline inference for M4 gamma11/gamma12: Satterthwaite + KR + CR2 + bootstrap
  tryCatch({
    hi <- list()
    for (DV in c("RD", "SI")) {
      m <- models[[paste0("M4_", DV)]]$m; sat <- summary(m)$coefficients
      kr <- tryCatch(summary(m, ddf = "Kenward-Roger")$coefficients, error = function(e) NULL)
      cr <- tryCatch(as.data.frame(clubSandwich::coef_test(m, vcov = "CR2")), error = function(e) NULL)
      bt <- tryCatch(confint(m, parm = c("aiie_cwc:z_task_profile", "aiie_cwc:z_dualization"),
                             method = "boot", nsim = 200, boot.type = "perc"), error = function(e) NULL)
      crn <- if (!is.null(cr)) (if ("Coef" %in% names(cr)) cr$Coef else rownames(cr)) else NULL
      for (g in c("aiie_cwc:z_task_profile", "aiie_cwc:z_dualization")) {
        ci <- if (!is.null(cr)) which(crn == g) else integer(0)
        hi[[length(hi) + 1]] <- data.frame(dv = DV, term = g,
          sat_est = sat[g, "Estimate"], sat_se = sat[g, "Std. Error"], sat_df = sat[g, "df"], sat_p = sat[g, "Pr(>|t|)"],
          kr_df = if (!is.null(kr)) kr[g, "df"] else NA, kr_p = if (!is.null(kr)) kr[g, "Pr(>|t|)"] else NA,
          cr2_se = if (length(ci)) cr$SE[ci] else NA, cr2_p = if (length(ci) && "p_Satt" %in% names(cr)) cr$p_Satt[ci] else NA,
          boot_lo = if (!is.null(bt)) bt[g, 1] else NA, boot_hi = if (!is.null(bt)) bt[g, 2] else NA)
      }
    }
    if (length(hi)) wr(do.call(rbind, hi), "headline_inference_M4.csv")
  }, error = function(e) LOG("ERROR headline inference: %s", conditionMessage(e)))

  ## 3. robustness panel
  tryCatch({
    rp <- lapply(rob, function(r) data.frame(label = r$label, dv = r$dv, n = r$n, countries = r$countries,
      expect = r$expect, n_flag = isTRUE(r$flag_n), isSingular = r$isSingular, fallback = r$fallback, used = r$used))
    wr(do.call(rbind, rp), "robustness_panel.csv")
    for (r in rob) if (isTRUE(r$flag_n)) LOG("ROBUSTNESS N-FLAG: %s expected %d got %d", r$label, r$expect, r$countries)
  }, error = function(e) LOG("ERROR robustness panel: %s", conditionMessage(e)))

  ## 4. typology scatter + v1 cluster-count consistency check
  tryCatch({
    cl <- unique(df[!is.na(df$cluster_label), c("ctrcode", "z_task_profile", "z_dualization", "cluster_label")])
    counts <- table(cl$cluster_label)
    LOG("typology cluster counts: %s", paste(sprintf("%s=%d", names(counts), as.integer(counts)), collapse = ", "))
    v1 <- c(Continental = 8, Liberal = 6, Nordic = 6, Southern = 3)
    for (nm in names(v1)) { got <- if (nm %in% names(counts)) as.integer(counts[nm]) else NA
      if (is.na(got) || got != v1[nm]) LOG("*** SCATTER FLAG: cluster %s count %s != v1 %d (v1-v2 consistency) ***", nm, ifelse(is.na(got), "NA", got), v1[nm]) }
    if (requireNamespace("ggplot2", quietly = TRUE)) {
      p <- ggplot2::ggplot(cl, ggplot2::aes(z_task_profile, z_dualization, colour = cluster_label, label = ctrcode)) +
        ggplot2::geom_point(size = 3) + ggplot2::geom_text(vjust = -0.8, size = 3, show.legend = FALSE) +
        ggplot2::labs(title = "Typology (z_task_profile x z_dualization)", colour = "Cluster") + ggplot2::theme_minimal()
      ggplot2::ggsave(file.path(FIG, "typology_scatter.png"), p, width = 8, height = 6, dpi = 150)
      LOG("wrote figures/typology_scatter.png")
    }
  }, error = function(e) LOG("ERROR scatter: %s", conditionMessage(e)))

  ## 5. coverage assertions + singular flags + save .rds
  ncc <- function(col) length(unique(df$ctrcode[!is.na(df[[col]])]))
  axc <- unique(df$ctrcode[!is.na(df$z_task_profile)]); wgc <- unique(df$ctrcode[!is.na(df$dualization_gap_weighted_uncond)])
  LOG("coverage: raw_gap=%d axes=%d weighted=%d weighted_INT_axes=%d cwep=%d (expect 27/23/18/15/17)",
      ncc("dualization_gap_raw"), ncc("z_task_profile"), ncc("dualization_gap_weighted_uncond"),
      length(intersect(axc, wgc)), ncc("cwep_tot_gen"))
  for (k in names(models)) if (lme4::isSingular(models[[k]]$m, tol = 1e-4)) LOG("SINGULAR (main ladder): %s", k)
  tryCatch(saveRDS(list(models = models, robustness = rob, brms = brms_fits, cleavage = cs),
                   file.path(OUT, "script08_models.rds")), error = function(e) LOG("ERROR .rds: %s", conditionMessage(e)))
  LOG("saved script08_models.rds")
  writeLines(V, file.path(OUT, "verification_log.txt"))
  cat("\n--- verification log ---\n"); cat(paste(V, collapse = "\n"), "\n")
  cat("Artifacts ->", OUT, "and figures/\n")
}

run_full <- function(df) {
  cat("===== FULL STAGE: M0-M6 + Part B (M7) + robustness + brms + output writer =====\n")
  models <- list()
  for (dv in c("RD", "SI")) {
    models[[paste0("M0_", dv)]] <- fit_M0(df, dv); models[[paste0("M1_", dv)]] <- fit_M1(df, dv)
    models[[paste0("M2_", dv)]] <- fit_M2(df, dv); models[[paste0("M3_", dv)]] <- fit_M3(df, dv)
    models[[paste0("M4_", dv)]] <- fit_M4(df, dv)
    models[[ifelse(dv == "RD", "M5_RD", "M6_SI")]] <- fit_M5_6(df, dv)
  }
  for (dv in c("RD", "SI")) for (fr in c("fear_lin", "fear_bin"))
    models[[paste0("M7_", dv, "_", fr)]] <- fit_M7(df, dv, fr)
  cat(sprintf("  main ladder + M7 fitted (%d models). Running robustness family ...\n", length(models)))
  rob <- run_robustness(df)
  cat(sprintf("  robustness fitted (%d rungs). Running brms co-primary ...\n", length(rob)))
  brms_fits <- tryCatch(report_brms(df), error = function(e) { cat("  brms stage ERROR:", conditionMessage(e), "\n"); NULL })
  cs <- cleavage_shape(df)
  cat("  writing outputs ...\n")
  write_outputs(df, models, rob, brms_fits, cs)
}

# =============================================================================
# RUNNER  --  RUN_STAGE: "smoke" | "m0_m3" | "m0_m4" | "m0_m6" | "partB" | "full"
# =============================================================================
main <- function() {
  raw <- read_analytic(PARQUET); assert_columns(raw); df <- prep(raw)
  cat(sprintf("Loaded %d rows | edu2=%s | sex 99->NA dropped=%d | parquet=%s | RUN_STAGE=%s\n",
              nrow(df), paste(levels(df$edu2), collapse = "/"),
              sum(df$dem_sex == 99, na.rm = TRUE), basename(PARQUET), RUN_STAGE))

  if (RUN_STAGE == "full") { run_full(df); return(invisible()) }

  if (RUN_STAGE == "partB") {            # standalone -- does NOT re-run M0-M6
    run_partB(df)
    cat("\n[partB stage complete -- HALT before robustness/brms. M7 (exploratory redescription)",
        "\n + MNAR diagnostic + cleavage-shape (descriptive) reported. M5w/M6w + CWEP +",
        "\n single-item/WTP + WeMix + bootstrap + brms remain DEFINED but NOT orchestrated.]\n")
    return(invisible())
  }

  cat("\n===== M0 + M1 (pooled, both DVs) =====\n")
  for (dv in c("RD", "SI")) report_M0M1(df, dv)
  if (RUN_STAGE == "smoke") {
    cat("\n[smoke stage complete (M0/M1). Set RUN_STAGE<-\"m0_m3\" for M2/M3.]\n")
    return(invisible())
  }

  cat("\n===== M2 (random slope) + M3 (+ L2 mains): #23 singular-fit fallback active =====\n")
  for (dv in c("RD", "SI")) {
    run_M2M3(df, dv, fixed = L1, label = "M2", l2_highlight = "aiie_cwc", expect_countries = 27)
    run_M2M3(df, dv, fixed = c(L1, L2_main), label = "M3",
             l2_highlight = c("aiie_cwc", "z_task_profile", "z_dualization", "gdp_z"),
             expect_countries = 23)
  }
  if (RUN_STAGE == "m0_m3") {
    cat("\n[m0_m3 stage complete -- HALT before M4. M2/M3 non-singular at this N (above).",
        "\n M4-M7 + robustness + Part B remain DEFINED but NOT orchestrated.]\n")
    return(invisible())
  }

  cat("\n===== M4 (HEADLINE cross-level interactions): both DVs, with/without GDP =====\n")
  for (dv in c("RD", "SI")) report_M4(df, dv)
  if (RUN_STAGE == "m0_m4") {
    cat("\n[m0_m4 stage complete -- HALT before M5/M6. gamma11/gamma12 small & non-sig at ~23",
        "\n clusters (expected); M5/M6 + robustness + Part B remain DEFINED but NOT wired.]\n")
    return(invisible())
  }

  cat("\n===== M5 / M6 (temporal DiD: wave x AIIE, entry C): both DVs =====\n")
  run_M5_6(df, "RD", "M5")
  run_M5_6(df, "SI", "M6")
  cat("\n[m0_m6 stage complete -- HALT before robustness/Part B. aiie_cwc:wave (the DiD term)",
      "\n reported with its entry-C identification check + Satterthwaite df; interpretation is the",
      "\n review step that follows. M5w/M6w + CWEP + single-item/WTP + WeMix + Part B (M7) +",
      "\n cleavage-shape remain DEFINED but NOT orchestrated.]\n")
}

if (sys.nframe() == 0L) main()
