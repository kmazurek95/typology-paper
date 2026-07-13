# 12_descriptives.R
# =============================================================================
# Table 2 descriptives on each outcome's M4 analysis frame (RD N=39,041;
# SI N=39,453), by wave and pooled. Descriptives only — NO models, no refit.
# Reuses Script 08's prep()/build_sample()/L1/L2_main VERBATIM so the frames are
# constructed identically to the main pipeline.
#
# Reads : v2_prep/data/processed/analytic_l1l2.parquet, model_meta_{RD,SI}.csv,
#         aiie_descriptives.csv (cross-check)
# Writes: v2_prep/output/table2_descriptives.csv  (long: frame, wave, variable, statistic, value)
# Hard check: frame Ns (pooled + per-wave) must match model_meta_*.csv M4 rows exactly.
# Does NOT commit.
# =============================================================================

suppressPackageStartupMessages({ library(lme4); library(lmerTest); library(arrow) })
OUT <- normalizePath("v2_prep/output")
say <- function(...) cat(sprintf(...), "\n")

# ---- prep()/build_sample()/L1/L2_main VERBATIM from 08_multilevel_regression.R -
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
  df
}
build_sample <- function(df, dv, predictors, wave = NULL) {
  d <- if (is.null(wave)) df else df[df$wave == wave, , drop = FALSE]
  need <- c(dv, predictors, "ctrcode", "weight")
  d[stats::complete.cases(d[, need, drop = FALSE]), , drop = FALSE]
}
L1      <- c("aiie_cwc", "edu2", "sex2", "agegrp", "dem_income_decile", "stdworker")
L2_main <- c("z_task_profile", "z_dualization", "gdp_z")

df <- prep(as.data.frame(arrow::read_parquet(normalizePath("v2_prep/data/processed/analytic_l1l2.parquet"))))
say("loaded %d rows", nrow(df))

# ---- descriptives helper (long rows) ----------------------------------------
descr_rows <- function(d, frame, wave, outcome) {
  R <- function(variable, statistic, value) data.frame(frame = frame, wave = wave,
        variable = variable, statistic = statistic, value = value, row.names = NULL)
  o <- list(); add <- function(x) o[[length(o) + 1]] <<- x
  y <- d[[outcome]]
  add(R(paste0(outcome, "_scale"), "mean", mean(y, na.rm = TRUE)))
  add(R(paste0(outcome, "_scale"), "sd",   sd(y, na.rm = TRUE)))
  add(R(paste0(outcome, "_scale"), "n",    sum(!is.na(y))))
  for (v in c("aiie_score", "aiie_cwc")) {
    add(R(v, "mean", mean(d[[v]], na.rm = TRUE)))
    add(R(v, "sd",   sd(d[[v]], na.rm = TRUE)))
  }
  add(R("edu2_low",    "share", mean(d$edu2 == "Low",    na.rm = TRUE)))
  add(R("sex2_female", "share", mean(d$sex2 == "Female", na.rm = TRUE)))
  ag <- prop.table(table(d$agegrp))
  for (lv in names(ag)) add(R(paste0("agegrp_", lv), "share", as.numeric(ag[[lv]])))
  add(R("income_decile", "mean",   mean(d$dem_income_decile, na.rm = TRUE)))
  add(R("income_decile", "median", stats::median(d$dem_income_decile, na.rm = TRUE)))
  sw <- prop.table(table(d$stdworker))
  for (lv in names(sw)) add(R(paste0("stdworker_", lv), "share", as.numeric(sw[[lv]])))
  add(R("frame", "N", nrow(d)))
  do.call(rbind, o)
}

# ---- build M4 frames, emit descriptives, hard-check Ns ----------------------
meta <- rbind(read.csv(file.path(OUT, "model_meta_RD.csv"), stringsAsFactors = FALSE),
              read.csv(file.path(OUT, "model_meta_SI.csv"), stringsAsFactors = FALSE))
rows <- list(); ok <- TRUE
for (dv in c("RD", "SI")) {
  d <- build_sample(df, dv, c(L1, L2_main))                 # = M4 frame
  m4 <- meta[meta$model == paste0("M4_", dv), ]
  n22 <- sum(d$wave == "2022"); n24 <- sum(d$wave == "2024")
  exp_pw <- strsplit(m4$per_wave, "/")[[1]]
  chk_n  <- nrow(d) == m4$n; chk_w <- n22 == as.integer(exp_pw[1]) && n24 == as.integer(exp_pw[2])
  say("HARD CHECK %s: N=%d (meta %d, %s) per-wave %d/%d (meta %s, %s)", dv, nrow(d), m4$n,
      ifelse(chk_n, "OK", "MISMATCH"), n22, n24, m4$per_wave, ifelse(chk_w, "OK", "MISMATCH"))
  if (!chk_n || !chk_w) { ok <- FALSE; say("*** HARD-CHECK MISMATCH for %s -> STOP", dv); next }
  for (w in c("pooled", "2022", "2024")) {
    dw <- if (w == "pooled") d else d[d$wave == w, , drop = FALSE]
    rows[[length(rows) + 1]] <- descr_rows(dw, dv, w, dv)
  }
}
out <- do.call(rbind, rows)
write.csv(out, file.path(OUT, "table2_descriptives.csv"), row.names = FALSE)
say("\nwrote table2_descriptives.csv: %d rows (%s)", nrow(out), if (ok) "all hard checks passed" else "WITH MISMATCH")

# ---- cross-check aiie vs aiie_descriptives.csv (RD frame) -------------------
ad <- read.csv(file.path(OUT, "aiie_descriptives.csv"), stringsAsFactors = FALSE)
say("\ncross-check vs aiie_descriptives.csv (RD frame):")
for (v in c("aiie_score", "aiie_cwc")) for (w in c("pooled", "2022", "2024")) {
  mine <- out[out$frame == "RD" & out$wave == w & out$variable == v & out$statistic == "mean", "value"]
  theirs <- ad[ad$variable == v & ad$wave == w, "mean"]
  d <- abs(mine - theirs)
  say("   %-10s %-6s mean: mine=%.5f theirs=%.5f  |Δ|=%.2e %s", v, w, mine, theirs, d,
      ifelse(d < 1e-6, "MATCH", "*** MISMATCH ***"))
}
# quick eyeball of key shares
for (dv in c("RD","SI")) {
  g <- function(var,stat) out[out$frame==dv & out$wave=="pooled" & out$variable==var & out$statistic==stat, "value"]
  say("   %s pooled: outcome mean=%.3f sd=%.3f | edu_low=%.3f female=%.3f inc_dec median=%.0f | std=%.3f nonstd=%.3f notemp=%.3f",
      dv, g(paste0(dv,"_scale"),"mean"), g(paste0(dv,"_scale"),"sd"), g("edu2_low","share"), g("sex2_female","share"),
      g("income_decile","median"), g("stdworker_Standard","share"), g("stdworker_NonStandard","share"), g("stdworker_NotEmployed","share"))
}
cat("\n== done ==\n")
