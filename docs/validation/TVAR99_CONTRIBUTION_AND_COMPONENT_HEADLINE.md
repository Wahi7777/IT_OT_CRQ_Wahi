# TVaR 99 contribution reconciliation & loss-component headline

## Issue 1 — Scenario TVaR 99 “$45m gap”

**Root cause:** Presentation / misreading — **not an engine allocation defect**.

In `outputs/RAKBANK_results.xlsx` (seed `20260821`, N=`500000`, Prudent):

| Scenario | Portfolio TVaR 99 contribution |
| --- | ---: |
| Critical business-service disruption | $22,090,349 |
| Sensitive-data compromise | $10,058,005 |
| Data or transaction-integrity compromise | $13,364,932 |
| Cyber-enabled theft or fraud | **$94,193,461** |
| **Sum** | **$139,706,747** |
| Aggregate TVaR 99 | **$139,706,747** |

The reported “Cyber-enabled theft = $49,193,461” figure understates the workbook value by exactly $45,000,000. Using the actual column **Portfolio TVaR 99 contribution** (formerly labelled “Contrib TVaR 99”), contributions already reconcile to aggregate TVaR 99 within floating-point noise (~1e-7).

Actor and loss-component portfolio TVaR 99 contributions also reconcile to the same aggregate.

**Distinction preserved:** standalone scenario TVaR 99 ≠ portfolio contribution. Labels on sheet 03 now say `(standalone)` vs `Portfolio TVaR 99 contribution`, with an explicit sum vs aggregate footer.

**Defect layer:** none in allocation maths; reporting labels clarified to prevent confusing standalone TVaR with portfolio allocation.

## Issue 2 — “See Business Impact” placeholder

**Root cause:** Reporting-layer placeholder. `populate_executive` fell back to `"See Business Impact"` because engines never set `top_tvar99_component`.

**Fix:** `leading_tvar99_component()` ranks `loss_components` by `contrib_tvar99`; IT/OT engines emit `top_tvar99_component` (formatted label), plus name/amount/pct fields.

**RAKBANK leading component:** Incident response — ~$96.5m (~69.1% of TVaR 99).

## Files changed

- `src/crq/reporting_helpers.py` — `leading_tvar99_component`, `portfolio_tail_reconcile`
- `src/it_crq/engine.py` / `src/ot_crq/engine.py` — emit component headline fields
- `src/it_ot_crq/reporting/populate.py` — executive headline; scenario/actor/component labels; reconciling footer
- `tests/unit/test_tvar_contribution_reconcile.py` — new

## Tests

- Focused: `tests/unit/test_tvar_contribution_reconcile.py` (+ reporting suite) PASS
- Full suite: all tests PASS (see `outputs/pytest_tvar_fix_suite.txt`)

## RAKBANK regeneration

- Model: `assessments/RAKBANK.xlsx`
- Output: `outputs/RAKBANK_results.xlsx`
- Seed: `20260821`
- Simulations: `500000`
- Validation: PASS; scenario/actor/component TVaR 99 contributions reconcile; executive headline populated; no `See Business Impact`

## Remaining limitations

- Non-BI OT components can share equal weights when driver stress weights are similar (allocation method, not this defect).
- Golden fixtures were **not** re-frozen (no metric methodology change).
