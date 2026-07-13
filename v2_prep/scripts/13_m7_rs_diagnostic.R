# 13_m7_rs_diagnostic.R
# =============================================================================
# M7 random-fear-slope diagnostic (pre-submission traceability). Re-runs the
# diagnostic documented in script_08_implementation_notes.md (2026-06-01):
# refit the M7 redescription with a RANDOM FEAR SLOPE (1 + fear | ctrcode)
# instead of the persisted random-intercept-only spec, for BOTH DVs and BOTH
# fear codings. This is a RE-RUN of a documented model, not a new specification.
#
# Reuses Script 08's prep()/build_sample()/fit_M7 structure VERBATIM (only the
# RE term changes: (1|ctrcode) -> (1 + fear|ctrcode)). RI SEs read from the
# persisted coef_table_*.csv for the SE-inflation ratio.
#
# Writes: v2_prep/output/m7_rs_diagnostic.csv
# Anchors (fear_lin): RD focal +0.025 SE~.015 p~.101; SI focal p~.199;
#   competing RD survives (p~.028) SI not (p~.97); fear-slope SD 0.066/0.049;
#   cor(int,slope) ~ -0.87; SE inflation ~2.5x vs RI. Deviations are FLAGGED.
# Does NOT commit.
# =============================================================================

suppressPackageStartupMessages({ library(lme4); library(lmerTest); library(arrow) })
OUT <- normalizePath("v2_prep/output")
say <- function(...) cat(sprintf(...), "\n")

# ---- prep()/build_sample() VERBATIM from 08 ---------------------------------
prep <- function(df) {
  scale3 <- function(d, items) { M <- as.matrix(d[, items]); k <- rowSums(!is.na(M))
    out <- rowMeans(M, na.rm = TRUE); out[k < 2] <- NA_real_; out }
  df$RD <- scale3(df, c("dv_rd_benefits", "dv_rd_ubi", "dv_rd_robottax"))
  df$SI <- scale3(df, c("dv_si_education", "dv_si_retraining", "dv_si_infrastructure"))
  df$edu2 <- factor(ifelse(is.na(df$dem_education_3cat), NA,
                    ifelse(df$dem_education_3cat == 1, "Low", "MedHigh")), levels = c("MedHigh", "Low"))
  df$sex2 <- factor(ifelse(df$dem_sex %in% c(1, 2), df$dem_sex, NA), levels = c(1, 2), labels = c("Male", "Female"))
  df$agegrp    <- factor(df$dem_agegroup)
  df$stdworker <- factor(df$iv_standard_worker, levels = c(1, 2, 3), labels = c("NotEmployed", "Standard", "NonStandard"))
  df$wave      <- factor(df$wave, levels = c("2022", "2024"))
  cm <- tapply(df$aiie_score, df$ctrcode, mean, na.rm = TRUE)
  df$aiie_cwc <- df$aiie_score - cm[as.character(df$ctrcode)]
  df$socx_z <- as.numeric(scale(df$socx_excl_oldsurv_pctgdp))
  df$gdp_z  <- as.numeric(scale(df$gdp_per_capita_ppp))
  df$fear_lin <- df$iv_dig_job_ai
  df$fear_bin <- ifelse(df$iv_dig_job_ai >= 3, 1L, ifelse(df$iv_dig_job_ai <= 2, 0L, NA))
  df
}
build_sample <- function(df, dv, predictors, wave = NULL) {
  d <- if (is.null(wave)) df else df[df$wave == wave, , drop = FALSE]
  need <- c(dv, predictors, "ctrcode", "weight")
  d[stats::complete.cases(d[, need, drop = FALSE]), , drop = FALSE]
}
mk <- function(dv, rhs) stats::as.formula(paste(dv, "~", paste(rhs, collapse = " + ")))
fc <- function(co, term) {                    # tolerant of interaction-term ordering
  cand <- term; if (grepl(":", term)) { p <- strsplit(term, ":")[[1]]; cand <- c(term, paste(p[2], p[1], sep = ":")) }
  hit <- cand[cand %in% rownames(co)]
  if (length(hit)) as.numeric(co[hit[1], c("Estimate", "Std. Error", "df", "Pr(>|t|)")]) else rep(NA_real_, 4)
}

# ---- M7 with RANDOM FEAR SLOPE (only the RE term differs from fit_M7) --------
fit_M7_rs <- function(df, dv, fear) {
  d <- build_sample(df, dv, c("z_dualization", "socx_z", fear,
                              "edu2", "sex2", "agegrp", "dem_income_decile", "stdworker"), wave = "2024")
  rhs <- c("edu2", "sex2", "agegrp", "dem_income_decile", "stdworker",
           "z_dualization", "socx_z", fear,
           paste0("z_dualization:", fear), paste0("socx_z:", fear),
           paste0("(1 + ", fear, "|ctrcode)"))
  list(m = lmer(mk(dv, rhs), data = d, REML = TRUE), d = d)
}

