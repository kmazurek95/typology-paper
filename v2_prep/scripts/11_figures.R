# 11_figures.R
# =============================================================================
# v2 §5 figures F1–F3. Plotting only — NO refitting.
#   F1 typology positions   (from typology_positions.csv + frame_rosters.csv)
#   F2 per-wave RD slopes    (from coef_table_RD.csv, batch_2024slope.csv, dropitem_did.csv)
#   F3 brms country slopes   (from script08_models.rds brms fits; posteriors persisted)
#
# Every plotted value is persisted to a CSV so figures are regenerable from
# scripts + persisted files alone. Outputs: figures/F{1,2,3}_*.{png,pdf}
#   png 300 dpi, pdf vector; ~5in single-column width; no baked-in titles;
#   colourblind-safe (Okabe–Ito) and greyscale-legible (shape/linetype carry info).
# Does NOT commit.
# =============================================================================

suppressPackageStartupMessages({ library(ggplot2) })
have_repel <- requireNamespace("ggrepel", quietly = TRUE)

OUT <- normalizePath("v2_prep/output")
FIG <- normalizePath("figures", mustWork = FALSE); dir.create(FIG, showWarnings = FALSE, recursive = TRUE)
rd  <- function(f) read.csv(file.path(OUT, f), stringsAsFactors = FALSE)
say <- function(...) cat(sprintf(...), "\n")

# Okabe–Ito
OI <- c(black="#000000", orange="#E69F00", skyblue="#56B4E9", green="#009E73",
        yellow="#F0E442", blue="#0072B2", vermillion="#D55E00", purple="#CC79A7")

base_theme <- theme_bw(base_size = 10) +
  theme(panel.grid.minor = element_blank(),
        plot.title = element_blank(), plot.subtitle = element_blank(),
        legend.position = "top", legend.title = element_text(size = 9),
        legend.margin = margin(0,0,0,0), legend.box.spacing = unit(2,"pt"))

save_fig <- function(p, stem, w, h) {
  ggsave(file.path(FIG, paste0(stem, ".png")), p, width = w, height = h, units = "in", dpi = 300)
  ggsave(file.path(FIG, paste0(stem, ".pdf")), p, width = w, height = h, units = "in")   # vector; no dpi
  say("   wrote %s.{png,pdf} (%.1fx%.1f in)", stem, w, h)
}

# =============================================================================
# F1 — typology positions
# =============================================================================
f1 <- function() {
  say("-- F1 typology --")
  typ <- read.csv(file.path("data","processed","typology_positions.csv"), stringsAsFactors = FALSE)
  fr  <- rd("frame_rosters.csv")                       # 23 in-frame countries
  typ$in_frame <- typ$country_iso3 %in% fr$country
  typ$is_deu   <- typ$country_iso3 == "DEU"
  med_x <- median(typ$z_task_profile); med_y <- median(typ$z_dualization)
  say("   29-country medians: z_task=%.4f z_dual=%.4f | in-frame=%d", med_x, med_y, sum(typ$in_frame))

  rng_x <- range(typ$z_task_profile); rng_y <- range(typ$z_dualization)
  corners <- data.frame(
    x = c(rng_x[2], rng_x[1], rng_x[2], rng_x[1]),
    y = c(rng_y[2], rng_y[2], rng_y[1], rng_y[1]),
    hjust = c(1, 0, 1, 0), vjust = c(1, 1, 0, 0),
    lab = c("complementary/deep", "displacement/deep",
            "complementary/narrow", "displacement/narrow"))

  p <- ggplot(typ, aes(z_task_profile, z_dualization)) +
    geom_hline(yintercept = med_y, linetype = "dashed", colour = "grey55", linewidth = 0.3) +
    geom_vline(xintercept = med_x, linetype = "dashed", colour = "grey55", linewidth = 0.3) +
    geom_text(data = corners, aes(x, y, label = lab, hjust = hjust, vjust = vjust),
              inherit.aes = FALSE, fontface = "italic", size = 3, colour = "grey35") +
    geom_point(aes(shape = in_frame), size = 2.1, colour = "black", fill = "grey70", stroke = 0.5) +
    geom_point(data = subset(typ, is_deu), shape = 23, size = 3.1, colour = OI[["vermillion"]],
               fill = OI[["vermillion"]], stroke = 0.7) +
    scale_shape_manual(values = c(`TRUE` = 19, `FALSE` = 1),
                       labels = c(`TRUE` = "In RTM frame (23)", `FALSE` = "Typology only (6)"),
                       name = NULL) +
    labs(x = "AI task-profile composition  (z_task_profile; higher = more complementarity)",
         y = "Labour-market dualization depth  (z_dualization; higher = deeper)") +
    base_theme
  lab_aes <- aes(label = country_iso3)
  p <- if (have_repel)
    p + ggrepel::geom_text_repel(lab_aes, size = 2.6, max.overlaps = 30, seed = 1,
                                 min.segment.length = 0.2, colour = "grey20")
  else p + geom_text(lab_aes, size = 2.4, vjust = -0.7, check_overlap = TRUE, colour = "grey20")
  p <- p + annotate("text", x = typ$z_task_profile[typ$is_deu], y = typ$z_dualization[typ$is_deu],
                    label = "DEU (diagnostic)", vjust = 2.1, size = 2.7, fontface = "bold",
                    colour = OI[["vermillion"]])
  save_fig(p, "F1_typology", 5.2, 5.0)
}

