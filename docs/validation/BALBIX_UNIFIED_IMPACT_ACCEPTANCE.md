# Unified Balbix impact — methodology acceptance validation

**Date:** 2026-08-27 (acceptance finalized; **IT goldens frozen**)  
**Status: Outcome A — model frozen (2026-08-27)**  
**Release:** **1.2.0** (tag `v1.2.0`, local only — not pushed)  
**Precision exception:** VaR 95 and VaR 99 retain original **tolerance-failure** results; the user accepts reported numerical precision at **N = 500,000** without raising N or changing model assumptions.  
**Goldens:** **IT fixtures re-frozen** (`regression_it_fs.json` at 50k; `regression_it_fs_500k.json` at 500k). **OT fixtures unchanged.**

> Golden fixtures record accepted implementation behaviour. Re-freezing does not establish empirical validity of the dependency or direct-loss calibration.

Machine-readable artefacts:

* Prior blockers: `outputs/balbix_acceptance/acceptance_blockers_report.json`
* Statistical review: `outputs/balbix_acceptance/statistical_acceptance_review.json`
* Freeze record: `tests/fixtures/freeze_environment.json`
* Harness: `scripts/balbix_statistical_acceptance_review.py`

Architecture, catalogue, pack gates, driver reporting, fraud≠IR, likelihood/path/control engines, restored OT calibration, `LOSS_BLOCK_RHO = 0.5` as working prior, and direct-loss as working prior are **retained** and not redesigned here.

---

## Production run identity

| Field | Value |
| --- | --- |
| Assessment | `assessments/RAKBANK.xlsx` |
| Domain / sector | IT / Financial Services |
| Sector pack | **FS-v1.1.1** (Development — working priors) |
| Pack SHA-256 | `3d5534faecc5390e101eab58dfecf6dedf71b5ed68d56d5d6fcab686f97f0bf4` |
| Simulation years | **500,000** (production standard — **retained**; not increased) |
| Seed | **20260821** |
| Basis | **Prudent** (`PRUDENCE_FREQUENCY_FACTOR` = 1.25) |
| Dependency | `channel_comonotonic_gaussian`, `LOSS_BLOCK_RHO` = **0.5** |
| Code commit | See §7 freeze record (tag `v1.2.0`) |
| Combined model | `model/Guided_IT_OT_CRQ_Model_v1_0.xlsx` |

### User decision on simulation count and precision

* **500,000** remains the production simulation count.  
* The user **accepts the reported numerical precision** for the intended assessment at this N.  
* Model assumptions, seeds, calibration, and ρ were **not** changed to improve precision.  
* Original VaR 95 / VaR 99 Pass/Fail results against documented tolerances remain on record (see §1); they are covered by a **documented acceptance exception**, not rewritten as Passes and not by silently widening tolerances.

---

## Statistical review summary

| Topic | Result |
| --- | --- |
| Nesting of standalone N-runs | **Not nested** (explains seed≠prefix only) |
| Production MC uncertainty vs documented tolerances | AAL, TVaR95, TVaR99 **Pass**; VaR95 & VaR99 **Fail** (exception accepted) |
| AAL movement across ρ (~7% point) | Compatible with CRN sampling noise (paired Δ CIs contain 0) |
| TVaR99 ρ sensitivity (~17% point at ρ=0) | Systematic under paired bootstrap |
| Before/after TVaR99 (~7.1% point) | Unpaired; illustrative CI contains 0 |
| OT goldens / fixtures | Unchanged |

---

## 1. Convergence / Monte Carlo uncertainty (production baseline)

Standalone N-runs are not nested. Precision is judged from Monte Carlo error on the **500k production** annual vector.

### Method

| Element | Detail |
| --- | --- |
| AAL | Classical iid SE \(s/\sqrt{N}\); 95% CI ≈ estimate ± 1.96·SE |
| VaR / TVaR | Percentile bootstrap of the annual loss vector, **B = 400** resamples; SE = bootstrap SD; 95% CI = 2.5% / 97.5% percentiles |
| Supporting | Batch means (10 × 50k-year batches) |
| What intervals measure | **Monte Carlo sampling error only** (fixed model, fixed assessment/pack) |
| Assumptions | Years treated as exchangeable MC replicates |
| Heavy-tail limitation | TVaR99 width is dominated by rare extremes; bootstrap can understate uncertainty if the sample maximum is atypical |

Nested-prefix diagnostics remain **separate** and are **not** used as independent-replication evidence.

### Clarification of “±$25m” for TVaR99

| Quantity | Value | Role |
| --- | ---: | --- |
| Monte Carlo SE (bootstrap) | **~$10.6m** | SD of bootstrap TVaR99 replicates |
| 95% bootstrap CI | **[$132.3m, $171.5m]** | Percentile interval |
| CI half-width (vs point) | **~$22.0m** | Distance from estimate to farther CI endpoint |
| Documented acceptance tolerance | **$25m** | Decision / reporting precision — **not** a SE and **not** automatically a 95% half-width |

### Acceptance table (original Pass/Fail retained)

