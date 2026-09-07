# Phase 4A — governed runtime equivalence and product experience design

Status: design complete; no frontend or AWS implementation in this phase

Evidence commit: `ccb2ac344a9ab5c62ff893dae8f9a86f12abde9a`

Quantitative change: none

Approved baseline change: none

## 1. Decision summary

Phase 3C's macOS/Linux arm64 deltas are accepted as **platform numerical equivalence**, not methodology drift. The governed policy is machine-readable at `contracts/policies/numerical-equivalence-policy.json`. Exact comparison remains the default. Only the three mirrored IT annual-event-probability paths and the single mirrored OT empirical-LEC ordinate may use the recorded narrow limits. Headline AAL, VaR, TVaR, event frequency and P(any event) remain exact.

V1 execution becomes asynchronous:

```text
React frontend -> API Gateway -> API Lambda -> SQS (batch window 0)
               -> Worker Lambda -> unchanged CRQ application/engine -> S3
```

The API Lambda validates the envelope, creates durable input and `QUEUED` status objects, sends a minimal queue message, and immediately returns `run_id`. The worker changes status to `RUNNING`, invokes the existing application boundary, writes the canonical `CRQResult`, and finally writes `COMPLETED`; safe terminal errors produce `FAILED`. Quantitative code does not know whether it runs in Lambda or a future runtime.

The complete web product is designed against `CRQAssessment`, immutable `ModelBundle`, JSON-Schema validation metadata, and `CRQResult`. It does not invent model inputs. Model-owned assumptions are locked references, evidence is visibly non-quantitative where applicable, and inactive workbook fields never become active.

## 2. Numerical-equivalence governance

Comparison is allowed only when assessment hash, bundle hash, engine/methodology/schema/pack versions, seed, simulation count and quantitative runtime configuration match exactly. Otherwise the two runs are `NOT_COMPARABLE`.

| Surface | Rule | Limit and rationale |
|---|---|---|
| Categorical/configuration/path states/IDs/versions/stable hashes | Exact | These values have no legitimate platform variance. `CLOSED` and `UNKNOWN` remain distinct. |
| Headline AAL, VaR95/99, TVaR95/99, frequency, P(any) | Exact | Phase 3C proved these stable and they are executive quantitative outputs. |
| All other numbers | Exact by default | A tolerance must never spread through broad recursive “close enough” comparison. |
| IT annual-event probability, three identified mirror patterns | Absolute **and** relative | `abs <= 1.2e-16` and `rel <= 6.5e-14`; observed `1.1102230246251565e-16`, from the platform `libm` final bits of `1-exp(-x)`. |
| OT prudent LEC x-coordinate at index 91, three identified mirror patterns | Absolute **and** ULP | `abs <= 4.0e-9` and `<= 2 ULP`; observed `3.725290298461914e-9`. No other ordinate is included. |

An invocation result hash always verifies its own complete payload exactly. It is not compared between invocations because run identity and timestamps are included. Stable input, bundle, pack and artifact hashes remain exact. A separate equivalence attestation records the policy version, every accepted pointer, deltas, and all exact failures; it never substitutes a new hash.

Any new pointer, exceeded limit, changed headline, or failed precondition fails the gate and opens a drift investigation. The policy cannot regenerate, approve, or rewrite a baseline. This closes the Phase 3C parity issue without modifying the engine, methodology, pack, accepted result, or general regression threshold.

## 3. Minimum asynchronous AWS design

### Responsibilities and trust boundaries

