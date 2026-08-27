# Reporting redesign — limitations register

Last updated: 2026-08-26

## Shared metric definitions (do not reopen unless tests fail)

- AAL / VaR 95 / TVaR 95 / VaR 99 / TVaR 99 are defined in `src/crq/metrics.py` and `docs/methodology/FINANCIAL_RISK_METRICS.md`.
- Appetite thresholds are independent of insurance retention (`src/crq/appetite.py`).

## Implemented in this pass

- IT/OT parity for packages, trial-level insurance, five-metric what-ifs, actor/scenario TVaR contributions, loss components, sensitivity flag behaviour.
- Business Impact: Balbix major categories and applicable drivers with shared portfolio-tail contributions; OT non-Balbix consequences flagged as catalogue gaps.
- LEC: VaR 95/99 markers, TVaR explanation, AEP/OEP definitions, zero-loss axis treatment.
- Tiered e2e script: `scripts/tiered_e2e_validation.py`.

## Remaining limitations

1. **OT component taxonomy granularity** — non-BI annual losses are allocated to taxonomy labels by static driver severity weights, not per-driver Monte Carlo paths. AAL and TVaR contributions still reconcile to the aggregate.
2. **OT physical-damage-only sensitivity** — isolated physical-damage driver shocks remain limited; actor-mix (renormalised), facility route closure, and stage-prior ±20% shocks are live `evaluate()` reruns when `CRQ_RUN_SENSITIVITY=1`.
3. **IT operational percentiles** — records/endpoints/services use organisation point exposures when supplied; downtime/capacity percentiles are OT-applicable and omitted for IT (not shown as zero).
4. **IT revenue sensitivity** — implemented via Duration / Direct / Exposure block scales, not a separate revenue ledger path.
5. **Treatment costs** — optional; when absent the UI shows `Cost not provided`. Workbook cost input cells are not yet a dedicated governed input block on every control row.
6. **IT golden (`tests/integration/test_it_financial_services.py`)** — resolved as **Outcome B** on 2026-08-26. Root cause: FS pack actor-mix recalibration 12/68/10/10 → 10/80/8/2 with unchanged path success/severity. See `docs/validation/IT_FS_GOLDEN_DRIFT_ROOT_CAUSE.md`. Fixture re-frozen with five-metric set.
7. **Production freeze bridge tests** — accept legacy sheet titles `00 Output Bridge` / `00 Engine Results` as well as `00 COMMON - *`.
8. **Visual QA** — LibreOffice can export sheet PDFs; Excel chart fidelity (markers, fonts) may differ. Pixel-level Excel inspection remains required for final chart QA.
9. **Tier 3 (500k)** — run explicitly via `--tier 3`; not executed by default in CI. Tiers 1–2 set `CRQ_E2E_ALLOW_OT_N=1` so OT can use reduced simulation counts for smoke/medium wiring checks without weakening the production guard (still enforced when the env flag is unset).
10. **Best Estimate→Prudent bridge** — reconciles metric-level differences; parameter-level sequential attribution is not available (documented on sheet 07).

## Sensitivity flag

When `CRQ_RUN_SENSITIVITY` is unset: sheet 07 shows `Sensitivity analysis not run` and engines return an empty sensitivity list (no stale zeros).
