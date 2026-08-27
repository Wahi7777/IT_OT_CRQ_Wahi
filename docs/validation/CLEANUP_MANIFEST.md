# Repository cleanup manifest

**Date:** 2026-08-27
**Scope:** Disposable caches, logs, and verified-redundant staging only.
**Note:** Workspace has no `.git`; recovery for deleted items is by regeneration, not git history.

| Path | Action | Reason/evidence | Recovery location, if deleted |
| ---- | ------ | --------------- | ----------------------------- |
| `.DS_Store` | **Deleted** | OS junk; regeneratable | OS regenerates; not in VCS |
| `assessments/.DS_Store` | **Deleted** | OS junk; regeneratable | OS regenerates; not in VCS |
| `sector_packs/.DS_Store` | **Deleted** | OS junk; regeneratable | OS regenerates; not in VCS |
| `docs/.DS_Store` | **Deleted** | OS junk; regeneratable | OS regenerates; not in VCS |
| `model/.DS_Store` | **Deleted** | OS junk; regeneratable | OS regenerates; not in VCS |
| `.pytest_cache` | **Deleted** | Tool cache; regeneratable by pytest/ruff | Recreate by running pytest/ruff |
| `.ruff_cache` | **Deleted** | Tool cache; regeneratable by pytest/ruff | Recreate by running pytest/ruff |
| `tests/__pycache__` | **Deleted** | Python bytecode cache | Recreated on import |
| `scripts/__pycache__` | **Deleted** | Python bytecode cache | Recreated on import |
| `src/ot_crq/__pycache__` | **Deleted** | Python bytecode cache | Recreated on import |
| `src/crq/__pycache__` | **Deleted** | Python bytecode cache | Recreated on import |
| `src/it_crq/__pycache__` | **Deleted** | Python bytecode cache | Recreated on import |
| `src/it_ot_crq/__pycache__` | **Deleted** | Python bytecode cache | Recreated on import |
| `src/it_ot_crq/reporting/__pycache__` | **Deleted** | Python bytecode cache | Recreated on import |
| `src/crq/impact/__pycache__` | **Deleted** | Python bytecode cache | Recreated on import |
| `tests/unit/__pycache__` | **Deleted** | Python bytecode cache | Recreated on import |
| `tests/security/__pycache__` | **Deleted** | Python bytecode cache | Recreated on import |
| `tests/integration/__pycache__` | **Deleted** | Python bytecode cache | Recreated on import |
| `tests/regression/__pycache__` | **Deleted** | Python bytecode cache | Recreated on import |
| `outputs/pytest_complete_suite.txt` | **Deleted** | Disposable pytest/console log; superseded by balbix_acceptance evidence and fresh pytest | Re-run pytest |
| `outputs/pytest_final.txt` | **Deleted** | Disposable pytest/console log; superseded by balbix_acceptance evidence and fresh pytest | Re-run pytest |
| `outputs/pytest_golden_ot_sens.txt` | **Deleted** | Disposable pytest/console log; superseded by balbix_acceptance evidence and fresh pytest | Re-run pytest |
| `outputs/pytest_golden_sens.txt` | **Deleted** | Disposable pytest/console log; superseded by balbix_acceptance evidence and fresh pytest | Re-run pytest |
| `outputs/pytest_it_golden.txt` | **Deleted** | Disposable pytest/console log; superseded by balbix_acceptance evidence and fresh pytest | Re-run pytest |
| `outputs/pytest_suite.txt` | **Deleted** | Disposable pytest/console log; superseded by balbix_acceptance evidence and fresh pytest | Re-run pytest |
| `outputs/pytest_suite_full.txt` | **Deleted** | Disposable pytest/console log; superseded by balbix_acceptance evidence and fresh pytest | Re-run pytest |
| `outputs/pytest_suite_summary.txt` | **Deleted** | Disposable pytest/console log; superseded by balbix_acceptance evidence and fresh pytest | Re-run pytest |
| `outputs/pytest_tvar_fix_suite.txt` | **Deleted** | Disposable pytest/console log; superseded by balbix_acceptance evidence and fresh pytest | Re-run pytest |
| `outputs/pytest_junit.xml` | **Deleted** | Disposable pytest/console log; superseded by balbix_acceptance evidence and fresh pytest | Re-run pytest |
| `outputs/RAKBANK_rerun_console.txt` | **Deleted** | Disposable pytest/console log; superseded by balbix_acceptance evidence and fresh pytest | Re-run pytest |
| `outputs/_balbix_verify_rakbank.xlsx` | **Deleted** | Ephemeral underscore verify staging; not authoritative acceptance evidence | Re-run verification scripts |
| `outputs/_balbix_verify_rakbank_model.xlsx` | **Deleted** | Ephemeral underscore verify staging; not authoritative acceptance evidence | Re-run verification scripts |
| `outputs/_balbix_verify_rakbank_results.xlsx` | **Deleted** | Ephemeral underscore verify staging; not authoritative acceptance evidence | Re-run verification scripts |
| `outputs/_pg_verify.xlsx` | **Deleted** | Ephemeral underscore verify staging; not authoritative acceptance evidence | Re-run verification scripts |
| `outputs/_balbix_pack_smoke` | **Deleted** | Temporary pack-smoke model copies; regeneratable via router configure_run | Re-run four-pack smoke |
| `assessments/_pg_verify.xlsx` | **Deleted** | Temporary PG verify assessment copy (underscore); not a customer assessment | Copy template again if needed |
| `outputs/balbix_acceptance/blockers_console.log` | **Deleted** | Regeneratable staging, console echo, failed refresh attempt, or duplicate non-final 500k workbook (final retained) | scripts/balbix_* or acceptance ladder |
| `outputs/balbix_acceptance/statistical_review_console.log` | **Deleted** | Regeneratable staging, console echo, failed refresh attempt, or duplicate non-final 500k workbook (final retained) | scripts/balbix_* or acceptance ladder |
| `outputs/balbix_acceptance/_it_stage_500000_20260821.xlsx` | **Deleted** | Regeneratable staging, console echo, failed refresh attempt, or duplicate non-final 500k workbook (final retained) | scripts/balbix_* or acceptance ladder |
| `outputs/balbix_acceptance/_it_stage_2000_20260821.xlsx` | **Deleted** | Regeneratable staging, console echo, failed refresh attempt, or duplicate non-final 500k workbook (final retained) | scripts/balbix_* or acceptance ladder |
| `outputs/balbix_acceptance/_it_stage_50000_20260821.xlsx` | **Deleted** | Regeneratable staging, console echo, failed refresh attempt, or duplicate non-final 500k workbook (final retained) | scripts/balbix_* or acceptance ladder |
| `outputs/balbix_acceptance/pg_check.xlsx` | **Deleted** | Regeneratable staging, console echo, failed refresh attempt, or duplicate non-final 500k workbook (final retained) | scripts/balbix_* or acceptance ladder |
| `outputs/balbix_acceptance/pg_check_out.xlsx` | **Deleted** | Regeneratable staging, console echo, failed refresh attempt, or duplicate non-final 500k workbook (final retained) | scripts/balbix_* or acceptance ladder |
| `outputs/balbix_acceptance/pg_hash.xlsx` | **Deleted** | Regeneratable staging, console echo, failed refresh attempt, or duplicate non-final 500k workbook (final retained) | scripts/balbix_* or acceptance ladder |
| `outputs/balbix_acceptance/pg_frozen_refresh.xlsx` | **Deleted** | Regeneratable staging, console echo, failed refresh attempt, or duplicate non-final 500k workbook (final retained) | scripts/balbix_* or acceptance ladder |
| `outputs/balbix_acceptance/rakbank_bridge_model.xlsx` | **Deleted** | Regeneratable staging, console echo, failed refresh attempt, or duplicate non-final 500k workbook (final retained) | scripts/balbix_* or acceptance ladder |
| `outputs/balbix_acceptance/rakbank_model_n500000.xlsx` | **Deleted** | Regeneratable staging, console echo, failed refresh attempt, or duplicate non-final 500k workbook (final retained) | scripts/balbix_* or acceptance ladder |
| `outputs/balbix_acceptance/rakbank_out_n500000.xlsx` | **Deleted** | Regeneratable staging, console echo, failed refresh attempt, or duplicate non-final 500k workbook (final retained) | scripts/balbix_* or acceptance ladder |
| `_work/lec_chart_smoke.xlsx` | **Deleted** | Ad-hoc smoke workbook; freeze evidence lives under _work/golden_freeze/ | Re-stage from model/ if needed |
| `_work/it_input.xlsx` | **Deleted** | Ad-hoc smoke workbook; freeze evidence lives under _work/golden_freeze/ | Re-stage from model/ if needed |
| `_work/it_result.xlsx` | **Deleted** | Ad-hoc smoke workbook; freeze evidence lives under _work/golden_freeze/ | Re-stage from model/ if needed |

