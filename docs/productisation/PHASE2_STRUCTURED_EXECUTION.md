# Phase 2 structured execution boundary

## Scope

Phase 2 introduces a runtime-neutral boundary over the unchanged IT and OT engines:

`Excel -> extract_assessment -> CRQAssessment -> run_*_assessment -> unchanged engine -> CRQResult`

No frontend, API, Lambda handler, AWS resource, database, authentication or GenAI implementation is included.

## Public interface

`crq.application` exports:

- `extract_assessment(workbook)`
- `load_model_bundle(domain, sector)`
- `run_it_assessment(assessment, model_bundle, run_config)`
- `run_ot_assessment(assessment, model_bundle, run_config)`
- immutable `CRQAssessment`, `ModelBundle`, `RunConfig` and `CRQResult` value objects

Workbook paths are confined to the Excel adapter. They are not part of either execution function's public contract.

## Compatibility mechanism

The adapter extracts common, domain, architecture/topology, control, impact/BIA, appetite, insurance, permitted-override, evidence and runtime inputs. Each replayable workbook cell carries its Phase 1 ownership classification. Governed pack inputs are deliberately excluded from `CRQAssessment`; inactive and evidence-only values remain inactive/evidence-only.

During this migration phase the facade copies the governed combined template into an operating-system temporary directory, replays only client-owned/evidence/legacy cells, invokes the existing engine, normalizes the result and deletes the temporary directory. Quantitative source packages remain unchanged.

## ModelBundle

The read-only loader validates the selected registry record and pack metadata, captures the complete pack workbook and relevant governed core sheets into structured snapshots, records source hashes, and calculates a canonical JSON bundle hash. The returned object recursively freezes mappings and sequences.

## Result preservation

Material outputs are normalized into the canonical summary, formation, decomposition, loss, architecture, impact, treatment, sensitivity, uncertainty, insurance and provenance sections. The complete native engine dictionary is additionally retained under `compatibility.legacy_engine_extension`.

This extension is a deliberate migration safeguard: no native field can silently disappear while typed mappings are completed. It must not be treated as a new quantitative source or exposed as an ordinary editable input.

## Validation and parity

The adapter enforces domain/sector consistency, reporting-basis values, simulation-count limits, non-negative seeds, model-bundle applicability and exact RunConfig seed/count agreement. Existing workbook and engine validation remains authoritative inside the compatibility execution.

`tests/integration/test_structured_execution_facade.py` executes both paths for IT Financial Services and all three supported OT packs. It compares the complete native engine dictionary exactly, apart from the temporary output pathname, and separately asserts canonical headline metrics and provenance.

## Next boundary

The smallest next phase is a thin request/response API adapter that validates JSON against the existing schemas and invokes these facade functions. It should contain no quantitative logic and initially use the same synchronous runtime-neutral interface.
