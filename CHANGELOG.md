# Changelog

Package history. Engine-level notes are in [docs/release_notes/MODEL_CHANGELOG.md](docs/release_notes/MODEL_CHANGELOG.md).

## 1.2.0 — 27 Aug 2026

Unified Balbix IT impact acceptance (**Outcome A**) and IT golden re-freeze:

- Per-driver Balbix severity, channel-comonotonic dependency, corrected Direct Loss of Funds reporting (accepted; see `docs/validation/BALBIX_UNIFIED_IMPACT_ACCEPTANCE.md`).
- **IT fixtures re-frozen:** `regression_it_fs.json` (50k regression) and `regression_it_fs_500k.json` (500k production). OT fixtures unchanged.
- Production simulation count remains **500,000**; VaR 95 / VaR 99 precision exception documented (not reclassified as Pass).
- `LOSS_BLOCK_RHO = 0.5` and direct-loss calibration remain working priors.
- Fix: `freeze_goldens.py` native IT pack path (`sector_packs/IT`).

## 1.1.2 — 26 Aug 2026

OT pack `09 Scenario Parameters` restructured to a row-oriented table (`DOWNTIME_DAYS`, `CAPACITY_AFFECTED` only). IT enterprise parameter columns removed from all OT packs. OT engine now loads scenario downtime/capacity from the pack (fail-closed). IT / Financial Services pack unchanged. No recalibration of retained OT values.

## 1.1.1 — 25 Aug 2026

Repository hygiene only: documentation grouped under `docs/`, pytest config moved into `pyproject.toml`, `.gitignore` expanded. No methodology, calibration, or simulation change.

## 1.1.0 — 24 Aug 2026

Coordinated IT/OT package restructure:

- Model domain is an explicit Run Setup selection; Sector is filtered by domain.
- Four external sector packs under `sector_packs/IT` and `sector_packs/OT`. OT packs are extracted from the former embedded sheets; numerical calibration is copied, not recalibrated. OT pack workbooks use the same 00–18 sheet names and table chrome as the Financial Services IT pack.
- Combined workbook tabs use domain and ownership labels. Pack/core/calc sheets are Advanced / Read Only.
- Runner loads and validates packs from `config/sector_pack_registry.json` and fails closed if a pack is missing or mismatched.
- Rebuild from code: `python -m crq rebuild-workbook`.

See `docs/methodology/SHEET_NAME_MAPPING.md`, `docs/methodology/ASSUMPTION_OWNERSHIP.md`, `docs/methodology/OT_PACK_MIGRATION.md`.

No undocumented methodology change. Production 500k goldens should be re-checked with `python -m crq validate-release --production`.

## 1.0.0 — 23 Aug 2026

Production release candidate for the combined package. Dual-engine router. Frozen 500,000-year goldens for FS, PG, EA, MF. Authoritative Python Output Bridge. `python -m crq validate-release [--production]`.

**Acceptance: A — PRODUCTION READY** (Excel visual UAT is user-owned and out of scope). Control What-If validated at N=500,000 for all four sectors. See `docs/release_notes/PRODUCTION_READINESS_REPORT.md`.

OT engine patch **1.7.1** for optional OI prevent-barrier overlay (identity when unused).

## 1.0.0-rc — 23 Aug 2026

Independent review of package v0.3; fail-closed and security controls; **not** accepted as production until 500k goldens and Bridge writes.

## 0.3

Combined workbook + IT v1.1.1 + OT v1.7 as originally supplied.