**Pass rule:** CI half-width ≤ documented acceptance tolerance.  
**Exception:** VaR 95 and VaR 99 **Fail** under that rule; user accepts the reported precision at N=500k without changing N or assumptions.

| Metric | Production estimate | Monte Carlo SE | 95% MC interval | Acceptance tolerance | Pass/Fail | Approx. CI half-width |
| --- | ---: | ---: | --- | ---: | --- | ---: |
| AAL | $2,581,309 | $100,570 | [$2.38m, $2.78m] | $250,000 | **Pass** | ~$197k |
| VaR 95 | $9,571,863 | $68,465 | [$9.45m, $9.70m] | $100,000 | **Fail** | **~$124k** |
| TVaR 95 | $45,250,159 | $2,135,576 | [$41.8m, $49.5m] | $5,000,000 | **Pass** | ~$4.3m |
| VaR 99 | $41,519,840 | $395,299 | [$40.7m, $42.3m] | $500,000 | **Fail** | **~$771k** |
| TVaR 99 | $149,582,084 | $10,582,763 | [$132.3m, $171.5m] | $25,000,000 | **Pass** | ~$22.0m |

**Documented acceptance exception (VaR 95 / VaR 99):** The Fail rows above remain the statistical result against the original tolerances. For intended assessment use at **500k years**, the user accepts the achieved precision (half-widths ≈ **$124k** and **≈ $771k** respectively). Tolerances were **not** rewritten to Pass. N was **not** increased to 2M.

---

## 2. AAL movement under `LOSS_BLOCK_RHO` (~7%)

### Implementation invariants (verified)

| Check | Result |
| --- | --- |
| Driver marginal LN parameters (μ, σ) | Unchanged with ρ |
| Event frequency / actor–scenario–route weights | Unchanged (CRN: identical positive-year mask; P(any)=0.127606 all ρ) |
| Driver applicability | Unchanged |
| Control treatment | Unchanged |
| Caps / recoveries in severity draw | **No** cross-driver monetary cap; per-driver uncapped `exp(μ+σZ)` then sum |
| Nonlinear multi-driver adjustment in `_simulate` | **None** |

Analytical prudent AAL (ρ-invariant) = **$2,437,831**.

### Paired AAL results vs ρ = 0.5

| Rho | Simulated AAL | Analytical AAL | Difference vs ρ 0.5 | SE of difference | 95% interval | Interpretation |
| ---: | ---: | ---: | ---: | ---: | --- | --- |
| 0.00 | 2,397,381 | 2,437,831 | −183,928 (−7.1%) | 102,146 | [−384k, +16k] | CI contains 0 — compatible with noise |
| 0.25 | 2,525,099 | 2,437,831 | −56,210 (−2.2%) | 57,314 | [−169k, +56k] | CI contains 0 |
| **0.50** | **2,581,309** | **2,437,831** | **0** | **0** | **[0, 0]** | Baseline |
| 0.75 | 2,621,644 | 2,437,831 | +40,334 (+1.6%) | 64,232 | [−86k, +166k] | CI contains 0 |
| 1.00 | 2,592,018 | 2,437,831 | +10,709 (+0.4%) | 134,137 | [−252k, +274k] | CI contains 0 |

An interval containing zero is **not** proof of correctness; it fails to reject Δ=0 under this CRN path.

---

## 3. Uncertainty in reported TVaR movements

### 3a. ρ sensitivity of TVaR99 (~17% point at ρ=0)

Paired year-index bootstrap (B=400); recompute TVaR each resample.

| Rho | Point TVaR99 | Δ vs ρ=0.5 | Bootstrap SE(Δ) | 95% CI for Δ | Systematic? |
| ---: | ---: | ---: | ---: | --- | --- |
| 0.00 | 124,166,966 | −25.4m (−17.0%) | 10.3m | **[−46.8m, −7.0m]** | **Yes** |
| 0.25 | 139,966,033 | −9.6m (−6.4%) | 5.5m | **[−20.9m, −0.5m]** | **Yes** |
| 0.75 | 158,450,101 | +8.9m (+5.9%) | 6.2m | [−2.4m, +20.5m] | No |
| 1.00 | 161,358,852 | +11.8m (+7.9%) | 13.1m | [−10.3m, +39.2m] | No |

Best estimate remains ρ=0.5 (**structured expert working prior — not empirically calibrated**). Prudence remains the frequency overlay.

### 3b. Before/after TVaR99 (~7.1% point)

| Item | Value |
| --- | --- |
| Before (pre-unified workbook) | $139,706,747 |
| After (production 500k) | $149,582,084 |
| Point Δ | +$9.88m (**+7.1%**) |
| Pairing | **Invalid** — pre-refactor annual vector not retained |
| After-only 95% CI | [$132.8m, $171.5m] |
| Illustrative unpaired CI for Δ | [−$19.1m, +$38.8m] (contains 0) |

---

## 4. Governance of working priors (unchanged)

| Item | Status |
| --- | --- |
| `LOSS_BLOCK_RHO = 0.5` | **Structured expert working prior** — not empirically validated calibration |
| Direct-loss / fraud P50≈$0.84m, P99≈$251.5m | **Working prior requiring validation** — mathematically consistent; not empirically calibrated |
| Best estimate vs prudence | Best estimate uses ρ=0.5; prudence via `PRUDENCE_FREQUENCY_FACTOR` |

