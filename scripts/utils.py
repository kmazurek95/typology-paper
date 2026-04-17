"""Shared utilities for the typology paper data pipeline."""

from pathlib import Path

import matplotlib.pyplot as plt

# ── Paths ────────────────────────────────────────────────────────────────────
ROOT_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT_DIR / "data" / "raw"
PROCESSED_DIR = ROOT_DIR / "data" / "processed"
FIGURES_DIR = ROOT_DIR / "figures"
OUTPUT_DIR = ROOT_DIR / "output"

# Ensure output directories exist
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
FIGURES_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ── Country code mappings ────────────────────────────────────────────────────

ISO2_TO_ISO3 = {
    "AT": "AUT", "AU": "AUS", "BE": "BEL", "BG": "BGR", "CA": "CAN",
    "CH": "CHE", "CL": "CHL", "CY": "CYP", "CZ": "CZE", "DE": "DEU",
    "DK": "DNK", "EE": "EST", "EL": "GRC", "ES": "ESP", "FI": "FIN",
    "FR": "FRA", "GB": "GBR", "GR": "GRC", "HR": "HRV", "HU": "HUN",
    "IE": "IRL", "IL": "ISR", "IS": "ISL", "IT": "ITA", "JP": "JPN",
    "KR": "KOR", "LT": "LTU", "LU": "LUX", "LV": "LVA", "ME": "MNE",
    "MK": "MKD", "MT": "MLT", "MX": "MEX", "NL": "NLD", "NO": "NOR",
    "NZ": "NZL", "PL": "POL", "PT": "PRT", "RO": "ROU", "RS": "SRB",
    "SE": "SWE", "SG": "SGP", "SI": "SVN", "SK": "SVK", "TR": "TUR",
    "US": "USA",
}

NAME_TO_ISO3 = {
    "Australia": "AUS", "Austria": "AUT", "Belgium": "BEL", "Bulgaria": "BGR",
    "Canada": "CAN", "Chile": "CHL", "Colombia": "COL", "Costa Rica": "CRI",
    "Croatia": "HRV", "Cyprus": "CYP", "Czech Republic": "CZE", "Czechia": "CZE",
    "Denmark": "DNK", "Estonia": "EST", "Finland": "FIN", "France": "FRA",
    "Germany": "DEU", "Greece": "GRC", "Hungary": "HUN", "Iceland": "ISL",
    "Ireland": "IRL", "Israel": "ISR", "Italy": "ITA", "Japan": "JPN",
    "Korea": "KOR", "South Korea": "KOR", "Latvia": "LVA", "Lithuania": "LTU",
    "Luxembourg": "LUX", "Mexico": "MEX", "Montenegro": "MNE",
    "Netherlands": "NLD", "New Zealand": "NZL", "Norway": "NOR",
    "Poland": "POL", "Portugal": "PRT", "Romania": "ROU", "Serbia": "SRB",
    "Singapore": "SGP", "Slovak Republic": "SVK", "Slovakia": "SVK",
    "Slovenia": "SVN", "Spain": "ESP", "Sweden": "SWE", "Switzerland": "CHE",
    "Türkiye": "TUR", "Turkey": "TUR", "United Kingdom": "GBR",
    "United States": "USA",
}

CNTRYID_TO_ISO3 = {
    36: "AUS", 40: "AUT", 56: "BEL", 124: "CAN", 152: "CHL",
    191: "HRV", 203: "CZE", 208: "DNK", 233: "EST", 246: "FIN",
    250: "FRA", 276: "DEU", 348: "HUN", 372: "IRL", 376: "ISR",
    380: "ITA", 392: "JPN", 410: "KOR", 428: "LVA", 440: "LTU",
    528: "NLD", 554: "NZL", 578: "NOR", 616: "POL", 620: "PRT",
    702: "SGP", 703: "SVK", 724: "ESP", 752: "SWE", 756: "CHE",
    826: "GBR", 840: "USA",
}

ISO3_TO_NAME = {v: k for k, v in NAME_TO_ISO3.items()}
ISO3_TO_NAME.update({
    "CZE": "Czechia", "KOR": "Korea", "SVK": "Slovakia",
    "TUR": "Türkiye", "GBR": "United Kingdom", "USA": "United States",
})

# ── Cluster labels and colours ───────────────────────────────────────────────

CLUSTER_LABELS = {
    1: "Complementary + Narrow gap",
    2: "Complementary + Deep gap",
    3: "Displacement + Narrow gap",
    4: "Displacement + Deep gap",
}

CLUSTER_SHORT = {
    1: "Nordic",
    2: "Continental",
    3: "Liberal",
    4: "Southern",
}

CLUSTER_COLORS = {
    1: "#4477AA",   # blue   — Nordic
    2: "#EE6677",   # red    — Continental
    3: "#228833",   # green  — Liberal
    4: "#CCBB44",   # yellow — Southern
}


def setup_plot_style():
    """Configure matplotlib for clean academic figures."""
    plt.rcParams.update({
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "axes.grid": False,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "font.family": "sans-serif",
        "font.size": 11,
        "axes.labelsize": 12,
        "axes.titlesize": 13,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
        "legend.fontsize": 9,
        "figure.dpi": 150,
        "savefig.dpi": 300,
        "savefig.bbox": "tight",
    })
