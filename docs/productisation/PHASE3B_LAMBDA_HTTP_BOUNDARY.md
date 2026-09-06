# Phase 3B — Minimal Lambda and HTTP API boundary

## Outcome and call flow

```text
API Gateway HTTP API v2
  -> crq.lambda_adapter.handler(event, context)
  -> body/content-type/route checks
  -> existing execute_assessment()
  -> existing Phase 2 facade
  -> unchanged IT or OT engine
  -> unchanged AssessmentRunResponse body in an HTTP proxy envelope
```

The Lambda adapter contains no quantitative methodology. It does not calculate or modify frequency, probability, severity, dependency, route/path, control, impact, appetite, insurance, AAL, VaR, TVaR, or treatment metrics.

## Authoritative runtime

V1 uses CPython `3.12.x` only. The authoritative declarations are:

- `.python-version`: `3.12`;
- `pyproject.toml`: `>=3.12,<3.13`;
- Terraform Lambda runtime: `python3.12`;
- ZIP wheel target: CPython 3.12 ABI on `manylinux_2_28_aarch64`;
- runtime pins: NumPy 2.5.2, OpenPyXL 3.1.5 and et-xmlfile 2.0.0.

This resolves the former `>=3.11` metadata conflict without changing numerical dependencies. NumPy 2.5.2 supplies an arm64 `manylinux_2_27/_2_28` wheel, suitable for the Amazon Linux 2023 Python 3.12 runtime; it does not supply the older `manylinux2014_aarch64` target. Historical Python 3.14 freeze metadata remains unedited as historical evidence.

## Routes

| Route | Behaviour |
|---|---|
| `GET /health` | Returns status, platform version and IT/OT engine versions. It does not load a bundle or execute a model. |
| `POST /v1/assessments/run` | Requires JSON, limits the decoded body to 1 MiB, passes it to Phase 3A, and returns the Phase 3A body unchanged inside the Lambda proxy response. |

All other routes return 404. Other methods on a defined route return 405. Non-JSON content returns 415 and oversized content returns 413. API Gateway CORS preflight is handled by HTTP API configuration; no third Lambda route is added.

## Application error mapping

| Application code | HTTP status |
|---|---:|
| `INVALID_REQUEST` | 400 |
| `INVALID_ASSESSMENT` | 422 |
| `UNSUPPORTED_DOMAIN` | 422 |
| `UNSUPPORTED_SECTOR` | 422 |
| `MODEL_BUNDLE_NOT_FOUND` | 404 |
| `MODEL_BUNDLE_INCOMPATIBLE` | 422 |
| `SCHEMA_VERSION_UNSUPPORTED` | 422 |
| `VALIDATION_FAILED` | 422 |
| `EXECUTION_FAILED` | 500 |
| `RESULT_VALIDATION_FAILED` | 500 |

Boundary-specific `INVALID_REQUEST` responses use 400, 404, 405, 413, or 415 as appropriate. Every response is deterministic JSON with `content-type: application/json` and `cache-control: no-store`. Exceptions do not place stack traces, environment variables, local paths, or temporary names in the response.

## Safe logging

One JSON log record is emitted per request with only:

- `request_id` (Lambda request ID, API Gateway request ID, or generated UUID);
- `domain`;
- approved `bundle_id`/sector-pack ID;
- `status`;
- `duration_ms`;
- `engine_duration_ms`.

Assessment bodies, financial exposures, controls, insurance values, raw results, paths, environment variables, and secrets are not logged.

## Artifact choice and layout

ZIP is the selected artifact. The measured deterministic package is 17,346,892 bytes compressed and 57,226,444 bytes uncompressed (1,200 files), below the 50 MiB direct ZIP and 250 MiB uncompressed limits. A container image is therefore unnecessary.

The ZIP layout keeps `src/` so existing project-root resolution remains runtime-neutral:

```text
/var/task/
  numpy, openpyxl, et_xmlfile
  src/crq, src/it_crq, src/ot_crq, src/it_ot_crq
  model/
  sector_packs/
  config/
  contracts/mappings/model-bundle-source-map.json
```

Lambda sets `PYTHONPATH=/var/task/src` and `TMPDIR=/tmp`. Model and pack assets are packaged read-only, and their existing hashes are still verified. The Phase 2 facade creates a unique `TemporaryDirectory` per invocation under `/tmp` and cleans it automatically. It neither writes to the package directory nor reuses assessment artifacts.

`scripts/build_lambda_package.py` downloads only pinned Linux arm64 binary wheels, fixes ZIP timestamps and modes, and sorts entries. Two consecutive builds produced the same SHA-256: `f774ad19a502488a07cf14280037f9902b9ff9b55471ffea2be05b12e2844a16`. Full measurements and Terraform base64 hash are in `lambda-package-report.json`.

## Terraform resources and permissions

`infra/phase3b` creates only:

