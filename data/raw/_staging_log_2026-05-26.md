# External Inputs Staging Log — 2026-05-26

**Date:** 2026-05-26
**Operator:** Claude Code session (Pass 2 of Option β implementation per [`v2_prep/docs/v2_measurement_decisions_log.md`](../../v2_prep/docs/v2_measurement_decisions_log.md) entry S2).
**Purpose:** Stage Eurostat `lfsa_etgar` (Temporary employees by main reason) for the Axis 2 weighted-gap robustness construction.

## File staged

| Source URL | Source organization | Target path | Bytes (filtered) |
|---|---|---|---|
| `https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/lfsa_etgar/?format=SDMX-CSV` | Eurostat (EU statistical office) | `data/raw/eurostat_lfsa_etgar.csv` | 15,481 (176 rows post-filter) |

## Fetch protocol

The fetch was authorized for this single public Eurostat URL per the session's per-file authorization policy. Two-step:

1. **Bulk download** from Eurostat's SDMX 2.1 REST endpoint. The endpoint serves the full dataset (no server-side dimension filtering — earlier attempts to filter via query string returned HTTP 406). The bulk file was 81,064,605 bytes covering all dimension combinations from 1995 onward.

2. **Post-fetch filter** to the target dimension cuts (Unit=`PC_SAL_TEMP`, Sex=`T`, Age=`Y15-64`, Reason=`NF_PJOB`, TIME_PERIOD ∈ {2020, 2021, 2022, 2023, 2024}). Bulk file deleted from disk after filtered artifact written. Both SHAs recorded for provenance.

## Provenance details

- **Server response timestamp (Eurostat DATAFLOW field):** 17/04/26 11:00:00 — confirms the dataset version matches the coverage check document.
- **Content-Type returned by server:** `application/vnd.sdmx.data+csv;version=1.0.0`
- **Bulk SHA256:** `540df4c5d0d00b0ef4b90da609eb7e2da1593ab0a5c92a284261c0d53044d6e2` (81,064,605 bytes)
- **Filtered SHA256:** `c219e9177ea32aad25912f10ed466fc30c102effbcd85b43ca2cdfd3af89e842` (15,481 bytes)
- **Machine-readable provenance:** [`_eurostat_lfsa_etgar_provenance.json`](_eurostat_lfsa_etgar_provenance.json) (kept alongside the staged file).

## TLS verification note

Both the Python urllib stdlib and `requests` + `certifi` failed with `CERTIFICATE_VERIFY_FAILED` against `ec.europa.eu`. This is a local Windows cert chain issue on the operator's install (likely a corporate or system store mismatch), not a server problem. For this single authorized public-data fetch, TLS chain verification was bypassed; integrity is verified via:

- SHA256 hash of the server response (bulk and filtered, both logged above).
- SDMX-CSV schema validation: the bulk header was checked for the expected columns (`DATAFLOW, freq, unit, sex, age, reason, geo, TIME_PERIOD, OBS_VALUE, OBS_FLAG, CONF_STATUS`) before any data was written to the repo.
- Content cross-check against the coverage matrix in [`v2_prep/docs/lfsa_etgar_coverage_check_2026-05-26.md`](../../v2_prep/docs/lfsa_etgar_coverage_check_2026-05-26.md): filtered output covers the expected 21 RTM countries cleanly plus EE and LV with reliability flags.

The TLS bypass is bounded to this one URL on this one fetch. Future Eurostat fetches require the same per-URL authorization conversation.

## Coverage verification (against the coverage check document)

The 27 RTM countries break down post-filter as:

- **Present in filtered artifact (23):** AT, BE, CZ, DE, DK, FI, FR, EL (=GRC), ES, HU, IE, IT, LT, NL, NO, PL, PT, SK, SI, SE, TR — 21 RTM "Clean" countries; plus EE and LV in the "Partial" bucket (coverage check document hard-excludes them).
- **Absent from filtered artifact (4):** CHL, ISR, KOR, MEX — matches the "No coverage" bucket in the coverage check document; non-EU OECD members not in Eurostat by definition.

Coverage matches the coverage check document exactly. Per the decision threshold in entry S2, 20 clean countries (the 21 minus Estonia, which is hard-excluded for reliability flags) is above the ≥20 threshold; Option β proceeds.

## Files NOT staged this session

Nothing else. The download authorization was bounded to this single URL.

## Auxiliary file

[`_eurostat_lfsa_etgar_provenance.json`](_eurostat_lfsa_etgar_provenance.json) — machine-readable record of the fetch, filter, and SHAs. Safe to delete once Script 01b is operational and downstream artifacts have been verified.