## Retained (uncertain or required)

| Path | Why retained |
| ---- | ------------ |
| `_work/golden_freeze/` | Referenced by freeze scripts, UAT checklist, IT FS drift root-cause |
| `_work/whatif_freeze/` | Referenced by tests/regression/freeze_whatifs.py |
| `_work/ot09_baseline/` | OT-09 scenario-parameter migration evidence; ownership unclear |
| `_work/ot09_after/` | OT-09 after-migration e2e evidence; ownership unclear |
| `outputs/tiered_e2e/` | Cited by QA docs and excel_visual_qa.py |
| `outputs/visual_qa/` | Cited by REPORTING_REDESIGN_COMPLETION.md |
| `outputs/visual_qa_reporting_suite.xlsx` | Standalone visual QA artefact; not proven disposable |
| `outputs/Power_Generation.xlsx` | May be customer/run output; not proven disposable |
| `outputs/RAKBANK.xlsx` | May be customer/run output; not proven disposable |
| `outputs/RAKBANK_results.xlsx` | Authoritative post-unified customer results |
| `outputs/RAKBANK_results_pre_balbix_unified.xlsx` | Before/after methodology evidence |
| `outputs/balbix_acceptance/*.json` | Acceptance evidence |
| `outputs/balbix_acceptance/rakbank_*_final.xlsx` | Production acceptance workbooks |
| `outputs/balbix_acceptance/rakbank_model_n{25,100,250}k*.xlsx` | N-ladder audit trail paired with summary_n*.json |
| `outputs/balbix_acceptance/verify_*.xlsx / pack_*.xlsx / pg_restored_* / pg_frozen_native_*` | OT pack / PG restore verification trail |
| `docs/validation/BALBIX_UNIFIED_IMPACT_COMPLETION.md` | Distinct early completion notes vs acceptance; retained |
| `assessments/RAKBANK.xlsx` | Authoritative customer assessment input |
| `assessments/Power_Generation.xlsx` | Authoritative customer assessment input |
| `scripts/balbix_acceptance_validation.py` | Maintained acceptance ladder tooling |
| `scripts/balbix_acceptance_blockers.py` | Maintained blockers harness |
| `scripts/balbix_statistical_acceptance_review.py` | Required statistical review harness |

## Size

| | Value |
| --- | --- |
| Before cleanup | 183M (`du -sh`; 187816 KB) |
| After cleanup | 169M (`du -sh`; 173016 KB) |
| Approximate reduction | ~14.5 MB |

## Verification (post-cleanup)

| Check | Result |
| --- | --- |
| Full pytest | **139 passed** (`outputs/balbix_acceptance/pytest_post_cleanup.txt`) |
| Model / pack SHA-256 vs pre-cleanup | **Unchanged** |
| Golden fixture hashes | **Unchanged** (not re-frozen) |
| OT PG / EA / MF smoke vs goldens | **Bit-exact** Prudent AAL |
| IT reconciliations | **PASS** (driver/category AAL & TVaR) |
| CLI `python -m crq` | Help OK; packs resolve and open |