| Component | Minimum responsibility |
|---|---|
| React frontend | Validate for usability, submit canonical request, retain `run_id`, poll status, fetch result. Browser validation is never authoritative. |
| API Gateway | TLS edge, route/size/throttle controls; Cognito is deferred, so this design is not production-public-ready. |
| API Lambda | Authoritative request/schema/bundle-reference validation; create S3 input/status using conditional writes; enqueue identifiers and hashes; return 202. No calculation. |
| SQS | One message per run, batch size 1, maximum batching window 0, visibility timeout greater than worker timeout, DLQ after a governed retry count. Queue carries references, not assessment bodies. |
| Worker Lambda | Claim queued run idempotently; set `RUNNING`; read and re-hash assessment; call the existing runtime-neutral application service; validate/write result; set terminal state. |
| CRQ application/engine | Existing structured execution boundary and unchanged IT/OT quantitative semantics. No AWS imports. |
| S3 | Durable assessment input, current status, completed canonical result; encryption, versioning and tenant-prefixed access are implementation requirements. |

RDS, Step Functions and Fargate are explicitly excluded. S3 conditional writes and the run state document provide minimum idempotency. A duplicate SQS delivery must observe an existing `RUNNING` or terminal status and must not create a second logical result. The worker writes the result before `COMPLETED`; the frontend can therefore never observe completion without a fetchable result. A failed result write leaves a retryable non-terminal state or becomes `FAILED`—never a false completion.

### Lifecycle

```text
SUBMITTING (client only)
    -> QUEUED -> RUNNING -> COMPLETED
                       \-> FAILED
```

Only the service persists `QUEUED`, `RUNNING`, `COMPLETED`, and `FAILED`. State transitions are monotonic and timestamped. `RUNNING` may expose `VALIDATING`, `EXECUTING`, or `FINALISING`; no invented completion percentage is shown.

### Storage contract

| Key | Content | Write rule |
|---|---|---|
| `assessments/{assessment_id}/input.json` | Validated `AssessmentRunRequest`/`CRQAssessment` reference and immutable hashes | Conditional create or exact idempotent replay |
| `runs/{run_id}/status.json` | Lifecycle, timestamps, safe error, links | Conditional/optimistic state transition |
| `runs/{run_id}/result.json` | Validated `CRQResult` | Write once before terminal completion |

The machine-readable API is `contracts/api/async-run-api.openapi.json`. `POST /v1/assessments/run` requires `Idempotency-Key` and returns 202 `QUEUED`. `GET /v1/runs/{run_id}` returns current state. `GET /v1/runs/{run_id}/result` returns 200 only for a completed result, 202 while pending, 409 for failed, and 404 for an unknown or inaccessible run. Error bodies are safe and never contain assessment values, stack traces, paths, environment variables or secrets.

## 4. Complete sitemap

```text
/login
/assessments                         Assessment dashboard
/assessments/new                     Create assessment
/assessments/:assessmentId/
  setup                              Domain, pack and reporting basis
  organisation-exposure              IT identity and financial exposure
  facility                           OT identity and facility scale
  architecture                       IT routes or OT topology
  controls                           Domain control assessment
  business-impact                    Exposure/BIA and permitted impact overrides
  loss-driver-assumptions            OT governed driver references
  outside-in                         Outside-in evidence
  assumptions-overrides              Governed references and permitted overrides
  appetite-insurance                 Appetite and programme structure
  review                             Readiness and Run CRQ
/runs/:runId                          Queued/running/failed state
/results/:runId/
  overview
  risk-drivers
  scenarios
  attack-paths
  business-impact
  treatment
  insurance
  uncertainty
  evidence
```

Global drawers: assessment navigation, validation issues, evidence detail, and locked ModelBundle/methodology provenance. Global actions: save draft (future persistence), validate, run, export, and AI Risk Interpretation placeholder.

## 5. User journey

1. Sign in and open the assessment dashboard. Authentication behavior is a visual contract only in this phase.
2. Create an assessment; select IT/OT, supported sector/asset, and approved bundle. Incompatible choices are blocked using schema and bundle applicability.
3. Follow a domain-aware stepper. Each save validates the current section; cross-field validation runs continuously but is summarized without blocking unrelated editing.
4. Review readiness: required/optional counts, errors, warnings and evidence coverage, plus resolved versions and run configuration.
5. Submit. The button enters `SUBMITTING`; a 202 response transitions to the run page with `QUEUED` and a resumable `run_id` URL.
6. Poll status every 2.5 seconds. On `COMPLETED`, fetch the result and replace the run page with Overview. On `FAILED`, preserve assessment state and present a safe correlation ID and retry rule.
7. Explore quantitative results and trace every derived statement to result data. Generate no narrative yet; the AI panel remains a stateful placeholder.
8. Compare governed treatment and insurance outputs, then export when a later export adapter is implemented.

