# Production readiness report

**Verdict: A — PRODUCTION READY**  
Date: 23 August 2026  
Package: Combined IT/OT CRQ 1.0.0

Microsoft Excel visual/display UAT is **out of scope** for this classification (user-performed separately). Automated production tests, 500k Control What-If, CRN, monotonicity, Basis selector, and engine→Bridge writes are in scope.

The dual-engine architecture is unchanged: Financial Services → IT v1.1.1; Power Generation / Energy Assets / Manufacturing → OT v1.7.1. Methodologies are not merged.

## Freeze environment

| Item | Value |
| --- | --- |
| Python | 3.14.3 |
| numpy | 2.5.2 |
| openpyxl | 3.1.5 |
| et-xmlfile | 2.0.0 |
| Host | darwin 25.5.0 |
| Combined workbook | `model/Guided_IT_OT_CRQ_Model_v1_0.xlsx` |
| Combined / router | 1.0.0 / 1.0.0 |
| Outside-In schema | 1.0.0 |
| Command | `PYTHONPATH=src:. python tests/regression/freeze_goldens.py` then `freeze_whatifs.py` |
| Elapsed (four sectors + native compare) | ~47 s baseline goldens |
| What-if freeze (N=500,000, all mapped controls) | FS 14.7 s / PG 12.7 s / EA 12.7 s / MF 13.0 s |

Tolerance used only for native-vs-combined: `abs(a-b) <= 1e-6 * max(1, abs(a))`. Goldens themselves are exact JSON dumps of engine floats.

---

## Production metrics (N = 500,000)

### Financial Services — IT 1.1.1 / FS-v1.1.1 / Organisation / seed 20260821

Input SHA-256: `af5a18a4dfc8e1aec681b30a10954986245b4448acfce96b3688988a5c7ae6eb`  
Pack status: Development — working priors; calibration required  
Outside-In: No  
Validation: PASS  
Native vs combined: exact-or-1e-6-rel

| | Best Estimate | Prudent |
| --- | ---: | ---: |
| AAL | 1,059,877.25 | 1,311,679.36 |
| VaR95 | 5,487,402.48 | 7,125,947.96 |
| TVaR95 | 18,021,076.14 | 20,885,314.90 |
| VaR99 | 22,824,448.17 | 26,218,158.97 |
| TVaR99 | 46,179,340.42 | 51,675,144.84 |
| P(any successful event) | 0.114878 | 0.140772 |
| Attempt frequency / yr | 1.0 | 1.25 |
| Successful-event frequency / yr | 0.120944 | 0.151180 |

Actor AAL (Prudent view): Cybercriminal 651,035.53; Hacktivist 240,056.84; Malicious insider 301,385.84; Nation-state 119,201.14. Sum = Prudent AAL.

### Power Generation — OT 1.7.1 / PG-v1.6 / CCGT / seed 20260813

Input SHA-256: `b0bac4325181365f0bd2e8eaf34a9b2af41b714955fcd62cf9a9c8a7f8b3df30`  
Pack status: Reference pack / working calibration  
Validation: PASS

| | Best Estimate | Prudent |
| --- | ---: | ---: |
| AAL | 1,323,497.77 | 1,935,742.98 |
| VaR95 | 0 | 924,397.25 |
| TVaR95 | 26,469,955.49 | 38,708,768.41 |
| VaR99 | 34,846,254.94 | 50,166,813.79 |
| TVaR99 | 100,626,039.56 | 128,228,296.40 |
| P(any successful event) | 0.034304 | 0.05048 |
| Attempt frequency / yr | 0.60635 | 0.906584 |
| Successful-event frequency / yr | 0.03498 | 0.051778 |

Best Estimate VaR95 = 0 with positive TVaR95 is expected (sparse annual losses: 95th percentile year is still zero).

### Energy Assets — OT 1.7.1 / EA-v1.0 / Upstream Onshore / seed 20260813

