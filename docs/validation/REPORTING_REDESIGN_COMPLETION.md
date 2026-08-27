# Reporting redesign — final completion report

## 1. IT Financial Services golden drift

**Root cause (Outcome B):** Sector-pack actor weights for Financial Services (`FS-v1.1.1`) changed in place without a pack-version bump (Nation-state 12%→10%, Cybercriminal 68%→80%, Insider 10%→8%, Hacktivist 10%→2%). Frequency/severity path maths were unchanged on the frozen input; ~16% AAL drop follows from the mix shift.

**Resolution:** Fixture `tests/fixtures/regression_it_fs.json` re-frozen after documented reconciliation; engine not reverted. Evidence: `docs/validation/IT_FS_GOLDEN_DRIFT_ROOT_CAUSE.md`.

## 2. OT sensitivity coverage

Live OT sensitivities (when `CRQ_RUN_SENSITIVITY=1`): frequency, downtime, capacity, revenue, restoration/non-BI, **actor-mix** (NS ×1.2 renormalised), **route applicability** (close first enabled configurable gate), **stage/barrier priors** (±20% clipped to [0,1]). Empty list when sensitivity is off (no stale zeros). Tests: `tests/unit/test_ot_sensitivity_shocks.py`.

## 3. Pytest

Complete suite: **129 passed** (re-confirmed green after OT narrative shadowing fix). Runtime ~107–118s. Log: `outputs/pytest_complete_suite.txt`.

## 4. Tier-3 (500k)

### Financial Services (IT)
- Basis: Prudent; controls: baseline+packages; insurance: active
- Seed: 20260821; N: 500,000; runtime: 8.89s
- AAL: 1,154,481.24; VaR95: 6,177,328.63; TVaR95: 19,010,754.82; VaR99: 24,046,135.31; TVaR99: 47,738,116.76
- AAL SE: 9,497.51
- Packages: 4; Target package AAL: 719651.6502447224

### Power Generation (OT)
- Basis: Prudent; controls: baseline+packages; insurance: active
- Seed: 20260821; N: 500,000; runtime: 7.85s
- AAL: 1,806,788.87; VaR95: 981,576.16; TVaR95: 36,125,774.60; VaR99: 46,314,486.35; TVaR99: 122,027,090.61
- AAL SE: 25,427.47
- Packages: 4; Target package AAL: 1806788.8664876083

## 5. Tier-2 vs Tier-3 convergence

### Financial Services
- aal: Δ%=+3.87% (tol ±5%) PASS
- var95: Δ%=+4.16% (tol ±8%) PASS
- tvar95: Δ%=+3.25% (tol ±12%) PASS
- var99: Δ%=+4.76% (tol ±10%) PASS
- tvar99: Δ%=+7.25% (tol ±15%) PASS

### Power Generation
- aal: Δ%=-0.48% (tol ±5%) PASS
- var95: Δ%=-26.95% (tol ±35%) PASS
- tvar95: Δ%=-0.46% (tol ±12%) PASS
- var99: Δ%=-4.24% (tol ±10%) PASS
- tvar99: Δ%=-3.06% (tol ±15%) PASS

Machine-readable: `outputs/tiered_e2e/tier3_report.json`. Human: `outputs/tiered_e2e/tier3_convergence.md`.

## 6. Excel QA

- Excel 16.106.3 on darwin 26.5.2 (macOS): **PASS** (structural + opened in Excel).
- Fixed during QA: OT executive narrative used overwritten actor-loop VaR locals (`v95`/`v99`); now matches Prudent headline cards.
- Detail: `outputs/visual_qa/excel_manual_qa_report.md`.

## 7. Remaining limitations

- Pack content can change without `PACK_VERSION` bump (process debt).
- OT Foundation package can raise AAL when uplifting from higher maturity to Developing (package semantics).
- OT Target/User-defined may match baseline when controls are already at Managed.
- Sparse OT VaR 95 needs wider Tier-2→Tier-3 tolerance (±35%).
- Cursor→Excel Apple Events Automation is blocked on this host (-1743); visual confirmation used openpyxl + opening files in Excel.
- Governed control-cost inputs were out of scope for this pass.

## 8. Validated workbook paths

- `outputs/tiered_e2e/tier3_prod_Financial_Services.xlsx`
- `outputs/tiered_e2e/tier3_prod_Power_Generation.xlsx`
- Tier-2 references: `outputs/tiered_e2e/tier2_medium_*.xlsx`