## 6. Input card grammar and ownership

Every field card contains: question/label; suitable control; concise explanation; “why this matters”; evidence/source; confidence (`High`, `Medium`, `Low`, or `Not assessed`); required/optional; validation state; and value origin (`Entered`, `Inherited`, `Overridden`, `Locked`, `Derived`, `Evidence only`, or `Inactive`). Help text comes from governed validation metadata, never ad hoc UI calculations.

Example topology card:

```text
Can the corporate network reach critical production systems?      Required
○ Yes  ○ No  ○ Unknown                                             Entered

Why this matters  Determines whether applicable user-originated routes remain feasible.
Evidence          Reported · Verified · Observed · Assumed          Confidence: Medium
Validation        Valid
```

`UNKNOWN` is a first-class answer and never renders as `CLOSED`. Architecture feasibility and control effectiveness occupy separate cards and separate result layers.

| Classification | Web treatment |
|---|---|
| `USER_INPUT` | Editable question card subject to canonical validation. |
| `PERMITTED_OVERRIDE` | Amber-edged override card; permission, rationale, evidence, actor and timestamp required. Original inherited value remains visible. |
| `GOVERNED_PACK_INPUT` | Locked reference card with pack/version/calibration provenance. Never an ordinary form input. |
| `DERIVED` | Read-only resolved value; calculation source is named. |
| `EVIDENCE_ONLY` | Evidence card explicitly marked “no direct quantitative effect” unless a separately approved override exists. |
| `DISPLAY_ONLY` | Recreated only when useful presentation; never submitted as an assessment input. |
| `INACTIVE_LEGACY` | Hidden by default or shown as inactive migration context; cannot affect validation readiness or results. |

Machine-enforced placement is in `contracts/frontend/frontend-placement.json`. Every one of the 51 grouped inventory entries resolves to one canonical screen location. Repeated canonical patterns representing different domain/classification slices share that location but retain their own inventory-driven renderer; expanded field instances inherit the placement.

## 7. IT input screen map and page wireframes

| Screen | Canonical content | Wireframe-level layout |
|---|---|---|
| Assessment setup | `assessment.domain/sector/asset_type/reporting_basis`; requested/resolved bundle; runtime; TVaR selection | Header with step status; two-column selector grid; locked “Resolved model” rail; compatibility errors inline; footer Back/Continue. Runtime values are read-only except the existing TVaR selection. |
| Organisation & exposure | IT `assessment.{parameter}`; active financial exposure; exposure-model flag; inactive employees/customers | Left two-thirds identity/exposure cards grouped by units; right summary with financial scale and completeness. Inactive fields appear only in an expandable migration note. |
| IT architecture | Routes, applicability/feasibility, opportunity, S1–S5/impact overrides, attached evidence | Route list left; selected route detail centre; evidence drawer right. State badge is `OPEN`, `CONDITIONAL`, `CLOSED`, or `UNKNOWN`. Feasibility and controls are not collapsed into one score. |
| IT controls | Control maturity/coverage plus evidence IDs | Filterable control groups; assessment cards in centre; evidence panel. Quantitative maturity/coverage is visibly separated from evidence metadata. |
| Business impact | Rate and scenario parameter overrides | Baseline locked value beside permitted P50/P99 override; unit/range validation; impact area preview contains no newly calculated risk metric. |
| Assumptions & overrides | Frequency adjustments; immutable pack references in drawer | Override register with inherited/current values, rationale, evidence and audit identity. Locked actor/scenario/route priors appear only in reference mode. |
| Outside-in evidence | Apply flag, structured evidence, hidden legacy path | Coverage summary above evidence table. Evidence can support review; legacy file path is never exposed. |
| Risk appetite & insurance | Appetite parameters, retention, primary/aggregate limits, layers | Appetite cards then an insurance tower visual beside an editable layer table; cross-field reconciliation/errors beneath. |
| Review & Run | Derived reporting basis, validation and resolved provenance | Readiness panel, issue list and locked run identity; single primary Run CRQ action. |