df <- prep(as.data.frame(arrow::read_parquet(normalizePath("v2_prep/data/processed/analytic_l1l2.parquet"))))
coef_ri <- rbind(read.csv(file.path(OUT, "coef_table_RD.csv"), stringsAsFactors = FALSE),
                 read.csv(file.path(OUT, "coef_table_SI.csv"), stringsAsFactors = FALSE))
ri_se <- function(dv, fear, which) {           # RI-fit SE from the persisted coef table
  mdl <- paste0("M7_", dv, "_", fear)
  sub <- coef_ri[coef_ri$model == mdl, ]
  key <- if (which == "focal") "z_dualization" else "socx_z"
  r <- sub[grepl(key, sub$term) & grepl("fear", sub$term), ]
  if (nrow(r)) r$se[1] else NA_real_
}

rows <- list(); flags <- character(0)
for (dv in c("RD", "SI")) for (fear in c("fear_lin", "fear_bin")) {
  r <- suppressWarnings(fit_M7_rs(df, dv, fear)); m <- r$m; d <- r$d
  co <- summary(m)$coefficients
  sing <- lme4::isSingular(m, tol = 1e-4)
  G <- lme4::VarCorr(m)$ctrcode
  sd_fear <- sqrt(G[2, 2]); cor_is <- attr(G, "correlation")[1, 2]
  nc <- length(unique(d$ctrcode))
  say("\n[%s / %s]  N=%d ctry=%d  isSingular=%s  fear-slope SD=%.4f  cor(int,slope)=%+.3f",
      dv, fear, nrow(d), nc, sing, sd_fear, cor_is)
  for (which in c("focal", "competing")) {
    term <- if (which == "focal") paste0("z_dualization:", fear) else paste0("socx_z:", fear)
    v <- fc(co, term); rs <- ri_se(dv, fear, which); infl <- v[2] / rs
    rows[[length(rows) + 1]] <- data.frame(dv = dv, fear_coding = fear, role = which, term = term,
      est = v[1], se = v[2], df = v[3], p = v[4], ri_se = rs, se_inflation = infl,
      fear_slope_sd = sd_fear, cor_int_slope = cor_is, isSingular = sing, n = nrow(d), countries = nc, row.names = NULL)
    say("   %-9s %-24s est=%+.4f se=%.4f df=%.1f p=%.4f | ri_se=%.4f infl=%.2fx",
        which, term, v[1], v[2], v[3], v[4], rs, infl)
  }
}
out <- do.call(rbind, rows)
write.csv(out, file.path(OUT, "m7_rs_diagnostic.csv"), row.names = FALSE)
say("\nwrote m7_rs_diagnostic.csv (%d rows)", nrow(out))

# ---- anchor validation (fear_lin only; fear_bin has no documented anchor) ----
say("\n-- anchor check (fear_lin) --")
chk <- function(lab, got, exp, tol) { ok <- abs(got - exp) <= tol
  say("   %-34s got=%.4f exp~%.3f %s", lab, got, exp, ifelse(ok, "OK", "*** DEVIATES ***"))
  if (!ok) flags <<- c(flags, lab) }
gf <- function(dv, role) out[out$dv == dv & out$fear_coding == "fear_lin" & out$role == role, ]
chk("RD focal est",        gf("RD","focal")$est, 0.025, 0.004)
chk("RD focal p",          gf("RD","focal")$p,   0.101, 0.03)
chk("RD focal SE",         gf("RD","focal")$se,  0.015, 0.004)
chk("SI focal p",          gf("SI","focal")$p,   0.199, 0.05)
chk("RD competing p",      gf("RD","competing")$p, 0.028, 0.02)
chk("SI competing p",      gf("SI","competing")$p, 0.97, 0.05)
chk("RD SE inflation",     gf("RD","focal")$se_inflation, 2.5, 0.6)
say("\n%s", if (length(flags)) sprintf("*** %d anchor deviation(s): %s -- REVIEW", length(flags), paste(flags, collapse="; "))
    else "all fear_lin anchors within tolerance (faithful re-run)")
say("note: fear_bin uses (1 + fear_bin | ctrcode); the notes documented only the fear_lin refit, so fear_bin is the analogous extension (no anchor).")
cat("\n== done ==\n")
