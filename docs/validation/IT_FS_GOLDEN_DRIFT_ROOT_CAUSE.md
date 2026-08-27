# IT Financial Services golden drift — root cause

Date: 2026-08-26  
Case: `tests/integration/test_it_financial_services.py` vs `tests/fixtures/regression_it_fs.json`  
Pack: `FS-v1.1.1` (`sector_packs/IT/IT_CRQ_Sector_Pack_Financial_Services_v1_1_1.xlsx`)

## Decision: Outcome B (intentional pack calibration; re-freeze fixture)

The ~16% AAL reduction is **not** an accidental engine regression. It is explained entirely by an **actor-mix recalibration inside the FS sector pack** while `PACK_ID` / `PACK_VERSION` remained `FS-v1.1.1` / `1.1.1`.

## Controlled comparison

Same frozen staged IT input (`_work/golden_freeze/it_stage/it_input.xlsx`), seed `20260821`, exposure off, prudence 1.25, λ = 1:

| Quantity | Freeze result (Aug 23 engine×pack) | Current engine × current pack | Notes |
|----------|-------------------------------------|-------------------------------|-------|
| Σ attempts | 1.0 | 1.0 | Unchanged |
| Σ P(success)×attempt (event freq) | 0.12094386 | 0.10842823 | −10.35% |
| Analytic AAL | 1,046,974 | 915,409 | −12.57% |
| Mean event severity (AAL/event) | unchanged cell-by-cell | unchanged | **0 mean diffs** |
| Path P(success) / duration / exposure / direct / impact | unchanged | unchanged | **0 path-factor diffs** |

Attempt mix (campaign frequency by actor):

| Actor | Freeze (old pack weights) | Current pack weights | Δ |
|-------|---------------------------|----------------------|---|
| Nation-state | 0.12 | 0.10 | −0.02 |
| Cybercriminal | 0.68 | 0.80 | +0.12 |
| Malicious insider | 0.10 | 0.08 | −0.02 |
| Hacktivist | 0.10 | 0.02 | −0.08 |

Current pack sheet `02 Actor Weights` documents the **proposed** mix **10% / 80% / 8% / 2%** with Verizon DBIR / Mandiant / Microsoft rationale (Evidence Grade D working prior). Scenario attempt shares shift only as the actor-weighted average of unchanged actor→scenario propensities.

## Identity checks

- Analytic AAL identity holds both eras: `Σ(event_rate × mean severity)` with cell success/severity unchanged.
- Simulated AAL at N=50k reconciles to analytic within MC tolerance (~2%): e.g. current sim best AAL 897,063 vs analytic 915,409.
- Fixture `actor_aal` / `scenario_aal` were **Prudent-view** decompositions (sum = prudent AAL), not Best Estimate.

## Why not Outcome A

Re-running the **exact freeze input** through the current engine reproduces the new (lower) frequencies. Workbook controls, exposure, λ, seed, and path success are identical. Restoring the old fixture without restoring the old actor weights would disagree with the governed pack.

## Fixture action

- Previous fixture retained historically in this note and git history.
- `tests/fixtures/regression_it_fs.json` re-frozen to current pack×engine at N=50k, seed 20260821, with **all five** financial metrics for Best Estimate and Prudent.
- **Process note:** pack content changed without bumping `PACK_VERSION`; future calibrations should bump pack version when actor weights change.

## Expected tolerance

Integration test continues to allow 2% relative tolerance on AAL at N=50k (Monte Carlo). Exact metric keys are asserted where stored.