IT routing preserves workbook semantics: six routes, stage progression and evidence remain distinct. Pack-owned route matrices, actor/scenario priors and dependency assumptions remain locked.

## 8. OT input screen map and page wireframes

| Screen | Canonical content | Wireframe-level layout |
|---|---|---|
| Assessment setup | Common selection, reporting basis, runtime and resolved bundle | Same shell as IT; only approved OT sector/asset combinations appear. Simulation and seed remain resolved/read-only under current inventory. |
| Facility | OT `assessment.{parameter}` | Facility identity and geography at left; production scale/context at right; clear units and required state. |
| OT architecture & topology | Seven topology responses | One decision card per topology question with Yes/No/Unknown, explanation and evidence. A small topology map summarizes answers but does not infer closures. |
| OT controls | 52 maturity/coverage inputs plus tested/result/evidence metadata | Search/filter rail; virtualized card/table hybrid; quantitative columns separated by a divider from evidence-only columns. |
| Business impact | Revenue/asset/exposure fields; inactive employees | Financial and operational exposure cards with unit validation; employee field hidden/inactive. |
| Loss-driver assumptions | Driver applicability/rates/quantities/formulas and scenario impact | Fully locked pack-reference table/cards, pack provenance and calibration status. The page explains why client editing is prohibited. |
| Assumptions & permitted overrides | Prudence override; reference campaigns, actors, scenario difficulty, exposure map, geography/sector multipliers, propensity and TTP applicability | Prudence is the only editable override and requires governance metadata. All other values render as locked reference sections, hidden where the source inventory marks them hidden. |
| Outside-in evidence | Same common evidence contract | Same common pattern; evidence cannot silently alter calculations. |
| Risk appetite & insurance | Common appetite/programme | Same common pattern, with OT-relevant labels and units only. |
| Review & Run | Readiness and resolved provenance | Same common pattern; emphasizes OT pack/calibration/asset applicability. |

OT S1–S5 semantics are preserved in results. Architecture/path applicability, topology feasibility, control barriers and stage-through probabilities remain separate layers.

## 9. Readiness screen

The hero panel shows:

```text
Required inputs       x/x       Domain               IT or OT
Optional inputs       x/x       Sector pack          ID + version
Validation errors     x         Engine version       resolved
Warnings              x         Methodology version  resolved
Evidence coverage     x%        Simulation count     resolved
                                Reporting basis      selected/resolved
```

Below it, tabs group blocking errors, warnings, evidence gaps, overrides and locked assumptions. Each issue links to its exact field. The Run CRQ button is disabled only for blocking validation, incompatible bundle or missing required input; warnings require acknowledgement but do not get silently coerced. Readiness counts exclude display-only and inactive fields. Evidence-only completeness contributes to evidence coverage, not quantitative input completeness.

## 10. Async run UX and states

| State | UI behavior |
|---|---|
| `SUBMITTING` | Disable duplicate submit, show neutral spinner, retain draft. If the response is uncertain, replay the same idempotency key. |
| `QUEUED` | Pulsing queue icon, submission time and “safe to leave” copy; begin 2.5-second polling. |
| `RUNNING` | Pulsing execution icon and named phase; no fabricated percent or countdown. |
| `COMPLETED` | Stop polling, fetch result once, route directly to Overview; announce completion accessibly. |
| `FAILED` | Stop polling; show safe message, retryability and correlation ID; retain assessment and link back to offending fields where supplied. |

