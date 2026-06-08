"""
Script 00: RTM Ingestion (.dta -> Parquet + JSON metadata)

Thin wrapper around pyreadstat that reads the raw OECD RTM .dta files for
2022 and 2024 and writes per-wave Parquet plus companion JSON metadata.
No cleaning, no recoding, no renaming. The point is to contain the .dta
dependency to one place so downstream scripts can work with fast Parquet.

Inputs
------
- data/OECD_RTM_2022_Public_Use_Microdata/FinalData_dta/FinalData_dta/
    OECD_RTM_2022_Public_Use_Microdata.dta
- data/OECD_RTM_2024_Public_Use_Microdata/OECD_RTM_2024_Public_Use_Microdata/
    OECD_RTM_2024_Public_Use_Microdata/OECD_RTM_2024_Public_Use_Microdata.dta

Outputs
-------
- v2_prep/data/processed/rtm_2022_raw.parquet
- v2_prep/data/processed/rtm_2024_raw.parquet
- v2_prep/data/processed/rtm_2022_meta.json
- v2_prep/data/processed/rtm_2024_meta.json

Invocation
----------
python v2_prep/scripts/00_ingest_rtm.py
"""

import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

import pyreadstat

# ── Paths ──────────────────────────────────────────────────────────────────

ROOT = Path(__file__).resolve().parents[2]
PROCESSED = ROOT / "v2_prep" / "data" / "processed"
PROCESSED.mkdir(parents=True, exist_ok=True)

DTA_PATHS = {
    "2022": ROOT / "data" / "OECD_RTM_2022_Public_Use_Microdata" / "FinalData_dta"
            / "FinalData_dta" / "OECD_RTM_2022_Public_Use_Microdata.dta",
    "2024": ROOT / "data" / "OECD_RTM_2024_Public_Use_Microdata"
            / "OECD_RTM_2024_Public_Use_Microdata"
            / "OECD_RTM_2024_Public_Use_Microdata"
            / "OECD_RTM_2024_Public_Use_Microdata.dta",
}

EXPECTED_N_LOW = 20_000
EXPECTED_N_HIGH = 35_000


def _metadata_to_dict(meta) -> dict:
    """Serialize pyreadstat metadata to a JSON-safe dict.

    Keeps only the keys downstream consumers actually need: variable labels,
    value labels, dtypes, row/column counts, encoding.
    """
    return {
        "n_rows": int(meta.number_rows),
        "n_columns": int(meta.number_columns),
        "column_names": list(meta.column_names),
        "column_labels": dict(zip(meta.column_names, meta.column_labels)),
        # value labels: pyreadstat keys these by "value-label set name" via
        # variable_to_label, then variable_value_labels maps the var to the
        # actual {code: label} dict
        "variable_value_labels": {
            var: {str(k): v for k, v in labels.items()}
            for var, labels in meta.variable_value_labels.items()
        },
        "variable_to_label": dict(meta.variable_to_label),
        "missing_ranges": {
            var: [[float(rng["lo"]), float(rng["hi"])] for rng in ranges]
            for var, ranges in (meta.missing_ranges or {}).items()
        },
        "file_encoding": meta.file_encoding,
        "file_label": meta.file_label,
    }


def ingest_wave(wave: str) -> None:
    src = DTA_PATHS[wave]
    assert src.exists(), f"Missing raw .dta for {wave}: {src}"

    print(f"\n[{wave}] Reading {src}")
    df, meta = pyreadstat.read_dta(str(src), apply_value_formats=False)

    # Sanity checks
    assert EXPECTED_N_LOW < len(df) < EXPECTED_N_HIGH, (
        f"[{wave}] n_rows={len(df)} outside expected band "
        f"({EXPECTED_N_LOW:,}-{EXPECTED_N_HIGH:,}); OECD documentation said ~27,500."
    )
    empty_cols = [c for c in df.columns if df[c].isna().all()]
    assert not empty_cols, f"[{wave}] all-NaN columns found: {empty_cols[:10]}"

    print(f"[{wave}] n_rows={len(df):,}  n_cols={len(df.columns):,}")

    parquet_path = PROCESSED / f"rtm_{wave}_raw.parquet"
    json_path = PROCESSED / f"rtm_{wave}_meta.json"

    df.to_parquet(parquet_path, index=False)
    print(f"[{wave}] Wrote {parquet_path} ({parquet_path.stat().st_size / 1e6:.2f} MB)")

    json_path.write_text(
        json.dumps(_metadata_to_dict(meta), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"[{wave}] Wrote {json_path} ({json_path.stat().st_size / 1e3:.1f} KB)")


def main() -> int:
    for wave in ("2022", "2024"):
        ingest_wave(wave)
    print("\nIngestion complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
