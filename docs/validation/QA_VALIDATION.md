# QA validation

## Tiers

### Fast CI (`python -m crq validate-release` or `pytest tests -q -m "not production"`)

Unit math (ES, TVaR≥VaR, OT stage product, controls), routing, fail-closed, security, OI, workbook integrity (template), IT FS at 50,000 years, OT pack resolve `simulate=False`, OT sim-count guard, snapshot overwrite unit test.

Do not replace this tier with 500k runs.

### Production release (`python -m crq validate-release --production`)

1. Fast suite + ruff + bandit + pip-audit  
2. `tests/regression/freeze_goldens.py` — FS, PG, EA, MF at **N=500,000**, baseline (`run_whatifs=False` for this golden only)  
3. `tests/regression/freeze_whatifs.py` — same four sectors at **N=500,000** with Control What-If on  
4. `pytest -m production` with `CRQ_REQUIRE_GOLDENS=1`

## Dashboard Basis

Default = Prudent. Alternative = Best Estimate. Metric names are basis-independent.

## Excel visual UAT

OUT OF SCOPE for automated release. Structural openpyxl checks remain in CI.  

## Automated vs Excel

| Check | Method |
| --- | --- |
| Engine metrics | Python return dict / JSON goldens |
| Output Bridge B/C and `00 Engine Results` | openpyxl values after run (not formulas) |
| Dashboard displayed KPIs | Excel Full Calc — **operator UAT** |
| Dashboard selected-view cache B71:B78 | Python ENGINE_WRITTEN |

openpyxl formula presence is **not** treated as a calculated result.

## Production-N evidence

See `docs/release_notes/PRODUCTION_READINESS_REPORT.md` and `tests/fixtures/regression_*.json`.

IT 50k fixture `tests/fixtures/regression_it_fs.json` remains the fast golden (AAL ≈ 1.30m on the Prudent basis).
