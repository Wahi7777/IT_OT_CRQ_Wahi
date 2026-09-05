# Immutable quantitative baseline policy

## Normal test execution

`pytest` and `python -m crq validate-release` are verification commands. They must never create, regenerate, overwrite or approve a fixture. Production validation executes the current engine and compares it with approved data; it no longer invokes a freeze script.

Approved production cases are registered in `tests/baselines/approved/registry.json`. `APPROVAL.sha256` locks the registry. Each case also locks the source template, sector pack and accepted historical result fixture by SHA-256.

The production test performs these checks before execution:

1. template hash is exact;
2. sector-pack hash is exact;
3. accepted result fixture hash is exact;
4. canonical input recipe hash is exact;
5. engine, domain, sector, pack, seed, simulation count and validation state are exact;
6. actor/scenario key sets are exact;
7. quantitative results are compared to the accepted values.

## Tolerances

| Field type | Tolerance | Reason |
|---|---:|---|
| Categorical, identifiers, path/configuration states, seed, simulation count | Exact | These are discrete governed semantics. |
| Probabilities stored by the current engine | Absolute `1e-12` | Fixed seed and fixed N make them deterministic; tolerance only covers representation at the last decimal place. |
| AAL, VaR, TVaR, frequency and decompositions | `max(1e-8, abs(expected) × 1e-10)` | Permits last-bit floating-point differences across otherwise equivalent supported environments. It is not a statistical or sampling tolerance. |

The historical acceptance's VaR95/VaR99 precision exception remains recorded. It is not used to widen the engine comparison automatically. A platform that exceeds a tolerance produces a drift failure for investigation.

## Candidate generation and approval

Candidate generation is deliberately separate:

```bash
python tests/regression/freeze_goldens.py \
  --output-dir /absolute/review/location \
  --acknowledge-candidate-not-approved
```

The command refuses to write inside `tests/fixtures` or `tests/baselines/approved`. The same rule applies to `freeze_whatifs.py`.

To approve a new baseline, a reviewer must:

1. open a dedicated model-governance change;
2. explain why output changed and confirm whether methodology, engine or pack versions must advance;
3. compare candidate and approved results field by field;
4. obtain named approval;
5. copy the reviewed result deliberately into the approved location;
6. update provenance and hashes in the registry;
7. update `APPROVAL.sha256` explicitly;
8. run the full production suite from a clean checkout.

Normal CI has no baseline-update step and must not have write permission to the approved-baseline directory.