Polling uses TanStack Query with a 2,500 ms interval for non-terminal states, stops when the tab is hidden if the browser can resume safely, immediately refreshes on focus, uses bounded backoff only for transport errors, and never retries a deterministic 4xx. A page reload recovers from the URL `run_id`. A missing result after `COMPLETED` is treated as a service integrity error, not an empty result.

## 11. Results screen map

| Screen | Canonical families | Layout and interactions |
|---|---|---|
| Overview | `run`, `provenance`, `summary` | Top cards: AAL, prudent VaR99, prudent TVaR99, P(material event, using the canonical applicable probability), appetite status and evidence confidence. Annual-loss chart, top drivers, top treatment and AI placeholder below. Best/prudent toggle never recomputes values. |
| Risk Drivers | `formation`; actor and actor-scenario decomposition | Interactive funnel: Campaigns → Actor → Scenario → Route/path → Architecture feasibility → Control effectiveness → Successful event → Financial impact. Selecting a stage highlights governed downstream facts only. |
| Scenarios | scenario, IT route and OT path/TTP decomposition | Scenario cards show engine-supplied AAL contribution, TVaR contribution where present, frequency/probability, actors, paths and financial drivers; drill-down preserves source labels. |
| Attack Paths | all `architecture` outputs | IT state matrix (`OPEN/CONDITIONAL/CLOSED/UNKNOWN`) with gates, TTPs, barriers, stage-through and path success. OT presents S1–S5 progression, applicability and feasibility without merging control effectiveness. |
| Business Impact | `loss`, `impact` | AEP/OEP and return-period chart; BI/non-BI split; categories/drivers; AAL/VaR/TVaR selector only where those series exist; OT downtime/capacity or IT records/endpoints/services. |
| Treatment | `treatments`, `sensitivity` | Ranked individual controls and packages; current versus post-treatment values; engine-calculated AAL/tail reduction; sensitivity detail. No UI-side reduction arithmetic. |
| Insurance | all `insurance` | Ground-up → retention → recoveries → residual waterfall; programme tower; attachment/exhaustion probability and reconciliation. Values come directly from `CRQResult`. |
| Uncertainty | Monte Carlo and evidence limitations | Simulation uncertainty, high-uncertainty areas, evidence gaps and limitations. Distinguish sampling uncertainty from evidence quality. |
| Evidence | provenance and compatibility/raw extension references | Evidence coverage/composition, bundle/calibration status, versions and limitations. Legacy extension is inspectable for governance, not an executive primary view. |

All 69 machine-readable output mappings resolve to at least one screen. Underlying outputs remain in the result even when an executive page initially summarizes them.

### AI placeholder only

`AI Risk Interpretation` is a panel shell with `NOT_GENERATED`, `GENERATING`, `READY`, and `FAILED`. Phase 4A defines no prompts, narrative taxonomy, model, endpoint or quantitative behavior. The eventual feature must consume only a deterministic `NarrativeFactBundle`; it may never calculate or infer a numeric metric.

## 12. Component inventory

App shell: `AppFrame`, `PrimaryNav`, `AssessmentStepper`, `PageHeader`, `Breadcrumbs`, `CommandBar`, `MethodologyDrawer`.

Forms: `QuestionCard`, `LockedReferenceCard`, `OverrideCard`, `DerivedValueCard`, `EvidenceCard`, `ConfidenceControl`, `OriginBadge`, `ValidationMessage`, `MoneyInput`, `PercentInput`, `EnumRadioGroup`, `LayerTable`, `ControlMatrix`, `TopologyQuestion`, `FieldHelp`.

Readiness/run: `ReadinessScorecard`, `IssueList`, `RunIdentityCard`, `RunButton`, `RunStatusPanel`, `StatusPulse`, `SafeFailurePanel`.

