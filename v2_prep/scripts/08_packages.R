# 08_packages.R — install/verify the R toolchain for Script 08
# -----------------------------------------------------------------------------
# Run ONCE, in RStudio, where CRAN is reachable. NOTE: in the CLI build
# environment CRAN was unreachable (SSL/cert-chain — the same issue the project
# hit for sdmx.oecd.org / ec.europa.eu), so package installation must be done
# from a session with working network access (e.g. your RStudio).
#
# Windows note: lme4/lmerTest/pbkrtest/clubSandwich/WeMix/arrow/nanoparquet/
# performance/broom.mixed/ggplot2 install from CRAN *binaries* (no Rtools needed).
# brms installs as a binary too, BUT compiling Stan models at fit() time needs a
# C++ toolchain (Rtools45 on Windows), which is NOT currently installed. Until
# Rtools45 is present, brms::brm() will fail at compile; the frequentist path
# (lme4 + lmerTest + pbkrtest + clubSandwich) is fully functional without it.
# -----------------------------------------------------------------------------

options(repos = c(CRAN = "https://cloud.r-project.org"))

pkgs <- c(
  # parquet IO: arrow preferred, nanoparquet a light fallback (Script 08 tries both)
  "arrow", "nanoparquet",
  # frequentist multilevel + small-sample inference (decision-log #23)
  "lme4", "lmerTest", "pbkrtest", "clubSandwich",
  # survey-weighted multilevel robustness (C4)
  "WeMix",
  # Bayesian co-primary for the variance components (#23) -- needs Rtools45 to fit
  "brms",
  # helpers + plotting
  "performance", "broom.mixed", "ggplot2"
)

missing <- setdiff(pkgs, rownames(installed.packages()))
if (length(missing)) {
  message("Installing: ", paste(missing, collapse = ", "))
  install.packages(missing)
} else {
  message("All declared packages already installed.")
}

cat("\nLoad status:\n")
for (p in pkgs) cat(sprintf("  %-14s %s\n", p, requireNamespace(p, quietly = TRUE)))

# C++ toolchain check (for brms / Stan)
has_tools <- tryCatch(pkgbuild::has_build_tools(debug = FALSE), error = function(e) NA)
cat(sprintf("\nC++ build tools (Rtools, needed for brms model compile): %s\n", has_tools))
if (isFALSE(has_tools) || is.na(has_tools)) {
  cat("  -> Install Rtools45: https://cran.r-project.org/bin/windows/Rtools/\n")
  cat("     (or use cmdstanr). Frequentist inference works without it.\n")
}
