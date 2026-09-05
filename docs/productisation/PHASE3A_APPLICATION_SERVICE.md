# Phase 3A — Runtime-neutral assessment application service

## Outcome

Phase 3A introduces a synchronous, framework-neutral boundary:

```text
AssessmentRunRequest JSON
  -> request and assessment validation
  -> server-side approved ModelBundle resolution
  -> Phase 2 run_it_assessment()/run_ot_assessment()
  -> CRQResult validation
  -> AssessmentRunResponse JSON
```

The application layer implements no quantitative methodology. Frequency, probability, severity, dependency, route/path, control, impact, appetite, insurance, Monte Carlo, VaR, and TVaR behaviour remain exclusively in the unchanged engines called by the Phase 2 facade.

## Modules and responsibilities

| Module/artifact | Responsibility |
|---|---|
| `src/crq/application/service.py` | Stateless orchestration, request/run compatibility, facade selection, result integrity checks, response envelope and timings. |
| `src/crq/application/request_adapter.py` | Validates caller-owned structured fields and creates server-generated allowlisted compatibility cells. It rejects governed inputs and paths. |
| `src/crq/application/bundle_resolver.py` | Resolves only approved registry IDs, loads governed bundles, and verifies engine/pack/schema versions and pack hash. |
| `src/crq/application/serialization.py` | Canonical JSON naming/order, NumPy scalar conversion, and rejection of NaN/Infinity. |
| `src/crq/application/errors.py` | Stable public error codes and path/trace-free payloads. |
| `config/approved_model_bundles.json` | Deterministic approved bundle registry; a later persistence implementation may replace this resolver source. |
| `contracts/schemas/assessment-run-*.schema.json` | Formal JSON request and response contracts. |
| `contracts/examples/assessment-run-*.json` | Complete IT FS and OT PG 500k requests and successful responses derived from approved assessments. They are examples, not baseline authorities. |

The compatibility workbook remains a temporary internal adapter used by the Phase 2 facade. It is not accepted in the public request and its path is not emitted in CRQResult.

## Public request contract

`AssessmentRunRequest` schema version `1.0.0` requires:

- `request_id`;
- a public projection of `CRQAssessment` schema `1.0.0-draft`;
- `model_bundle_reference` containing only `bundle_id` and `bundle_version`;
- `run_config` containing only `reporting_basis`, `simulation_count`, and `random_seed`.

Run configuration must match the assessment. Phase 3A accepts baseline execution only: what-if, package, sensitivity, and outside-in application flags cannot be activated through this endpoint. The application generates compatibility cells from a server-owned workbook template and known IDs. Callers cannot provide workbook paths, pack paths, cell coordinates, compatibility data, calibration tables, priors, correlation/dependency assumptions, mappings, caps/floors, or governed overrides.

Recommended HTTP boundary for Phase 3B: reject request bodies over 1 MiB before parsing. Current examples are approximately 14 KiB. This is a transport protection, not a schema rule.

## Approved bundles

| Public reference | Domain | Sector | Engine | Pack version | Verification |
|---|---|---|---|---|---|
| `FS-v1.1.1@1.0.0` | IT | Financial Services | 1.1.1 | 1.1.1 | registry status, compatibility and SHA-256 |
| `PG-v1.6@1.0.0` | OT | Power Generation | 1.7.1 | 1.6 | registry status, compatibility and SHA-256 |
| `EA-v1.0@1.0.0` | OT | Energy Assets | 1.7.1 | 1.0 | registry status, compatibility and SHA-256 |
| `MF-v1.0@1.0.0` | OT | Manufacturing | 1.7.1 | 1.0 | registry status, compatibility and SHA-256 |

An unknown ID/version returns `MODEL_BUNDLE_NOT_FOUND`. A known bundle with a different domain/sector, or a loaded artifact that fails a configured version/hash check, returns `MODEL_BUNDLE_INCOMPATIBLE`.

## Response and provenance

`AssessmentRunResponse` schema version `1.0.0` contains `request_id`, `status`, `result`, `warnings`, `validation`, and `error`. A success contains the complete canonical `CRQResult`; an error contains no result.

The service validates the result section set, schema version, assessment hash, bundle ID/version/hash, sector pack ID/version, input/output schema versions, seed, simulation count, finite JSON representation, and result hash. CRQResult retains the lossless native engine extension while the canonical mapping is completed. The engine's temporary `output` path is deliberately excluded because it is infrastructure metadata, not a model output.