Results: `MetricCard`, `BasisToggle`, `AnnualLossChart`, `LossExceedanceChart`, `FrequencyFunnel`, `ScenarioCard`, `ActorTable`, `AttackPathExplorer`, `StageProgression`, `LossDriverWaterfall`, `TreatmentComparison`, `InsuranceTower`, `UncertaintyPanel`, `EvidenceCoverage`, `LimitationsList`, `ProvenanceCard`, `AIRiskInterpretationPlaceholder`.

Primitives: accessible button/input/select/dialog/tabs/tooltip/table/skeleton/toast; `GlassPanel`; semantic badges; chart table fallback; visually hidden live region.

## 13. Glassmorphic design system

The visual character is a high-end financial risk platform: charcoal/navy neutral canvas, translucent surfaces, crisp numbers, restrained indigo/teal accents, and semantic status colors. It must not use cyber-green, scan-line motifs or pervasive glow.

| Token | Direction |
|---|---|
| Background | `#090B10` base with low-saturation radial navy/graphite gradients |
| Glass surface | white at 5–9% opacity, `backdrop-filter: blur(18px)`, solid fallback at `#151922` |
| Elevated glass | 10–13% opacity, 1 px white at 12–16%, soft 24–48 px black shadow |
| Text | primary `#F4F6FA`, secondary near `#B5BDCB`, muted no lower than WCAG AA |
| Accent | restrained indigo for actions; desaturated cyan only for selected analytical data |
| Semantic | red for material breach/error, amber for caution/override, green for completed/within appetite; never color alone |
| Typography | Inter or system sans for UI; tabular numerals; 16 px body minimum; 12–14 px only for supporting labels |
| Radius/space | 12/18/24 px radii; 4/8/12/16/24/32 px spacing rhythm |
| Focus | 2 px high-contrast focus ring with offset; visible on every interactive element |

Panels use blur only when supported and maintain opaque contrast fallbacks. Charts use patterns/markers and accessible tables as alternatives. Financial values align on decimals and always display unit, currency and basis.

### Motion and pulse rules

Pulse only for queued/running work, unresolved material warning, high-risk alert, new AI insight, stale assessment, or evidence requiring review. Standard cadence is 1.8 seconds ease-in-out, opacity 0.62–1.0, with at most one primary and two secondary pulses in a viewport. High-risk uses a single 2.4-second low-amplitude halo, not rapid flashing. Success does not pulse after its entry transition.

`prefers-reduced-motion: reduce` removes scale, translation and repeated opacity animation; pulse becomes a static icon plus explicit status text. No animation exceeds three flashes per second. Exploration of the risk funnel uses 160–220 ms transitions and only animates the selected connection.

## 14. Responsive, loading, error and empty behavior

Desktop (≥1200 px): 12-column layout, persistent navigation, main content 8–9 columns and context rail 3–4. Tablet (768–1199): collapsible navigation, two-column cards, evidence as drawer. Mobile (<768): single column, sticky bottom actions, horizontally scrollable data table with card alternative, charts simplified but never data-truncated.

Skeletons mirror the final layout and avoid fake numeric data. Empty states distinguish “not entered,” “not applicable,” “not generated,” and “not returned.” Validation errors appear at field and page summary, focus the first invalid field on submit, and persist until resolved. Network errors retain entered data and expose retry. Authorization/not-found screens do not reveal tenant existence. Charts with absent optional series explain why rather than substituting zero.

## 15. Frontend API and contract mapping

| Frontend action | Contract/API | Handling |
|---|---|---|
| Render/validate input | `crq-assessment.schema.json`, `field-inventory.json`, selected `ModelBundle` metadata | Curated schema-driven components; server revalidates. |
| Display locked assumptions | `model-bundle.schema.json` and approved bundle projection | Never merge into normal editable form state. |
| Submit run | `POST /v1/assessments/run` with existing AssessmentRunRequest and idempotency key | Expect 202; persist `run_id` in route state. |
| Observe run | `GET /v1/runs/{run_id}` | Poll at 2.5 seconds while non-terminal. |
| Load results | `GET /v1/runs/{run_id}/result` | Validate against `crq-result.schema.json` before rendering. |
| Map results | `engine-output-to-crq-result.json`, `frontend-placement.json` | UI never reads workbook coordinates or legacy engine keys when a canonical field exists. |
| AI placeholder | Local UI state only | No LLM endpoint or narrative generation in Phase 4A/4B. |