- one Lambda function (`arm64`, Python 3.12, 2,048 MiB, 60 seconds, 512 MiB ephemeral storage);
- one API Gateway HTTP API, one Lambda proxy integration, exactly two routes, and one default stage;
- one CloudWatch log group with configurable retention;
- one Lambda execution role and inline logs-only policy;
- one Lambda invoke permission for that HTTP API.

The execution role permits only `logs:CreateLogStream` and `logs:PutLogEvents` on the dedicated log group. Terraform creates the group, so Lambda does not need `logs:CreateLogGroup`. No S3, RDS, Secrets Manager, Cognito, VPC, queue, workflow, container service, or external AWS permission is present.

CORS defaults to `http://localhost:3000` and must be set to explicit deployed frontend origins later. The endpoint has no authentication and is not production-public-ready.

## Lambda-boundary measurements

No AWS account execution was available in this phase. `lambda-boundary-benchmark.json` therefore records source-equivalent local arm64 cold/warm handler runs; it is not presented as an AWS benchmark.

| Case | Adapter import | Cold total | Warm handler | Cold engine | Peak RSS | Response |
|---|---:|---:|---:|---:|---:|---:|
| IT Financial Services 500k | 113 ms | 9,539 ms | 9,541 ms | 7,670 ms | 479 MiB | 211 kB |
| OT Power Generation 500k | 67 ms | 8,708 ms | 8,763 ms | 6,214 ms | 1,159 MiB | 2.07 MB |

Cold and warm canonical parity hashes match for both cases. Invocation-specific result hashes differ correctly because run IDs and timestamps differ. IT FS and OT PG Lambda-event integration tests compare the returned CRQResult with the corresponding Phase 3A complete example result after excluding only documented transient invocation metadata; all quantitative and stable provenance fields are exact.

The 2,048 / 3,072 / 4,096 MiB AWS matrix is explicitly unmeasured. The deployment plan is to publish one immutable function version and run one cold plus at least five warm invocations per case at each memory value, recording Lambda `INIT_REPORT`/`REPORT`, billed duration, max memory, engine/application timings, response size, and canonical parity hash. Local RSS indicates 2,048 MiB is a defensible starting point, but only AWS measurements may select the final memory tier.

## Commands

```bash
python scripts/build_lambda_package.py
terraform -chdir=infra/phase3b fmt -check
terraform -chdir=infra/phase3b init -backend=false
terraform -chdir=infra/phase3b validate
```

For deployment, pass the ZIP path and `base64sha256` from the package report as Terraform variables. No deployment was performed in this phase.

## Verification record

The final tree produced these outcomes:

| Command | Outcome |
|---|---|
| `pytest tests/unit/test_lambda_http_boundary.py tests/unit/test_lambda_packaging.py -q` | 16 passed |
| `pytest tests/integration/test_lambda_adapter.py -q` | 2 passed; IT FS and OT PG at 500k |
| `pytest tests/unit/test_application_service_boundary.py tests/unit/test_contract_artifacts.py -q` | 23 passed |
| `pytest tests/integration/test_application_service.py -q` | 4 passed; all production domains exact against Phase 2 |
| `pytest tests/integration/test_structured_execution_facade.py -q` | 6 passed |
| `pytest tests/regression/test_approved_baselines.py -q` | 9 passed |
| `pytest tests/integration -q` | 28 passed |
| `pytest tests/security tests/integration/test_workbook_integrity.py -q` | 19 passed |
| `pytest` | 198 passed, 1 skipped |
| Ruff on changed Python files | passed |
| `bandit -q -r src -ll` | passed; no medium/high findings |
| `pip-audit -r requirements.txt --cache-dir /tmp/crq-pip-audit-cache` | no known vulnerabilities |
| `terraform -chdir=infra/phase3b fmt -check -diff` | passed |
| `terraform -chdir=infra/phase3b validate` | valid configuration |
| two consecutive `scripts/build_lambda_package.py` runs | identical SHA-256 |

Approved baseline registry/correction hashes were checked before and after the work and are unchanged. No IT engine, OT engine, router, sector-pack, baseline, or production fixture file changed.

## Still missing before user exposure

1. Authentication/authorization and tenant isolation (Cognito is deliberately absent).
2. Actual Lambda 2/3/4 GiB benchmarks and final memory/cost selection.
3. A deployment environment, domain/TLS policy, production CORS origins, throttling/quotas, and abuse protection.
4. Audit/persistence policy for assessments and results; currently the service is intentionally stateless.
5. Operational alarms, dashboards, runbooks, and data-classification/logging review.
6. Frontend, reporting/export workflow, and grounded narrative integration.

## Minimum next web-product step

Do not begin the full frontend yet. First deploy Phase 3B to a non-production AWS environment, execute the governed 2/3/4 GiB benchmark matrix, verify parity and response limits, then add Cognito-backed authentication plus a minimal tenant-aware persistence design. Only after that boundary is governed should a React assessment workflow consume it.
