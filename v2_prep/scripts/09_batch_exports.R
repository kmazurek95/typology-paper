# 09_batch_exports.R
# =============================================================================
# v2 export script: persisted number exports (2026-07-03).
#
# Closes the number gaps blocking §5 of the v2 draft. Every value written here
# lands in a CSV under v2_prep/output/ (provenance rule: no session-only numbers
# enter any doc). Reads the persisted models where possible; refits only where a
# spec was documented-but-not-persisted (drop-item DiD; A/B/C temporal variants;
# H6 worker-status rung).
#
# Reuses Script 08's prep()/build_sample()/L1/L2_main VERBATIM so every frame is
# constructed identically to the main pipeline (08_multilevel_regression.R).
#
# Reads : v2_prep/data/processed/analytic_l1l2.parquet
#         v2_prep/output/script08_models.rds
#         v2_prep/output/headline_inference_M4.csv
#         v2_prep/data/processed/rtm_2022_raw.parquet   (starttime; Task 7)
#         data/processed/typology_positions.csv          (29-country base; Task 5)
# Writes: v2_prep/output/{dropitem_did, batch_2024slope, variant_bases,
#         frame_rosters, aiie_descriptives, mdes_table, h6_stdworker_rung,
#         fieldwork_share}.csv
#
# Does NOT commit. Does NOT overwrite any existing pipeline artifact.
# =============================================================================

suppressPackageStartupMessages({
  library(lme4)
  library(lmerTest)     # Satterthwaite df; contest1D for linear combinations
  library(arrow)
})

LOG <- character(0)
say <- function(...) { m <- sprintf(...); LOG <<- c(LOG, m); cat(m, "\n") }

# ---- paths ------------------------------------------------------------------
find_file <- function(cands) { hit <- cands[file.exists(cands)]; if (!length(hit)) stop("not found: ", cands[1]); normalizePath(hit[1]) }
PARQUET <- find_file(c("v2_prep/data/processed/analytic_l1l2.parquet"))
RDS     <- find_file(c("v2_prep/output/script08_models.rds"))
HEADCSV <- find_file(c("v2_prep/output/headline_inference_M4.csv"))
RAW2022 <- find_file(c("v2_prep/data/processed/rtm_2022_raw.parquet"))
TYPCSV  <- find_file(c("data/processed/typology_positions.csv"))
OUT     <- normalizePath("v2_prep/output")
wr <- function(obj, file) { p <- file.path(OUT, file); write.csv(obj, p, row.names = FALSE); say("wrote %s (%d rows)", file, nrow(obj)) }

