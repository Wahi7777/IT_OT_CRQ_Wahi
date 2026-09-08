# Phase 5A — Minimum integrated product backend

Status: implemented and validated in the controlled AWS development account.

## Protected starting point

Phase 5A starts from the separately committed and pushed Phase 4B checkpoint
`dbee565d4474b68fe0e02f14ef6e657d2fb30b35`. No IT engine, OT engine,
shared quantitative module, methodology, sector pack, approved baseline, or
numerical-equivalence-policy file is changed by this phase.

## Exact execution and data flow

```text
React browser
  -> Cognito authorization-code flow with PKCE
  -> API Gateway HTTP API JWT authorizer
  -> API Lambda (authorize, validate, persist, enqueue, read)
  -> S3 assessment/request/status records + lightweight SQS job
  -> SQS worker Lambda (batch 1, window 0)
  -> crq.application.service.execute_assessment()
  -> Phase 2 structured facade
  -> unchanged IT or OT engine
  -> validated CRQResult in S3
  -> authenticated API result retrieval
  -> existing nine-screen React result presentation
```

Only `execute_assessment()` crosses into quantitative execution. The API,
worker orchestration, browser, authentication, and persistence layers contain
no risk calculations.

## HTTP and authentication contract

`GET /health` is public. All other endpoints use the API Gateway Cognito JWT
authorizer:

- `POST /v1/assessments`
- `GET /v1/assessments/{assessment_id}`
- `POST /v1/assessments/{assessment_id}/run`
- `GET /v1/runs/{run_id}`
- `GET /v1/runs/{run_id}/result`

The create endpoint accepts only the public `CRQAssessment` projection. The
run endpoint accepts only `schema_version`, `request_id`,
`model_bundle_reference`, and `run_config`, plus a 16–128 character
`Idempotency-Key`. The full assessment is loaded server-side. The status
endpoint never returns the result and exposes only safe governed failure codes.
The result endpoint returns 202 before completion, 409 after failure, and 200
with the unchanged canonical `CRQResult` after completion.

The React application uses Cognito authorization code with PKCE. Tokens are
held in memory, not local/session storage. Protected requests receive the ID
JWT bearer token; 401/403 clears the session and redirects to sign-in. Demo
mode bypasses authentication and continues to use repository-approved result
artifacts.

Tenant identity comes from the verified `custom:tenant_id` claim. For the
controlled development environment only, a server-configured `crq-dev`
fallback is used when that claim is absent. Caller-supplied tenant IDs and S3
keys are never accepted. This fallback is not sufficient for production
multi-tenancy and must be removed or replaced by an authoritative mapping
before production.

## S3 contract

The server alone constructs deterministic keys:

```text
assessments/{tenant_id}/{assessment_id}/input.json
assessments/{tenant_id}/{assessment_id}/metadata.json
runs/{tenant_id}/{run_id}/request.json
runs/{tenant_id}/{run_id}/status.json
runs/{tenant_id}/{run_id}/result.json
```

`narrative.json` remains reserved and unimplemented. Objects carry stable
tenant, user, assessment, version, run, domain, sector, bundle, engine,
methodology, hash, status, and timestamp fields, with unavailable values null.
The bucket blocks all public access, uses BucketOwnerEnforced ownership,
AES-256 SSE-S3, versioning, and a deny-insecure-transport policy. Browser code
has no S3 permissions.

## Job, retries, and idempotency

The exact job contract is `contracts/schemas/phase5a-job.schema.json`.

The versioned `1.0` job contains only run, assessment, tenant, approved bundle
identifiers and run configuration. It contains no financial, architecture,
control, insurance, evidence, or result payload. The worker validates this
message against persisted server-owned identifiers before execution.

SQS uses batch size 1, batching window 0, 960-second visibility, SSE, and a
dead-letter queue with `maxReceiveCount=3`. The worker uses conditional S3
writes and a 16-minute lease. `COMPLETED` is terminal; duplicate deliveries are
acknowledged without recomputation. A persisted result is promoted to
`COMPLETED` after a status-write interruption. Governed application errors
become non-retryable `FAILED`; unexpected failures expose a bounded generic
code and are retried for DLQ handling.

