# Phase 6A — View-specific CRQ Copilot

## Decision and boundary

Phase 6A adds interpretation, not calculation. The quantitative result continues to be produced only by the governed application service and Phase 2 facade. The Copilot cannot alter an assessment, select model assumptions, execute a run, calculate a metric, or persist transient chat.

The controlled flow is:

```text
authenticated current view + server-owned assessment/result
  -> deterministic ViewContextBundle
  -> versioned global and view prompt
  -> Amazon Bedrock Converse structured JSON
  -> deterministic schema/fact/entity/number/ranking/path-state verifier
  -> VERIFIED or REJECTED
  -> existing CRQ Copilot panel
```

Only `VERIFIED` answer text is shown. Rejected model text is discarded. A narrow deterministic redirect handles clearly cross-view questions without invoking Bedrock.

## Contracts

- `contracts/schemas/view-context-bundle.schema.json` defines schema version `1.0.0`, stable fact IDs, selected entity, allowed entities, and page suggestions.
- `contracts/schemas/copilot-response.schema.json` defines the only accepted model response shape.
- `contracts/evaluations/copilot-evaluation-set.json` binds the evaluation cases to approved IT Financial Services and OT Power Generation contract examples.
- `contracts/api/phase5a-product-api.openapi.json` adds authenticated query and narrative operations.

Fact IDs are `vf_` plus the first 16 hexadecimal characters of SHA-256 over `context_type|source_path`. They are stable for a contract path and view and contain no source value.

## Context governance

The server builds context from tenant-owned S3 objects. The client may send identifiers, current view, selected entity, and question; it may not send facts or object keys. Each supported view has an explicit source-path allowlist. Raw descriptions, evidence payload/content, hashes, URLs/files, client names, tenant/user identifiers, raw samples, trials, and loss-exceedance arrays are excluded. Lists are bounded and every bundle is capped at 300 facts.

Supported assessment contexts are organization, architecture, controls, business impact, risk appetite/insurance, and review. Supported result contexts are overview, risk drivers, scenarios, attack paths, business impact, treatment, insurance, uncertainty, evidence, plus an executive context used only for the persisted narrative.

## Prompts and model

Prompt version is `1.0.1`. The global prompt requires supplied facts only, no calculation, no external facts, no generic recommendations, exact supplied numeric formatting, canonical metric labels, internal fact citations, view confinement, and concise risk-advisory language. It prohibits unsupported magnitude language, approximations, ambiguous reductions, and non-canonical spellings such as `Tvar99`. Each page adds a specific instruction from `src/crq/copilot/prompts.py`.

V1 provider configuration:

| Setting | Value |
|---|---|
| Provider | Amazon Bedrock |
| API | `bedrock-runtime` Converse |
| Model | `amazon.nova-pro-v1:0` |
| Region | `us-east-1` |
| Max output tokens | 700 |
| Temperature | 0 |
| Response format | Forced Bedrock tool-use with the governed JSON Schema as the tool input schema |

The model was selected after controlled dev-account validation. The initially proposed Anthropic model could not be invoked because that account was not permitted to complete the required AWS Marketplace subscription. Amazon Nova Pro is AWS-native, is available through Bedrock in `us-east-1`, supports Converse/tool use, and passed the governed IT/OT evaluation. The response is constrained through forced tool use and is still independently checked by the deterministic verifier before display.

- https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-amazon-nova-pro.html
- https://docs.aws.amazon.com/bedrock/latest/userguide/conversation-inference-call.html

## Verification

Verification is independent of Bedrock's structured-output enforcement. It rejects:

- malformed or extra response fields;
- mismatched schema version, status, or context;
- missing or unknown cited fact IDs;
- an entity absent from the page/selection allowlist;
- any numeric token not exactly equal to the raw or governed rendered value of a cited numeric fact;
- a dominance/ranking claim not citing the corresponding explicit ranked fact;
- an OPEN, CLOSED, CONDITIONAL, or UNKNOWN claim not supported by a cited state fact.