---

## 5. Retained prior findings (not reopened)

* Nested vs standalone N-runs; 250k outlier explanation.  
* Power Generation pack 09 restored to accepted golden BIA; PG/EA/MF AAL bit-exact vs fixtures.  
* OT Balbix gaps SF-01, EN-01, PD-03, OP-02, RC-02 remain explicit.  
* Reconciliations and workbook classification checks from the prior acceptance ladder remain in force.  
* Direct-loss formula chain and double-count controls documented in blockers JSON.

---

## 6. Outcome A — frozen (2026-08-27)

**Outcome A approved** with the VaR 95 / VaR 99 precision exception. **IT golden fixtures re-frozen** under release **1.2.0**.

### Fixtures changed

| Fixture | N | Previous prudent AAL | Frozen prudent AAL | Δ | Explanation |
| --- | ---: | ---: | ---: | ---: | --- |
| `regression_it_fs.json` | 50,000 | $1,116,065 | **$1,104,387** | −1.0% | Unified Balbix per-driver severity (frequency unchanged at 0.1355) |
| `regression_it_fs_500k.json` | 500,000 | $1,311,679 | **$1,155,611** | −11.9% | Aligns 500k with current pack frequency (0.1355 vs stale 0.1512) **plus** unified Balbix per-driver severity |

OT fixtures (`regression_ot_*.json`), sector packs, and combined model workbook: **unchanged**.

### Post-freeze verification

| Check | Result |
| --- | --- |
| Full pytest (`CRQ_REQUIRE_GOLDENS=1`) | **139 passed** (`outputs/balbix_acceptance/pytest_post_freeze.txt`) |
| Production golden schema / bridge | **PASS** |
| IT integration (50k, 2% AAL tol) | **PASS** |
| OT production goldens | **Unchanged — PASS** |

---

## 7. Freeze record (release 1.2.0)

| Field | Value |
| --- | --- |
| Release version | **1.2.0** |
| Tag | `v1.2.0` (local, not pushed) |
| Freeze date | 2026-08-27 |
| Python | 3.14.3 |
| numpy | 2.5.2 |
| openpyxl | 3.1.5 |
| pytest | 9.1.1 |
| Production N | **500,000** |
| IT regression N | **50,000** |
| Seed | **20260821** |
| Prudence factor | 1.25 |
| `LOSS_BLOCK_RHO` | 0.5 (working prior) |

### SHA-256

| Asset | Hash |
| --- | --- |
| `model/Guided_IT_OT_CRQ_Model_v1_0.xlsx` | `1024b88e6c8af7263960cafc13706c609a0e885d06f778d5c67d09f924808a7a` |
| FS pack | `3d5534faecc5390e101eab58dfecf6dedf71b5ed68d56d5d6fcab686f97f0bf4` |
| PG pack | `77b3d0b86a6ed82c66063d40663a308e35a6ad357f08e493e03d1a9ae321cf0b` |
| EA pack | `4a063dc8858b9105abe4e426d471cd392d7a55563af170f1d497cdee32089df4` |
| MF pack | `1af0d0e0d795d69b759ae5c5219cb4514173e517f64fbc4c760f1de97689fe83` |
| `regression_it_fs.json` | `78c4a08babeb10c8debde70718f8bc062bc6b095b7d22c348ef7e7c62d752665` |
| `regression_it_fs_500k.json` | `b0f3683b2a37c2eae823a7ab66bb568532747434bee68324ca8dbe700e52f4cb` |
| `regression_ot_power_generation.json` | `393341d1cfb3e26d2fc6ae715d6882431bffe4e5220f40c82079e817bff4152c` |
| `regression_ot_energy_assets.json` | `ebc3438be91bd4cbbbc00ce53ffdc91f7ff35907d02a4c7641de39f5ee90d64d` |
| `regression_ot_manufacturing.json` | `3e5e40eeeadabacaef1fe6803a7a1109eef70af1947f8dcbd4b0579b80ee54e7` |

Full machine-readable record: `tests/fixtures/freeze_environment.json`.

### Explicit non-claims (retained)

* Re-freezing does **not** validate empirical dependence or fraud quantiles.  
* Fixed-seed reproducibility ≠ statistical precision.  
* VaR 95 / VaR 99 **Fail** against original tolerances remains on record; **accepted exception** applies.  
* `LOSS_BLOCK_RHO = 0.5` and direct-loss parameters remain **working priors**.

---

## References

* Gap analysis: `docs/validation/BALBIX_UNIFIED_IMPACT_GAP_ANALYSIS.md`  
* Methodology: `docs/methodology/UNIFIED_BALBIX_IMPACT.md`  
* Cleanup manifest: `docs/validation/CLEANUP_MANIFEST.md`  
* Dependency: `src/crq/impact/dependency.py`  
* Blockers / statistical harness: `scripts/balbix_acceptance_blockers.py`, `scripts/balbix_statistical_acceptance_review.py`