## Error taxonomy

- `INVALID_REQUEST`
- `INVALID_ASSESSMENT`
- `UNSUPPORTED_DOMAIN`
- `UNSUPPORTED_SECTOR`
- `MODEL_BUNDLE_NOT_FOUND`
- `MODEL_BUNDLE_INCOMPATIBLE`
- `SCHEMA_VERSION_UNSUPPORTED`
- `VALIDATION_FAILED`
- `EXECUTION_FAILED`
- `RESULT_VALIDATION_FAILED`

Public errors contain only `code`, safe `message`, and bounded `details`. Unexpected exceptions become `EXECUTION_FAILED`; stack traces, local paths, temporary workbook names, and environment details are not returned.

## Parity rule

All four production cases execute through both the Phase 3A service and the Phase 2 facade. Canonical JSON is exact after excluding only invocation identity (`run_id`, start/completion timestamp, result hash derived from those values) and `router_metadata.input_hash`. The latter hashes a newly created XLSX ZIP and varies with archive timestamps; `assessment_hash` is the stable semantic input identity and is compared exactly. The complete native engine extension and every quantitative result remain exact.

## Local benchmark

The reproducible data is in `application-service-benchmark.json`. Each case ran in a clean child process on the recorded macOS arm64 host with Python 3.12.14 and production 500k settings.

| Case | Validation | Bundle | Internal workbook materialisation | Engine | Result normalization | Result validation | Serialization | Total | Peak RSS | Request / response |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| IT Financial Services | 626 ms | 205 ms | 967 ms | 7,894 ms | 9 ms | 7 ms | 2 ms | 9,713 ms | 477 MiB | 14.0 KiB / 206 KiB |
| OT Power Generation | 579 ms | 250 ms | 929 ms | 8,656 ms | 282 ms | 197 ms | 78 ms | 10,976 ms | 942 MiB | 14.4 KiB / 2.07 MB |

The application-boundary work (validation, bundle resolution, result validation and serialization) was 10.6% of engine time for IT and 12.7% for OT. It is bounded and does not dominate execution, but is measurable rather than literally zero; no optimization is justified before Lambda measurements. Internal workbook materialisation is Phase 2 compatibility overhead and is reported separately. The OT response is large because the lossless native extension is still present.

## Security and runtime properties

- No caller-controlled local paths or model-pack paths.
- Unknown fields are rejected at the request, run, identity, common input, and domain-input boundaries.
- Governed assumptions are rejected recursively and resolved server-side.
- JSON is finite and deterministic; NumPy-native scalars are normalized.
- Execution state is request-local. Temporary files use an explicit temporary directory and are removed after the run.
- No project-directory writes are required by the service.
- No secrets are accepted or logged by this layer.

## Remaining Lambda-wrapper blockers

1. Build and test an arm64/x86_64 deployment artifact with pinned NumPy/OpenPyXL and packaged model/sector assets. The current `requires-python >=3.11` metadata conflicts with NumPy 2.5.2 requiring Python 3.12+ and must be governed before packaging.
2. Benchmark in actual Lambda. Local peak RSS suggests starting at 1,536–2,048 MiB; local processing is 10–11 seconds, so start with a 60-second timeout and measure cold/warm behaviour.
3. Enforce a 1 MiB request limit and a response-size guard below Lambda's synchronous response limit. The current OT PG response is about 2.07 MB.
4. Map error codes to fixed HTTP statuses and add structured, redacted CloudWatch logging keyed by `request_id`; do not log assessments or full results by default.
5. Confirm read-only package assets and `/tmp` capacity in the built artifact. No Lambda handler should alter the application or quantitative interfaces.

## Minimal Phase 3B

Add one thin Lambda handler and API Gateway route for `POST /v1/assessments/run`, plus `GET /health` only if operationally required. The handler should enforce body/content-type limits, decode JSON, call `execute_assessment()`, map existing errors to HTTP responses, and emit redacted timings. Package the existing approved registry, template, packs, and Python dependencies unchanged. Add handler contract tests and cold/warm Lambda benchmarks. Do not add persistence, Cognito, frontend, GenAI, queues, or additional services.