Input SHA-256: `35b772ead6a972152b84686a8a9472b0765312a5f25711fb2b3ba77e57b6fa55`  
Pack status: Working pack — controlled calibration  
Validation: PASS

| | Best Estimate | Prudent |
| --- | ---: | ---: |
| AAL | 1,348,466.62 | 2,018,039.45 |
| VaR95 | 0 | 2,304,412.47 |
| TVaR95 | 26,969,332.35 | 40,284,480.51 |
| VaR99 | 36,142,883.90 | 52,265,985.36 |
| TVaR99 | 101,105,717.88 | 130,804,332.24 |
| P(any successful event) | 0.035488 | 0.052566 |
| Attempt frequency / yr | 0.624432 | 0.9343 |
| Successful-event frequency / yr | 0.036246 | 0.053998 |

### Manufacturing — OT 1.7.1 / MF-v1.0 / Process Manufacturing / seed 20260813

Input SHA-256: `944981fbb9d9f93c426a23058eb61f6dad38a0c55bf33e9a995a849e4cf0c697`  
Pack status: Working pack — controlled calibration  
Validation: PASS

| | Best Estimate | Prudent |
| --- | ---: | ---: |
| AAL | 1,388,358.67 | 2,083,676.46 |
| VaR95 | 0 | 4,209,116.05 |
| TVaR95 | 27,767,173.34 | 41,316,668.04 |
| VaR99 | 37,130,641.28 | 54,818,514.65 |
| TVaR99 | 100,198,097.05 | 127,840,814.51 |
| P(any successful event) | 0.038432 | 0.057006 |
| Attempt frequency / yr | 0.700478 | 1.049502 |
| Successful-event frequency / yr | 0.03921 | 0.058748 |

Fixtures: `tests/fixtures/regression_it_fs_500k.json`, `regression_ot_power_generation.json`, `regression_ot_energy_assets.json`, `regression_ot_manufacturing.json`. Fast CI retains `regression_it_fs.json` at 50,000 years.

---

## Release gate matrix

| Gate | Result | Evidence |
| --- | --- | --- |
| Independent unit/security suite | PASS | `pytest tests -q -m "not production"` (2026-08-23, ~68 s) |
| FS / PG / EA / MF 500k goldens | PASS | freeze_goldens.py + `pytest -m production` 8 passed |
| Four native vs combined / no scan | PASS | freeze_goldens native compare; rel 1e-6 |
| Engine = Output Bridge | PASS | Freeze B15/C15 numeric ENGINE_WRITTEN; `tests/regression/test_engine_bridge.py`; unit overwrite test |
| Output Bridge = Dashboard (Python) | PASS | Presentation `IF` on Basis; ENGINE_WRITTEN cache B71:B78 |
| Excel visual UAT | OUT OF SCOPE | User-performed; not an automated release blocker |
| Control What-If 500k all sectors | PASS | `freeze_whatifs.py`; fixtures `whatif_*_500k.json` |
| What-If CRN | PASS | OT evaluate twice same override exact AEP; IT `_simulate` same seed |
| What-If monotonicity | PASS | min Prudent AAL reduction ≥ 0 (OT zeros = unmapped) |
| Basis default Prudent | PASS | Run Setup C9; labels are basis-independent |
| OI exposure vs exploitability + anti-double-count | PASS | `tests/security/test_oi_barrier.py` |
| OI rationale reconciliation | PASS | `tests/security/test_oi_rationale.py` |
| Workbook error scan (freeze outputs) | PASS | 0 `#REF!` / `#VALUE!` / `#DIV/0!` / `#NAME?` / `#N/A` tokens in four `out_regression_*.xlsx` |
| ruff | PASS | `ruff check src tests` |
| bandit `-ll` | PASS | 0 medium+ after geography ValueError nosec B608 (false SQL) |
| pip-audit | PASS | `No known vulnerabilities found` vs `requirements.txt` |
| Secret scan | PASS | `tests/security/test_secrets_scan.py` |
| Formula injection / path safety | PASS | `tests/security/test_untrusted_input.py` |
| Dependencies locked | PASS | `requirements.txt` + `pyproject.toml` pins |
| Release metadata | PASS | Combined 1.0.0; OT patch 1.7.1 documented below |
| Production package | PASS with note | `_work/` freeze outputs are artefacts, not ship payload; keep `tests/fixtures` |

