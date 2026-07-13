# 10_robustness_export.R
# =============================================================================
# GAPS #1 — export ALL fixed-effect coefficients for the 14 robustness rungs
# persisted in script08_models.rds (robustness_panel.csv carries only
# N/singular/fallback; the estimates live only in the .rds).
#
# NO refitting: reads fitted objects only. Cross-checks each rung's model-derived
# N / country count against robustness_panel.csv (hard check); reports mismatches
# and skips that rung's export.
#
# Reads : v2_prep/output/script08_models.rds, v2_prep/output/robustness_panel.csv
# Writes: v2_prep/output/robustness_coefs.csv
#         (rung_label, dv, term, est, se, df, p, df_basis, isSingular, fallback, n, countries)
# Does NOT commit.
# =============================================================================

suppressPackageStartupMessages({ library(lme4); library(lmerTest) })

OUT   <- normalizePath("v2_prep/output")
rds   <- readRDS(file.path(OUT, "script08_models.rds"))
panel <- read.csv(file.path(OUT, "robustness_panel.csv"), stringsAsFactors = FALSE)

LOG <- character(0); say <- function(...) { m <- sprintf(...); LOG <<- c(LOG, m); cat(m, "\n") }
say("== 10_robustness_export.R (%s) ==", as.character(Sys.time()))

# ---- per-rung model N / countries (for the hard check) ----------------------
model_n_ctry <- function(m) {
  if (inherits(m, "merMod")) {
    n  <- stats::nobs(m)
    fl <- m@flist[["ctrcode"]]
    c(n = n, ctry = nlevels(droplevels(fl)))
  } else if (inherits(m, "WeMixResults")) {
    n <- tryCatch(length(m$resid), error = function(e) NA_integer_)
    ct <- tryCatch({
      g <- m$ngroups
      v <- suppressWarnings(as.integer(unlist(g)))
      v <- v[!is.na(v)]
      # level-2 group count = the count that is not the total obs (< n)
      cand <- v[v > 1 & v < n]
      if (length(cand)) max(cand) else NA_integer_
    }, error = function(e) NA_integer_)
    c(n = n, ctry = ct)
  } else c(n = NA_integer_, ctry = NA_integer_)
}

# ---- coefficient extraction (lmer vs WeMix) ---------------------------------
extract_coefs <- function(m) {
  if (inherits(m, "merMod")) {
    co <- summary(m)$coefficients
    data.frame(term = rownames(co), est = co[, "Estimate"], se = co[, "Std. Error"],
               df = if ("df" %in% colnames(co)) co[, "df"] else NA_real_,
               p  = co[, ncol(co)], row.names = NULL)
  } else if (inherits(m, "WeMixResults")) {
    est <- m$coef
    se  <- if (!is.null(names(m$SE)) && all(names(est) %in% names(m$SE))) m$SE[names(est)] else m$SE[seq_along(est)]
    est <- as.numeric(est); se <- as.numeric(se)
    tval <- est / se
    data.frame(term = names(m$coef), est = est, se = se, df = NA_real_,
               p = 2 * stats::pnorm(-abs(tval)), row.names = NULL)   # normal approx
  } else NULL
}

df_basis_for <- function(m, fallback) {
  if (inherits(m, "WeMixResults")) return("normal_approx (WeMix pseudo-ML; no Satterthwaite df)")
  if (isTRUE(fallback))            return("Satterthwaite (random-INTERCEPT fallback #23; L2xL1 df basis differs from rand-slope)")
  "Satterthwaite (random-slope; L2xL1 ~20 between-country df)"
}

rows <- list()
for (r in rds$robustness) {
  lab <- r$label
  prow <- panel[panel$label == lab, ]
  if (!nrow(prow)) { say("*** no panel row for rung '%s' -> SKIP", lab); next }
  m <- r$model
  if (is.null(m)) { say("*** rung '%s' has NULL model (%s) -> SKIP", lab, r$used); next }

  # hard check: model-derived N/countries vs panel
  mc <- model_n_ctry(m)
  n_ok  <- !is.na(mc["n"])  && mc["n"]  == prow$n
  c_ok  <- !is.na(mc["ctry"]) && mc["ctry"] == prow$countries
  if (!n_ok || (!c_ok && !is.na(mc["ctry"]))) {
    say("*** HARD-CHECK MISMATCH rung '%s': model N=%s ctry=%s vs panel N=%s ctry=%s -> STOP (skip rung)",
        lab, mc["n"], mc["ctry"], prow$n, prow$countries)
    next
  }
  if (is.na(mc["ctry"])) say("   note: rung '%s' countries not model-derivable (%s); N check passed (%s), carrying panel countries=%d",
                             lab, paste(class(m), collapse=","), mc["n"], prow$countries)

  cf <- extract_coefs(m)
  if (is.null(cf)) { say("*** rung '%s' unknown model class (%s) -> SKIP", lab, paste(class(m), collapse=",")); next }
  cf$rung_label <- lab; cf$dv <- prow$dv
  cf$df_basis   <- df_basis_for(m, prow$fallback)
  cf$isSingular <- prow$isSingular; cf$fallback <- prow$fallback
  cf$n <- prow$n; cf$countries <- prow$countries
  rows[[length(rows) + 1]] <- cf[, c("rung_label","dv","term","est","se","df","p",
                                     "df_basis","isSingular","fallback","n","countries")]
  say("   rung '%s' (%s): %d terms exported | df_basis=%s", lab, prow$dv, nrow(cf),
      sub(" \\(.*", "", cf$df_basis[1]))
}

out <- do.call(rbind, rows)
write.csv(out, file.path(OUT, "robustness_coefs.csv"), row.names = FALSE)
say("\nwrote robustness_coefs.csv: %d rows across %d rungs (panel has 14)",
    nrow(out), length(unique(out$rung_label)))
say("rungs exported: %s", paste(sort(unique(out$rung_label)), collapse=" | "))
# focal aiie_cwc across rungs (quick eyeball)
foc <- out[out$term == "aiie_cwc", c("rung_label","dv","est","se","p","df_basis")]
say("\nfocal aiie_cwc by rung:")
for (i in seq_len(nrow(foc))) say("   %-36s %-10s est=%+.5f se=%.5f p=%.4g",
    foc$rung_label[i], foc$dv[i], foc$est[i], foc$se[i], foc$p[i])
writeLines(LOG, file.path(OUT, "10_rung_export.log"))
cat("\n== done ==\n")