S3 and SQS cannot provide a transaction spanning status persistence and job
publication. The API therefore returns success only after publishing, records
`enqueued_at`, and safely republishes a still-QUEUED run when an idempotent
retry finds no enqueue marker. A crash after publication can create a duplicate
but cannot create a different result; the worker's conditional claim and
terminal-state checks handle that case. The remaining limitation is that a
client must retry an uncertain submission using the same idempotency key.

## Frontend integration and bundle split

The existing Phase 4B pages and visual system are unchanged. In API mode the
review action first persists the assessment, submits the lightweight run
request, polls every 2.5 seconds through QUEUED/RUNNING/COMPLETED/FAILED, then
retrieves and renders the canonical result. In demo mode the same components
use the approved fixtures.

The Phase 4B build emitted one approximately 3.16 MB JavaScript bundle because
both approved results were statically imported. Phase 5A dynamically imports
approved IT and OT results. The current build emits:

- main application chunk: 888.41 kB (253.39 kB gzip);
- approved IT result chunk: 211.06 kB (26.98 kB gzip);
- approved OT result chunk: 2,065.84 kB (104.29 kB gzip).

The OT artifact is no longer part of the initial application bundle and demo
mode does not use AWS services.

## Local verification

Completed on 2026-09-08:

| Check | Result |
|---|---|
| Complete Python suite | 222 passed, 1 skipped in 337.13 s |
| Phase 5A async IT FS 500k and OT PG 500k | passed, exact canonical equality after approved transient-field normalization |
| Frontend tests | 6 files, 19 passed |
| Frontend TypeScript/Vite production build | passed |
| npm audit | 0 vulnerabilities |
| Ruff on changed Python | passed |
| Bandit medium/high over `src` | passed |
| pip-audit pinned runtime dependencies | no known vulnerabilities (`--no-deps --disable-pip`; the ordinary isolated-env run aborted in local Python `ensurepip`) |
| Terraform fmt/validate | passed |

A repository-wide Ruff check also reports 29 existing findings in untouched
legacy/quantitative/reporting files. They predate Phase 5A and were not changed
because cosmetic edits to governed code are outside this phase.

## AWS evidence

Deployment used profile `aiengineer`, region `us-east-1`, and non-production
account `826971436811`, matching Phase 3C. The clean committed initial plan was
exactly `31 add, 0 change, 0 destroy` and contained only the scoped Phase 5A
resources. The final package SHA-256 is
`d345638cd4f7e0087db9c70790c5a301541907b203250de48d6eae3b34ccc15f`.
A final Terraform plan reported no changes.

Health returned 200; missing and invalid JWTs returned 401. Cognito issued ID
tokens for controlled temporary users with distinct tenant claims. Tenant B
received 404 for Tenant A's assessment, run, and result. All temporary test
users were deleted after validation. S3 independently reports the bucket as
non-public; encryption, versioning, public-access blocks, event mapping, queue
encryption, retry and DLQ settings match Terraform. Targeted CloudWatch scans
found zero financial, architecture, control or insurance payload patterns.

Actual AWS results:

| Case | Queue pickup | Worker | Submit-to-complete | Max memory | Parity |
|---|---:|---:|---:|---:|---|
| IT Financial Services 500k | 1.872 s | 29.250 s | 31.122 s | 550 MiB | PASS |
| OT Power Generation 500k | 0.208 s | 26.446 s | 26.655 s | 1,024 MiB | PASS |

The comparison applied `crq-cross-platform-numerical-equivalence/1.0.0` with
exact comparison as the default. Both cases had zero exact failures. The only
deltas were the already-governed Phase 4A exceptions: three mirrored IT values
at a maximum `1.1102230246251565e-16` and 156 mirrored OT values at a maximum
`3.725290298461914e-09`. Headline AAL, VaR, TVaR, event frequency and P(any)
were exact.

At the governed Phase 3C arm64 rate of USD 0.0000133334 per GB-second, measured
2,048 MiB worker compute is USD 0.000812857 per IT run and USD 0.000708110 per
OT run, excluding free tier. This is worker model-execution compute only, not
total product cost. Full resource identifiers, hashes, latencies, controls and
the investigated S3 missing-object failure are recorded in
`phase5a-aws-evidence.json`.

The reviewed destroy plan is exactly `0 add, 0 change, 31 destroy`, limited to
the Phase 5A dev stack. The stack remains live: the plan has not been applied
and destruction requires explicit human approval.