The assessment dashboard is fully designed but cross-session listing is deliberately not claimed by the minimum three-route API. Until a later persistence/listing decision, Phase 4B can show fixture/demo assessments and current-session drafts; it must not scrape S3 or invent an ungoverned listing endpoint.

## 16. Recommended React architecture

Use React + TypeScript + Vite as a simple SPA; React Router for route/layout boundaries; TanStack Query for server state and polling; React Hook Form for section state; AJV 2020-12 for the canonical JSON Schemas; Zustand only for minimal unsaved wizard/UI state if React context proves insufficient; Radix UI primitives with CSS variables/Tailwind utilities for accessible custom visuals; Apache ECharts for loss, funnel and decomposition views; Motion for React plus CSS for the few governed pulses; and `openapi-typescript`/a thin fetch client generated from the OpenAPI contract.

Suggested source boundaries:

```text
src/app/                 routing, providers, shell
src/contracts/           generated types, AJV registry, field registry
src/features/assessment/ wizard screens and ownership renderers
src/features/runs/       submit, polling and terminal-state UI
src/features/results/    result screens/selectors (no calculations)
src/features/ai/         placeholder only
src/components/          accessible primitives and glass components
src/api/                 generated client and error normalization
src/styles/              tokens, themes, reduced-motion rules
```

Selectors may format and select values but must not calculate AAL, VaR, TVaR, probabilities, reductions or recoveries. Formatting preserves raw value access and source pointer. Component tests include keyboard navigation, screen-reader labels, color contrast, reduced motion and 200% zoom/reflow.

## 17. Exact Phase 4B implementation scope

Phase 4B should implement a **local contract-driven frontend prototype**, not AWS production plumbing:

1. Scaffold the React/TypeScript/Vite application and the design-token/accessibility foundation.
2. Generate types from the existing schemas and OpenAPI; wire AJV validation.
3. Implement app shell, sitemap routes, IT/OT guided forms and all classification-specific card renderers using the real canonical examples and field placement map.
4. Implement readiness/validation, including evidence coverage and locked resolved provenance; do not calculate risk metrics.
5. Implement a replaceable `RunApi` interface plus deterministic fixture adapter for `SUBMITTING/QUEUED/RUNNING/COMPLETED/FAILED`; no live AWS deployment.
6. Implement all nine result route shells and the Overview/Frequency Funnel/Attack Path/Business Impact/Treatment/Insurance components against existing `CRQResult` examples. Preserve unshown fields.
7. Implement responsive behavior, empty/error/loading states, selective pulse/reduced-motion rules, keyboard/accessibility tests and contract coverage tests.
8. Add the AI Risk Interpretation placeholder with four UI states only.

Explicitly excluded: Cognito, RDS, production S3, Terraform changes, Lambda/SQS implementation, live API deployment, final exports, GenAI prompts/integration, new quantitative formulas, engine/pack changes and baseline changes.

## 18. Completion evidence

- Numerical policy is explicit, narrow, machine-readable and baseline-neutral.
- Async Lambda + SQS + S3 is the minimum V1 design with zero batching window.
- All requested screens, journeys and wireframe-level layouts are defined.
- Every grouped input inventory entry resolves to one canonical frontend location; governed/inactive fields are mechanically prevented from becoming editable.
- Every one of the 69 existing output mappings resolves to a results screen.
- Design tokens, pulse cadence, reduced motion and responsive/error/loading behavior are explicit.
- Async UI states and three-route API are machine-readable.
- AI remains placeholder-only.
- No quantitative engine, methodology, sector pack, approved baseline or accepted output changed.