# =============================================================================
# prep() / build_sample() / L1 / L2_main  —  VERBATIM from 08_multilevel_regression.R
# =============================================================================
prep <- function(df) {
  scale3 <- function(d, items) {                 # row-mean DV scale, >=2 of 3 items
    M <- as.matrix(d[, items]); k <- rowSums(!is.na(M))
    out <- rowMeans(M, na.rm = TRUE); out[k < 2] <- NA_real_; out
  }
  df$RD <- scale3(df, c("dv_rd_benefits", "dv_rd_ubi", "dv_rd_robottax"))
  df$SI <- scale3(df, c("dv_si_education", "dv_si_retraining", "dv_si_infrastructure"))

  df$edu2 <- factor(ifelse(is.na(df$dem_education_3cat), NA,
                    ifelse(df$dem_education_3cat == 1, "Low", "MedHigh")),
                    levels = c("MedHigh", "Low"))
  df$sex2 <- factor(ifelse(df$dem_sex %in% c(1, 2), df$dem_sex, NA),
                    levels = c(1, 2), labels = c("Male", "Female"))
  df$agegrp    <- factor(df$dem_agegroup)
  df$stdworker <- factor(df$iv_standard_worker, levels = c(1, 2, 3),
                         labels = c("NotEmployed", "Standard", "NonStandard"))
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
mk <- function(dv, rhs) stats::as.formula(paste(dv, "~", paste(rhs, collapse = " + ")))
L1      <- c("aiie_cwc", "edu2", "sex2", "agegrp", "dem_income_decile", "stdworker")
L2_main <- c("z_task_profile", "z_dualization", "gdp_z")
M4_INT  <- c("aiie_cwc:z_task_profile", "aiie_cwc:z_dualization", "z_task_profile:z_dualization")
M5_RHS  <- c(L1, L2_main, M4_INT, "wave", "aiie_cwc:wave", "(1 + aiie_cwc|ctrcode)")   # = fit_M5_6

# helper: pull one coef row (est, se, df, p) tolerant of missing df column
coefrow <- function(m, term) {
  co <- summary(m)$coefficients
  if (!term %in% rownames(co)) return(c(est = NA, se = NA, df = NA, p = NA))
  dfv <- if ("df" %in% colnames(co)) co[term, "df"] else NA_real_
  c(est = unname(co[term, "Estimate"]), se = unname(co[term, "Std. Error"]),
    df = unname(dfv), p = unname(co[term, ncol(co)]))
}
# linear-combination test via Satterthwaite (contest1D); L indexed by fixef names
lincomb <- function(m, weights) {
  fn <- names(lme4::fixef(m)); L <- setNames(rep(0, length(fn)), fn)
  for (nm in names(weights)) { if (!nm %in% fn) stop("term absent for lincomb: ", nm); L[nm] <- weights[nm] }
  r <- lmerTest::contest1D(m, L, ddf = "Satterthwaite")
  c(est = r[["Estimate"]], se = r[["Std. Error"]], df = r[["df"]], t = r[["t value"]], p = r[["Pr(>|t|)"]])
}
issing <- function(m) tryCatch(lme4::isSingular(m, tol = 1e-4), error = function(e) NA)

# =============================================================================
# LOAD
# =============================================================================
say("== 09_batch_exports.R  (%s) ==", as.character(Sys.time()))
raw <- as.data.frame(arrow::read_parquet(PARQUET))
df  <- prep(raw)
say("loaded %d rows | edu2=%s | parquet=%s", nrow(df), paste(levels(df$edu2), collapse="/"), basename(PARQUET))
rds <- readRDS(RDS)
M5_RD <- rds$models[["M5_RD"]]$m
M6_SI <- rds$models[["M6_SI"]]$m

# =============================================================================
# TASK 1 — Drop-item DiD sensitivity  ->  dropitem_did.csv   [LOAD-BEARING]
# Drop dv_rd_benefits (the wave-drifted item; verified RD-ONLY via prep()/08).
# Two defensible frame constructions (both reported; (a) = primary):
#   (a) relist : rebuild RD from {ubi,robottax} with the SAME k>=2 rule (=both
#       items present), then re-derive the listwise frame. N < 39,041.
#   (b) held   : keep the exact 39,041 M5_RD frame, recompute RD from the two
#       items with k>=1. Isolates the item-drop holding the sample fixed.
# =============================================================================
task1 <- function() {
  say("\n-- TASK 1: drop-item DiD --")
  # RD-only guard (self-check against the 08 scale definitions)
  rd_items <- c("dv_rd_benefits","dv_rd_ubi","dv_rd_robottax")
  si_items <- c("dv_si_education","dv_si_retraining","dv_si_infrastructure")
  stopifnot("dv_rd_benefits" %in% rd_items, !("dv_rd_benefits" %in% si_items))
  say("   dv_rd_benefits in RD items? %s ; in SI items? %s (guard passed)",
      "dv_rd_benefits" %in% rd_items, "dv_rd_benefits" %in% si_items)

  scale_k <- function(d, items, kmin) { M <- as.matrix(d[, items, drop = FALSE]); k <- rowSums(!is.na(M))
    o <- rowMeans(M, na.rm = TRUE); o[k < kmin] <- NA_real_; o }
  two <- c("dv_rd_ubi","dv_rd_robottax")

  fit_variant <- function(dcol) {
    d <- build_sample(df, dcol, c(L1, L2_main))
    m <- lmer(mk(dcol, M5_RHS), data = d, REML = TRUE)
    list(m = m, d = d)
  }
  rows <- list()
  # (a) relist, k>=2 (both remaining items) — primary
  df$RD_drop_a <<- scale_k(df, two, kmin = 2)
  ra <- fit_variant("RD_drop_a")
  # (b) held frame (k>=1) — recompute on the exact full-scale RD frame
  df$RD_drop_b <<- scale_k(df, two, kmin = 1)
  # build the held frame = M5_RD full-scale frame, then require RD_drop_b nonmissing (all present by construction)
  d_full <- build_sample(df, "RD", c(L1, L2_main))
  d_b    <- d_full[!is.na(d_full$RD_drop_b), , drop = FALSE]
  rb_m   <- lmer(mk("RD_drop_b", M5_RHS), data = d_b, REML = TRUE)
  rb <- list(m = rb_m, d = d_b)

  emit <- function(tag, frame_desc, kmin, rr) {
    m <- rr$m; d <- rr$d
    base <- coefrow(m, "aiie_cwc")
    inx  <- coefrow(m, "aiie_cwc:wave2024")
    lc   <- lincomb(m, c(aiie_cwc = 1, `aiie_cwc:wave2024` = 1))
    data.frame(frame = tag, frame_desc = frame_desc, kmin = kmin,
      n = nrow(d), countries = length(unique(d$ctrcode)),
      n_vs_39041 = nrow(d) - 39041, isSingular = issing(m),
      base_est = base["est"], base_se = base["se"], base_df = base["df"], base_p = base["p"],
      inter_est = inx["est"], inter_se = inx["se"], inter_df = inx["df"], inter_p = inx["p"],
      slope2024_est = lc["est"], slope2024_se = lc["se"], slope2024_df = lc["df"], slope2024_p = lc["p"],
      df_basis = "Satterthwaite (lmerTest::contest1D)", row.names = NULL)
  }
  out <- rbind(
    emit("a_relist_k2", "rebuild RD from {ubi,robottax}, k>=2 (both items); re-derive listwise frame [PRIMARY]", 2, ra),
    emit("b_held_k1",   "hold exact 39,041 full-scale RD frame; recompute RD from {ubi,robottax}, k>=1", 1, rb)
  )
  say("   (a) N=%d (%+d vs 39,041)  base=%.5f (p=%.3g)  inter=%.5f (p=%.3g)  2024slope=%.5f (p=%.3g) sing=%s",
      out$n[1], out$n_vs_39041[1], out$base_est[1], out$base_p[1], out$inter_est[1], out$inter_p[1],
      out$slope2024_est[1], out$slope2024_p[1], out$isSingular[1])
  say("   (b) N=%d (%+d vs 39,041)  base=%.5f (p=%.3g)  inter=%.5f (p=%.3g)  2024slope=%.5f (p=%.3g) sing=%s",
      out$n[2], out$n_vs_39041[2], out$base_est[2], out$base_p[2], out$inter_est[2], out$inter_p[2],
      out$slope2024_est[2], out$slope2024_p[2], out$isSingular[2])
  say("   anchors (full-scale M5_RD): base -0.02782 (p 3.1e-04); inter +0.01892 (p .0244)")
  wr(out, "dropitem_did.csv")
}

# =============================================================================
# TASK 2 — 2024 combined slopes from persisted models  ->  batch_2024slope.csv
# aiie_cwc + aiie_cwc:wave2024, Satterthwaite df via contest1D.
# =============================================================================
task2 <- function() {
  say("\n-- TASK 2: 2024 combined slopes (persisted M5_RD/M6_SI) --")
  mk_row <- function(dv, m) {
    base <- coefrow(m, "aiie_cwc"); inx <- coefrow(m, "aiie_cwc:wave2024")
    lc   <- lincomb(m, c(aiie_cwc = 1, `aiie_cwc:wave2024` = 1))
    data.frame(dv = dv, model = ifelse(dv=="RD","M5_RD","M6_SI"),
      base_est = base["est"], base_se = base["se"], base_df = base["df"], base_p = base["p"],
      inter_est = inx["est"], inter_se = inx["se"], inter_df = inx["df"], inter_p = inx["p"],
      slope2024_est = lc["est"], slope2024_se = lc["se"], slope2024_df = lc["df"],
      slope2024_t = lc["t"], slope2024_p = lc["p"],
      df_basis = "Satterthwaite (lmerTest::contest1D)", row.names = NULL)
  }
  out <- rbind(mk_row("RD", M5_RD), mk_row("SI", M6_SI))
  for (i in 1:2) say("   %s: base=%.5f  inter=%.5f  ->  2024 slope=%.5f (SE %.5f, df %.1f, p=%.4g)",
      out$dv[i], out$base_est[i], out$inter_est[i], out$slope2024_est[i], out$slope2024_se[i], out$slope2024_df[i], out$slope2024_p[i])
  say("   anchors: RD point ~ -0.0089 ; SI point ~ +0.0392")
  wr(out, "batch_2024slope.csv")
}

# =============================================================================
# TASK 3 — A/B/C temporal-shift variant bases  ->  variant_bases.csv
# Definitions (script_08_implementation_notes.md line 62):
#   A = country-constant shift  = base M5/M6  [= persisted]     RE (1+aiie_cwc|ctr)
#   B = random temporal slope   RE (1 + aiie_cwc + wave | ctr)  [singular expected]
#   C = + wave:z_task_profile + wave:z_dualization              RE (1+aiie_cwc|ctr)
# Not persisted (standalone diagnostic); reconstructed from the documented specs.
# =============================================================================
task3 <- function() {
  say("\n-- TASK 3: A/B/C variant bases (reconstructed) --")
  base_fixed <- c(L1, L2_main, M4_INT, "wave", "aiie_cwc:wave")
  specs <- list(
    A = list(desc = "country-constant shift (= base M5/M6 DiD)", rhs = c(base_fixed, "(1 + aiie_cwc|ctrcode)")),
    B = list(desc = "random temporal slope (1 + aiie_cwc + wave | ctrcode)", rhs = c(base_fixed, "(1 + aiie_cwc + wave|ctrcode)")),
    C = list(desc = "+ wave:z_task_profile + wave:z_dualization", rhs = c(base_fixed, "wave:z_task_profile", "wave:z_dualization", "(1 + aiie_cwc|ctrcode)"))
  )
  rows <- list()
  for (dv in c("RD","SI")) {
    d <- build_sample(df, dv, c(L1, L2_main))
    for (v in names(specs)) {
      m <- suppressWarnings(lmer(mk(dv, specs[[v]]$rhs), data = d, REML = TRUE))
      base <- coefrow(m, "aiie_cwc"); inx <- coefrow(m, "aiie_cwc:wave2024")
      wzd  <- coefrow(m, "wave2024:z_dualization"); if (is.na(wzd["est"])) wzd <- coefrow(m, "z_dualization:wave2024")
      rows[[length(rows)+1]] <- data.frame(variant = v, dv = dv, spec = specs[[v]]$desc,
        n = nrow(d), countries = length(unique(d$ctrcode)), isSingular = issing(m),
        base_est = base["est"], base_se = base["se"], base_df = base["df"], base_p = base["p"],
        inter_est = inx["est"], inter_se = inx["se"], inter_df = inx["df"], inter_p = inx["p"],
        wave_zdual_est = wzd["est"], wave_zdual_p = wzd["p"], row.names = NULL)
    }
  }
  out <- do.call(rbind, rows)
  for (i in seq_len(nrow(out))) say("   %s/%s: base=%+.5f (p=%.3g) inter=%+.5f (p=%.3g) sing=%s",
      out$variant[i], out$dv[i], out$base_est[i], out$base_p[i], out$inter_est[i], out$inter_p[i], out$isSingular[i])
  say("   anchors: aiie_cwc:wave RD +0.019 across A/B/C, SI +0.003; Variant C wave:z_dual RD +0.044 / SI +0.027")
  wr(out, "variant_bases.csv")
}

# =============================================================================
# TASK 5 — frame rosters (23 countries) + cleavage-cell identification
#   -> frame_rosters.csv
# quadrant_signature from median-split of the 29-country typology base.
# =============================================================================
task5 <- function() {
  say("\n-- TASK 5: frame rosters + cleavage cell id --")
  # cleavage cell identity (which two clusters the +0.001 gap difference was over)
  cl <- rds$cleavage
  g <- setNames(cl$gap, cl$cluster_label)
  say("   cleavage gaps: %s", paste(sprintf("%s=%.4f(n%d)", cl$cluster_label, cl$gap, cl$ctrcode), collapse=" "))
  say("   'Cell-4 vs Cell-1' gap diff = Continental(%.4f) - Liberal(%.4f) = %+.5f",
      g["Continental"], g["Liberal"], g["Continental"] - g["Liberal"])

  typ <- read.csv(TYPCSV, stringsAsFactors = FALSE)
  med_task <- median(typ$z_task_profile); med_dual <- median(typ$z_dualization)   # 29-country base
  say("   29-country medians: z_task=%.4f  z_dual=%.4f", med_task, med_dual)

  # 23-country RTM frame = countries with non-NA cluster_label in the analytic frame
  fr <- unique(df[!is.na(df$cluster_label), c("ctrcode","z_task_profile","z_dualization","cluster_label")])
  fr <- fr[order(fr$cluster_label, fr$ctrcode), ]
  hi_task <- fr$z_task_profile >= med_task; hi_dual <- fr$z_dualization >= med_dual
  fr$quadrant_signature <- sprintf("%s_task/%s_dual", ifelse(hi_task,"high","low"), ifelse(hi_dual,"high","low"))
  qmap <- c("high_task/high_dual"="complementary/deep", "high_task/low_dual"="complementary/narrow",
            "low_task/low_dual"="displacement/narrow",  "low_task/high_dual"="displacement/deep")
  fr$descriptive_quadrant <- qmap[fr$quadrant_signature]
  out <- data.frame(country = fr$ctrcode, z_task_profile = fr$z_task_profile, z_dualization = fr$z_dualization,
                    quadrant_signature = fr$quadrant_signature, pipeline_label = fr$cluster_label,
                    descriptive_quadrant = fr$descriptive_quadrant, row.names = NULL)
  out <- out[order(out$descriptive_quadrant, out$country), ]
  say("   frame N countries = %d", nrow(out))
  for (q in sort(unique(out$descriptive_quadrant)))
    say("     %-21s (%s): %s", q, unique(out$pipeline_label[out$descriptive_quadrant==q]),
        paste(out$country[out$descriptive_quadrant==q], collapse=" "))
  # consistency check: does median-split quadrant agree with cluster_label mapping?
  clmap <- c(Continental="complementary/deep", Nordic="complementary/narrow",
             Liberal="displacement/narrow", Southern="displacement/deep")
  mism <- out$country[out$descriptive_quadrant != clmap[out$pipeline_label]]
  say("   median-split vs cluster_label mismatches: %s", if(length(mism)) paste(mism, collapse=" ") else "none")
  wr(out, "frame_rosters.csv")
}

# =============================================================================
# TASK 6 — AIIE descriptives on the M4/M5 (RD) frame  ->  aiie_descriptives.csv
# =============================================================================
task6 <- function() {
  say("\n-- TASK 6: AIIE descriptives (M4/M5 RD frame) --")
  d <- build_sample(df, "RD", c(L1, L2_main))   # = M4_RD / M5_RD frame (39,041)
  say("   frame N=%d countries=%d", nrow(d), length(unique(d$ctrcode)))
  desc <- function(x) { x <- x[!is.na(x)]; q <- stats::quantile(x, c(.25,.75))
    data.frame(n = length(x), mean = mean(x), sd = sd(x), p25 = q[[1]], p75 = q[[2]],
               iqr = q[[2]]-q[[1]], min = min(x), max = max(x)) }
  rows <- list()
  for (v in c("aiie_cwc","aiie_score")) {
    rows[[length(rows)+1]] <- cbind(variable = v, wave = "pooled", desc(d[[v]]))
    for (w in c("2022","2024")) rows[[length(rows)+1]] <- cbind(variable = v, wave = w, desc(d[[v]][d$wave==w]))
  }
  out <- do.call(rbind, rows); out$frame <- "M4/M5 RD frame (39,041; 23 ctry)"
  say("   aiie_cwc pooled: mean=%.4f sd=%.4f IQR=%.4f [min %.3f, max %.3f]",
      out$mean[1], out$sd[1], out$iqr[1], out$min[1], out$max[1])
  wr(out, "aiie_descriptives.csv")
}

# =============================================================================
# TASK 7 — 2022 fieldwork share after ChatGPT release  ->  fieldwork_share.csv
# starttime lives only in the raw 2022 parquet (dropped from the analytic frame).
# =============================================================================
task7 <- function() {
  say("\n-- TASK 7: 2022 fieldwork share (starttime) --")
  r22 <- as.data.frame(arrow::read_parquet(RAW2022, col_select = c("starttime","ctrcode")))
  st  <- as.POSIXct(r22$starttime, format = "%Y-%m-%d %H:%M:%S", tz = "UTC")
  cut <- as.POSIXct("2022-11-30 23:59:59", tz = "UTC")   # strictly after Nov 30
  cut0<- as.POSIXct("2022-11-30 00:00:00", tz = "UTC")   # on/after Nov 30
  frame_ctry <- sort(unique(df$ctrcode[!is.na(df$cluster_label)]))   # 23-country frame
  mk_row <- function(scope, idx) {
    s <- st[idx]; n <- sum(!is.na(s))
    data.frame(scope = scope, n_total = n,
      fielding_start = as.character(min(s, na.rm=TRUE)), fielding_end = as.character(max(s, na.rm=TRUE)),
      n_after_nov30 = sum(s > cut, na.rm=TRUE), share_after_nov30 = mean(s > cut, na.rm=TRUE),
      n_on_or_after_nov30 = sum(s >= cut0, na.rm=TRUE), share_on_or_after_nov30 = mean(s >= cut0, na.rm=TRUE),
      chatgpt_release = "2022-11-30", note = "starttime = datetime of survey start (2022 wave only; 2024 has no timestamp)",
      row.names = NULL)
  }
  out <- rbind(mk_row("full_2022_wave", rep(TRUE, length(st))),
               mk_row("frame_23ctry",   r22$ctrcode %in% frame_ctry))
  for (i in 1:2) say("   %-16s N=%d window[%s .. %s] share_after_Nov30=%.4f (n=%d)",
      out$scope[i], out$n_total[i], substr(out$fielding_start[i],1,10), substr(out$fielding_end[i],1,10),
      out$share_after_nov30[i], out$n_after_nov30[i])
  wr(out, "fieldwork_share.csv")
}

# =============================================================================
# TASK 9 — MDES table  ->  mdes_table.csv
# MDES = (qt(.975, df) + qt(.80, df)) * SE, per-term Satterthwaite df.
# =============================================================================
task9 <- function() {
  say("\n-- TASK 9: MDES table --")
  hi <- read.csv(HEADCSV, stringsAsFactors = FALSE)
  mult <- qt(.975, hi$sat_df) + qt(.80, hi$sat_df)
  out <- data.frame(term = hi$term, DV = hi$dv, SE = hi$sat_se, df = hi$sat_df,
                    multiplier = mult, MDES = mult * hi$sat_se, row.names = NULL)
  for (i in seq_len(nrow(out))) say("   %-24s %s: SE=%.5f df=%.2f mult=%.3f MDES=%.5f",
      out$term[i], out$DV[i], out$SE[i], out$df[i], out$multiplier[i], out$MDES[i])
  say("   anchors (df~20): mult~2.95; RD gamma12 MDES~.0176; RD gamma11 MDES~.0212")
  wr(out, "mdes_table.csv")
}

# =============================================================================
# TASK 10 — AIIE x worker-status rung (EXPLORATORY H6 coarse probe)
#   -> h6_stdworker_rung.csv
# M4 spec + aiie_cwc:stdworker. Standard set as reference so NonStandard-vs-
# Standard is a direct term. NOT the pre-specified three-way. AIIE for Not-
# employed = last/most-recent job's sector (survey instructs retired/out-of-work
# to answer for most recent job; NACE 97 'never employed' -> NA -> dropped).
# =============================================================================
task10 <- function() {
  say("\n-- TASK 10: H6 AIIE x stdworker rung (exploratory) --")
  d10 <- df
  d10$stdworker <- stats::relevel(d10$stdworker, ref = "Standard")   # Standard = reference
  aiie_note <- paste0("AIIE assigned from iv_nace_sector; NACE item instructs retired/out-of-work ",
                      "to answer for MOST RECENT job -> Not-employed AIIE = last-job sector; ",
                      "NACE 97 'never employed'/99 -> NA -> dropped. stdworker ref=Standard.")
  rows <- list()
  for (dv in c("RD","SI")) {
    ds <- build_sample(d10, dv, c(L1, L2_main))
    rhs <- c(L1, L2_main, M4_INT, "aiie_cwc:stdworker", "(1 + aiie_cwc|ctrcode)")
    m <- suppressWarnings(lmer(mk(dv, rhs), data = ds, REML = TRUE))
    tab <- table(ds$stdworker)
    say("   %s frame N=%d  stdworker: %s  sing=%s", dv, nrow(ds),
        paste(sprintf("%s=%d", names(tab), as.integer(tab)), collapse=" "), issing(m))
    for (term in c("aiie_cwc:stdworkerNotEmployed","aiie_cwc:stdworkerNonStandard")) {
      cr <- coefrow(m, term)
      rows[[length(rows)+1]] <- data.frame(dv = dv, term = term,
        contrast = ifelse(grepl("NotEmployed", term), "NotEmployed vs Standard", "NonStandard vs Standard"),
        est = cr["est"], se = cr["se"], df = cr["df"], p = cr["p"],
        n = nrow(ds), countries = length(unique(ds$ctrcode)), isSingular = issing(m),
        notes = aiie_note, row.names = NULL)
      say("     %-32s est=%+.5f se=%.5f df=%.1f p=%.4g", term, cr["est"], cr["se"], cr["df"], cr["p"])
    }
  }
  out <- do.call(rbind, rows)
  wr(out, "h6_stdworker_rung.csv")
}

# =============================================================================
# RUN
# =============================================================================
run1 <- function(f, nm) tryCatch(f(), error = function(e) say("*** ERROR in %s: %s", nm, conditionMessage(e)))
run1(task1, "task1"); run1(task2, "task2"); run1(task3, "task3"); run1(task5, "task5")
run1(task6, "task6"); run1(task7, "task7"); run1(task9, "task9"); run1(task10, "task10")

writeLines(LOG, file.path(OUT, "09_batch_run.log"))
cat("\n== done; log -> v2_prep/output/09_batch_run.log ==\n")