# =============================================================================
# F2 — per-wave RD exposure slopes under three scale constructions
# =============================================================================
f2 <- function() {
  say("-- F2 per-wave RD slopes --")
  cfr <- rd("coef_table_RD.csv"); b24 <- rd("batch_2024slope.csv"); di <- rd("dropitem_did.csv")
  full22 <- cfr[cfr$model == "M5_RD" & cfr$term == "aiie_cwc", ]
  rdRD   <- b24[b24$dv == "RD", ]
  ra <- di[di$frame == "a_relist_k2", ]; rb <- di[di$frame == "b_held_k1", ]
  mkrow <- function(constr, wave, est, se, df, src)
    data.frame(construction = constr, wave = wave, est = est, se = se, df = df,
               ci_lo = est - qt(.975, df) * se, ci_hi = est + qt(.975, df) * se, source_file = src)
  pd <- rbind(
    mkrow("Full 3-item scale",     "2022", full22$estimate, full22$se, full22$df, "coef_table_RD.csv"),
    mkrow("Full 3-item scale",     "2024", rdRD$slope2024_est, rdRD$slope2024_se, rdRD$slope2024_df, "batch_2024slope.csv"),
    mkrow("Two-item, relist k>=2", "2022", ra$base_est, ra$base_se, ra$base_df, "dropitem_did.csv"),
    mkrow("Two-item, relist k>=2", "2024", ra$slope2024_est, ra$slope2024_se, ra$slope2024_df, "dropitem_did.csv"),
    mkrow("Two-item, held k>=1",   "2022", rb$base_est, rb$base_se, rb$base_df, "dropitem_did.csv"),
    mkrow("Two-item, held k>=1",   "2024", rb$slope2024_est, rb$slope2024_se, rb$slope2024_df, "dropitem_did.csv"))
  write.csv(pd, file.path(OUT, "f2_plotdata.csv"), row.names = FALSE)
  say("   wrote f2_plotdata.csv (%d rows)", nrow(pd))
  for (i in seq_len(nrow(pd))) say("     %-22s %s  est=%+.4f [%.4f, %.4f]",
      pd$construction[i], pd$wave[i], pd$est[i], pd$ci_lo[i], pd$ci_hi[i])

  pd$construction <- factor(pd$construction,
    levels = rev(c("Full 3-item scale","Two-item, relist k>=2","Two-item, held k>=1")))
  dodge <- position_dodge(width = 0.5)
  p <- ggplot(pd, aes(est, construction, shape = wave, colour = wave, fill = wave)) +
    geom_vline(xintercept = 0, linewidth = 0.4, colour = "grey40") +
    geom_errorbar(aes(xmin = ci_lo, xmax = ci_hi), orientation = "y", width = 0.18, linewidth = 0.5, position = dodge) +
    geom_point(size = 2.6, position = dodge, stroke = 0.6) +
    scale_shape_manual(values = c(`2022` = 21, `2024` = 24), name = "Wave") +
    scale_colour_manual(values = c(`2022` = OI[["blue"]], `2024` = OI[["vermillion"]]), name = "Wave") +
    scale_fill_manual(values = c(`2022` = OI[["blue"]], `2024` = OI[["vermillion"]]), name = "Wave") +
    labs(x = "RD exposure slope (aiie_cwc)  with 95% CI", y = NULL) +
    base_theme
  save_fig(p, "F2_perwave_RD_slopes", 5.2, 2.9)
}

