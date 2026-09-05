# Controlled productisation phase: contract and baseline foundation

This phase does not refactor either quantitative engine and does not build an API, frontend, cloud infrastructure, authentication or GenAI integration.

## Preserved invariants

- Prudence continues to affect frequency only where currently implemented.
- Architecture/path feasibility remains separate from control effectiveness.
- Closed paths remain closed; Unknown is not converted to Closed.
- IT and OT Monte Carlo and dependency semantics are unchanged.
- Existing paired/common-random-number behavior is unchanged.
- The narrative contract is downstream-only and cannot calculate risk metrics.

## Phase 2 minimum scope

The smallest safe next task is an adapter-first engine facade:

1. implement read-only Excel-to-`CRQAssessment` extraction with no engine changes;
2. materialize current governed workbook/pack assumptions into immutable `ModelBundle` objects and verify their hashes;
3. add thin `run_it_assessment()` and `run_ot_assessment()` facades that initially populate temporary compatibility workbooks and call the unchanged engines;
4. normalize returned dictionaries into `CRQResult`, preserving unmapped keys in `legacy_engine_extension`;
5. prove facade output equals the approved baselines and existing Excel route output;
6. only after parity is established, replace compatibility-workbook reads incrementally inside the engines.

No formula extraction or algorithm restructuring is required in the first Phase 2 increment.