### OT 1.7.1 decision

Outside-In may write `00 OI Engine Overlay` multipliers in (0, 1] applied only to the **Prevent/Resist actual** TTP barrier. Final P(success) is not overwritten. Empty overlay is identity versus 1.7. Version **1.7.1** records that engine change. Goldens above were frozen on 1.7.1; AAL matches the prior 1.7 freeze (overlay unused).

---

## CONTROL WHAT-IF PRODUCTION VALIDATION

N = 500,000. Control What-If enabled. Control assessment cells unchanged after the run. Ranking = engine AAL reduction (Prudent column used for freeze ranking). Dashboard 00 What-If selects Best Estimate vs Prudent columns from `00 Engine Results` via the Basis control.

### Financial Services (IT 1.1.1, analytic AAL + 500k tail sims per uplift)

| | |
| --- | --- |
| Pack / asset / seed | FS-v1.1.1 / Organisation / 20260821 |
| Elapsed | 14.7 s |
| Validation | PASS |
| Controls | 15 |
| AAL (Prudent basis) | 1,311,679 |
| TVaR 95 / TVaR 99 | 20,885,315 / 51,675,145 |
| Successful-event frequency | 0.151180 |
| Min AAL reduction | 1,198 (all mapped) |
| Rank 1 | C03 Privileged access management → AAL 1,200,150 (−108,567) |

IT What-If AAL is the governed analytic mean; TVaR/frequency at production N use `_simulate` with the same seed as the baseline (cell Poisson/loss stream).

### Power Generation (OT 1.7.1 CRN Monte Carlo)

| | |
| --- | --- |
| Pack / asset / seed | PG-v1.6 / CCGT / 20260813 |
| Elapsed | 12.7 s |
| Validation | PASS |
| Controls | 52 |
| AAL | 1,935,743 |
| Min AAL reduction | 0 (unmapped/excluded stay at baseline) |
| Rank 1 | M0930 Network Segmentation → AAL 1,287,765 (−647,978); frequency 0.034032 |

### Energy Assets

| | |
| --- | --- |
| Pack / asset / seed | EA-v1.0 / Upstream Onshore / 20260813 |
| Elapsed | 12.7 s |
| Validation | PASS |
| Controls | 52 |
| AAL | 2,018,039 |
| Min AAL reduction | 0 |

### Manufacturing

| | |
| --- | --- |
| Pack / asset / seed | MF-v1.0 / Process Manufacturing / 20260813 |
| Elapsed | 13.0 s |
| Validation | PASS |
| Controls | 52 |
| AAL | 2,083,676 |
| Min AAL reduction | 0 |

Channel checks (simulate=False, CCGT): Prevent / Resist does not change λ; Recover / Restore does not change λ and does not increase recover_factor; excluded controls do not change P(success).

---

## Dashboard Basis

Default = **Prudent**. Alternative = **Best Estimate**. Metric names stay AAL, VaR 95, TVaR 95, VaR 99, TVaR 99, P(any successful event), frequencies. There is no user-facing metric named “Prudent TVaR”. Pack calibration essays were removed from executive summary cells; pack **ID** remains on technical metadata.

---

Calibration caveats (FS/PG/EA/MF working priors) remain disclosed in technical pack registry sheets and **do not** affect this A classification.

---

## Commands

```bash
export PYTHONPATH="$PWD/src:."
python -m crq validate-release
python -m crq validate-release --production
```
