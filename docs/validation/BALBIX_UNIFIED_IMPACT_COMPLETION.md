# Unified Balbix impact implementation — completion notes

**Date:** 2026-08-26  
**Prerequisite:** [BALBIX_UNIFIED_IMPACT_GAP_ANALYSIS.md](BALBIX_UNIFIED_IMPACT_GAP_ANALYSIS.md)

## Delivered

1. **Gap analysis** documented before refactor (same folder).
2. **Core module** `src/crq/impact/` — Balbix catalogue, formula library, fitting/aggregation/reconciliation helpers.
3. **IT engine** fits and simulates **per Balbix driver**; control blocks remain Duration/Exposure/Direct **channels only**.
4. **Reporting** rolls drivers → Balbix major categories; Business Impact lists categories + applicable drivers; inapplicable drivers omitted.
5. **OT** likelihood/path/control maths unchanged; reporting maps Balbix analogues and **flags** non-Balbix drivers (`OT_BALBIX_GAPS`) without inventing IDs.
6. **Docs:** `docs/methodology/UNIFIED_BALBIX_IMPACT.md`, `docs/user_guide/BUSINESS_IMPACT.md`, README pointer.
7. **Tests:** `tests/unit/test_unified_balbix_impact.py`; full suite **PASS**.

## RAKBANK verification (25k years, seed from assessment, `--no-whatifs`)

| Metric | Value |
| --- | --- |
| AAL (Prudent) | ~$2.45m |
| TVaR 99 | ~$135.5m |
| Largest TVaR 99 **category** | **Direct Loss of Funds costs — ~$85.9m (63.4%)** |
| Largest TVaR 99 **driver** | Monetary theft / funds at risk (net of recovery) |
| Incident & response share of TVaR 99 | ~1.6% |

Previously fraud was mislabelled as **Incident response** (~69% of TVaR 99) because Direct-block trials were mapped to that label. That defect is closed.

Absolute AAL/TVaR levels differ from pre-refactor totals because severity is now fitted **per driver** (sum of lognormals ≠ lognormal of sums). **Goldens were not re-frozen.**

## Acceptance checklist

| Criterion | Status |
| --- | --- |
| IT uses unified Balbix driver engine | PASS |
| Sector pack enables/calibrates drivers | PASS (unchanged pack matrix) |
| Catalogue presence ≠ activation | PASS (e.g. CARD_REPLACEMENT not in FS pack) |
| Inapplicable drivers absent from BI tables | PASS |
| Financial theft ≠ incident response | PASS |
| Safety/physical OT gaps ≠ BI | PASS (gap labels) |
| Categories from underlying drivers | PASS |
| Likelihood/path/control unchanged | PASS (OT tests green) |
| Four sector packs / full pytest | PASS |
| Methodology + user guide updated | PASS |

## Follow-ups

* **Acceptance:** see [`BALBIX_UNIFIED_IMPACT_ACCEPTANCE.md`](BALBIX_UNIFIED_IMPACT_ACCEPTANCE.md) — **Outcome B**; goldens not re-frozen.
* Enable missing Balbix drivers in FS pack when calibrated (card replacement, PR, training, settlements, separate fraud reimbursement).
* OT pack migration onto Balbix IDs only after gap review for SF-01 / EN-01 / PD-03 / OP-02 / RC-02.
* Triage Power Generation AAL drift vs golden (EA/MF bit-exact).
