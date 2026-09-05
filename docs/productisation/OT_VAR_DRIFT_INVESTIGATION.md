# OT accepted-fixture VaR drift investigation

## Status

`RESOLVED_CURRENT_ENGINE_AUTHORITATIVE`

The new engine-executing regression test reproduced every accepted OT AAL, TVaR95, TVaR99, probability, frequency, actor AAL and scenario AAL value exactly. VaR95 and VaR99 differ from all three accepted OT fixtures.

| Case/field | Accepted | Current engine | Difference | Relative difference |
|---|---:|---:|---:|---:|
| PG prudent VaR95 | 924,397.253 | 925,138.440 | 741.187 | 0.080181% |
| PG best VaR99 | 34,846,254.942 | 34,868,942.699 | 22,687.756 | 0.065108% |
| PG prudent VaR99 | 50,166,813.795 | 50,170,571.702 | 3,757.907 | 0.007491% |
| EA prudent VaR95 | 2,304,412.466 | 2,304,505.776 | 93.310 | 0.004049% |
| EA best VaR99 | 36,142,883.899 | 36,153,204.754 | 10,320.855 | 0.028556% |
| EA prudent VaR99 | 52,265,985.363 | 52,279,254.174 | 13,268.812 | 0.025387% |
| MF prudent VaR95 | 4,209,116.050 | 4,210,741.892 | 1,625.842 | 0.038627% |
| MF best VaR99 | 37,130,641.276 | 37,137,226.380 | 6,585.105 | 0.017735% |
| MF prudent VaR99 | 54,818,514.649 | 54,828,218.348 | 9,703.699 | 0.017702% |

Best VaR95 is zero in each OT case and remains exact.

## Evidence and likely cause

- The current and frozen commit both declare `VAR_QUANTILE_METHOD = "higher"` in `src/crq/metrics.py`.
- Commit/history inspection shows no current-engine change since the accepted freeze for the shared metric implementation.
- The 1.2.0 acceptance documentation says the IT goldens were re-frozen. It does not state that OT goldens were re-frozen after the shared metric convention was finalized.
- The mismatch is isolated to quantile cut-point values. Tail means and the rest of each run remain exact.
- Repeated runs under different `PYTHONHASHSEED` values produced the same current VaR values.

Deterministic reproduction subsequently proved that every non-zero accepted OT VaR value was exactly NumPy `method="linear"`, while every current value was exactly `method="higher"` on the same annual vector. The model owner approved `CURRENT_ENGINE_AUTHORITATIVE` on 2026-09-05. The governed correction is recorded in `tests/baselines/approved/OT_VAR_BASELINE_CORRECTION.json`.

## Governance decision

`CURRENT_ENGINE_AUTHORITATIVE`. The correction aligns the OT fixtures with the already-authoritative release 1.2.0 convention. It does not change methodology, engine code, packs, seeds, simulation count, assumptions, or tolerances.