The formatting allowlist accepts deterministic contract rendering such as `49647805.4145752` or `$49.65M`, and rejects unsupported approximations such as `$50M`.

## APIs and persistence

`POST /v1/copilot/query` loads the authenticated tenant's assessment and, for a result view, its run result. It constructs context server-side and returns `VERIFIED` or `REJECTED`. Queries are not persisted.

`POST /v1/runs/{run_id}/narrative` creates the executive interpretation only after the result exists and persists only a verified response at:

```text
runs/{tenant_id}/{run_id}/narrative.json
```

The record is bound to the exact `result_hash`. A repeated request returns the existing interpretation for that hash; a conflicting hash is rejected. `GET /v1/runs/{run_id}/narrative` enforces the same tenant ownership checks.

## Frontend behavior

The approved Copilot panel and visual design are preserved. Page routing supplies `current_view`; result routing supplies `run_id`; selected entities are included when the page exposes one. Suggested questions are deterministic and page-specific. The user sees IDLE, THINKING, VERIFIED, REJECTED, or FAILED states. No model response text appears in REJECTED or FAILED states.

## Infrastructure and logging

No new compute or datastore is introduced. The existing API Lambda receives `bedrock:InvokeModel` only for the selected foundation-model ARN. Three authenticated API Gateway routes are added. No Bedrock credentials reach the browser. Routine logging continues to exclude prompts, bundles, response text, financial/control inputs, JWTs, and raw evidence.

## Evaluation and limitations

The governed evaluation set contains the original 12 IT Financial Services and OT Power Generation cases plus two free-form organisation cases that exercise an actual Bedrock call after standard panel questions were made deterministic. `scripts/evaluate_copilot.py` supports a context-only preflight and an actual Bedrock run that records fact count, context bytes, context-build time, Bedrock latency, verifier time, and input/output tokens.

Following the product-owner rejection of six responses, standard Overview, scenario, path-state, treatment, risk-driver, business-impact and evidence questions now use deterministic prose assembled exclusively from governed facts. Free-form questions continue through Bedrock and the same fail-closed verifier. The correction adds deterministic percentage/currency renderings and governed comparison facts; it does not add a quantitative model calculation.

The corrected controlled evaluation is recorded in `phase6a-copilot-evaluation-bedrock.json`: all 14 cases were `VERIFIED`, none were `REJECTED`, and the two free-form cases invoked Bedrock successfully. No unverified model text was displayed. AWS deployment and performance evidence from the original Phase 6A validation remain recorded in `phase6a-aws-evidence.json` and `phase6a-performance-evidence.json`; the targeted correction did not modify or redeploy the AWS runtime. The mandatory independent product-owner re-review sheet is `PHASE6A_HUMAN_REVIEW.md`.

Final automated validation completed on 9 September 2026:

- complete Python suite: 295 passed, 1 expected skip;
- frontend component/integration suite: 27 passed across 7 files;
- TypeScript project build: passed;
- frontend lint (`oxlint`, warnings denied): passed;
- frontend production build: passed;
- frontend dependency audit: no known vulnerabilities;
- Ruff, Bandit, pip-audit, Terraform formatting/validation/plan, JSON parsing, and whitespace checks: passed;
- final Terraform plan: no changes.

The frontend result integration test confirms that a route selected in the Attack Paths filter is included as the selected entity in the subsequent Copilot request.

Known limitations:

- V1 stores no chat history and performs no safe cross-view retrieval beyond deterministic navigation.
- The approved OT Power Generation result does not return a route identifier or explicit route/path state in `architecture.route_path_states`; the OT attack-path evaluation therefore remains page-scoped rather than selected-path scoped and the Copilot must not invent a path state.
- S3 narrative idempotency has the same conditional-write limitations documented for Phase 5A; this phase does not add DynamoDB.
- Cost is an estimate from observed Bedrock token counts and the recorded public on-demand token rates; taxes, free-tier effects and later price changes are excluded.

No quantitative code, methodology, sector pack, approved baseline, or numerical-equivalence policy is changed by this phase.