# =============================================================================
# F3 — country slope heterogeneity from the brms fits
# =============================================================================
f3 <- function() {
  say("-- F3 brms country slopes --")
  suppressPackageStartupMessages({ library(brms); library(posterior) })
  r <- readRDS(file.path(OUT, "script08_models.rds"))
  if (is.null(r$brms)) { say("   brms fits absent -> SKIP F3"); return(invisible()) }
  probs <- c(.05, .25, .5, .75, .95)
  ex <- function(m, dv) {
    dm <- posterior::as_draws_df(m); b <- dm[["b_aiie_cwc"]]
    cols <- grep("^r_ctrcode\\[.*,aiie_cwc\\]$", names(dm), value = TRUE)
    rows <- lapply(cols, function(col) {
      ctry <- sub("^r_ctrcode\\[(.*),aiie_cwc\\]$", "\\1", col)
      q <- quantile(b + dm[[col]], probs, names = FALSE)
      data.frame(country = ctry, dv = dv, median = q[3], q5 = q[1], q25 = q[2], q75 = q[4], q95 = q[5])
    })
    out <- do.call(rbind, rows)
    qb <- quantile(b, probs, names = FALSE)
    rbind(out, data.frame(country = "_gamma10_fixef", dv = dv,
          median = qb[3], q5 = qb[1], q25 = qb[2], q75 = qb[4], q95 = qb[5]))
  }
  post <- rbind(ex(r$brms$RD, "RD"), ex(r$brms$SI, "SI"))
  rm(r); gc()
  write.csv(post, file.path(OUT, "f3_slope_posteriors.csv"), row.names = FALSE)
  say("   wrote f3_slope_posteriors.csv (%d rows incl. 2 gamma10)", nrow(post))
  g10 <- post[post$country == "_gamma10_fixef", ]
  for (i in 1:2) say("     gamma10 %s median=%+.4f ; country-median SD=%.4f",
      g10$dv[i], g10$median[i],
      sd(post$median[post$dv == g10$dv[i] & post$country != "_gamma10_fixef"]))

  ctry <- post[post$country != "_gamma10_fixef", ]
  ord  <- ctry[order(ctry$dv, ctry$median), ]
  ctry$key <- factor(paste(ctry$dv, ctry$country, sep = "___"), levels = paste(ord$dv, ord$country, sep = "___"))
  gl <- data.frame(dv = g10$dv, x = g10$median)
  p <- ggplot(ctry, aes(y = key)) +
    geom_vline(xintercept = 0, linewidth = 0.4, colour = "grey40") +
    geom_vline(data = gl, aes(xintercept = x), linetype = "dashed", linewidth = 0.4, colour = OI[["vermillion"]]) +
    geom_segment(aes(x = q5, xend = q95, yend = key), linewidth = 0.35, colour = "grey55") +
    geom_segment(aes(x = q25, xend = q75, yend = key), linewidth = 1.1, colour = "black") +
    geom_point(aes(x = median), size = 1.5, colour = "black") +
    facet_wrap(~ dv, scales = "free_y", ncol = 2) +
    scale_y_discrete(labels = function(x) sub("^.*___", "", x)) +
    labs(x = "Country total AIIE slope  (gamma10 + u_j)", y = NULL) +
    base_theme + theme(legend.position = "none")
  save_fig(p, "F3_country_slopes", 5.4, 6.2)
}

run1 <- function(f, nm) tryCatch(f(), error = function(e) say("*** ERROR %s: %s", nm, conditionMessage(e)))
run1(f1, "F1"); run1(f2, "F2"); run1(f3, "F3")
cat("\n== figures done ->", FIG, "==\n")
