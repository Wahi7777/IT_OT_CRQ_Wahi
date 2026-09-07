# Phase 4B — V1 frontend implementation

Status: implemented locally against governed contracts

## Outcome

The V1 React/TypeScript frontend is implemented under `frontend/`. It supports approved-artifact demo mode and a replaceable real HTTP adapter aligned to the Phase 4A asynchronous OpenAPI contract. It contains no quantitative calculations and does not modify or bypass the CRQ application/engine boundary.

The product uses the existing `CRQAssessment`, `ModelBundle`, `CRQResult`, field inventory, frontend placement map and output mapping. Approved IT Financial Services and OT Power Generation request/result examples are imported directly from `contracts/examples`; no demo risk values are fabricated.

## Routes and pages

| Route | Page |
|---|---|
| `/login` | Placeholder login shell; no credential transmission or Cognito |
| `/assessments` | Assessment portfolio/dashboard |
| `/assessments/new` | IT/OT domain and approved-pack selection |
| `/assessments/:id/assessment-setup` | Common setup and resolved bundle/runtime |
| `/assessments/:id/organisation-exposure` | IT organisation and exposure |
| `/assessments/:id/facility` | OT facility |
| `/assessments/:id/it-architecture` | IT architecture/routes |
| `/assessments/:id/ot-architecture-topology` | OT topology |
| `/assessments/:id/it-controls` | IT controls |
| `/assessments/:id/ot-controls` | OT controls |
| `/assessments/:id/it-business-impact` | IT impact overrides |
| `/assessments/:id/ot-business-impact` | OT business impact |
| `/assessments/:id/ot-loss-driver-assumptions` | Locked OT driver assumptions |
| `/assessments/:id/outside-in-evidence` | Outside-in evidence |
| `/assessments/:id/it-assumptions-overrides` | IT permitted overrides |
| `/assessments/:id/ot-assumptions-overrides` | OT prudence and locked assumptions |
| `/assessments/:id/risk-appetite-insurance` | Appetite and insurance inputs |
| `/assessments/:id/review-run` | Readiness, provenance and submission |
| `/runs/:runId` | QUEUED/RUNNING/COMPLETED/FAILED state |
| `/results/:runId/overview` | Executive summary and AI placeholder |
| `/results/:runId/risk-drivers` | Formation funnel and actors |
| `/results/:runId/scenarios` | Scenario contributions |
| `/results/:runId/attack-paths` | IT route/OT path state records |
| `/results/:runId/business-impact` | Loss categories and domain impacts |
| `/results/:runId/treatment` | Current/post-treatment outputs |
| `/results/:runId/insurance` | Insurance outputs or explicit canonical empty state |
| `/results/:runId/uncertainty` | Monte Carlo uncertainty and limitations |
| `/results/:runId/evidence` | Evidence, provenance and mapping coverage |

## Component architecture

```text
App / AppFrame
├── LoginPage
├── DashboardPage / CreateAssessmentPage
├── AssessmentShell
│   ├── AssessmentSectionPage
│   ├── FieldGroup
│   │   ├── editable Question/Value fields
│   │   ├── LockedReference banner
│   │   ├── Evidence-only banner
│   │   └── permitted Override treatment
│   └── ReviewRunPage
├── RunPage
└── ResultsShell
    ├── MetricCard / FinancialBars / RiskFunnel / RankedList
    ├── nine result route renderers
    └── AIPlaceholder
```

`AssessmentContext` holds only current-session form state and the data-mode selection. No broad state-management dependency was added. `fieldExpansion.ts` expands governed grouped inventory records into the approved request's concrete fields while respecting `item_keys` and `parameter_keys`; workbook legend/display rows are not promoted into assessment controls.

## Ownership enforcement

The field inventory remains authoritative:

- `USER_INPUT` and non-inert `EVIDENCE_ONLY` fields use controls only when the inventory permits editing.
- `PERMITTED_OVERRIDE` uses an amber, explicitly attributed visual treatment.
- `GOVERNED_PACK_INPUT`, `DERIVED`, `DISPLAY_ONLY` and `INACTIVE_LEGACY` never render an editable control.
- identifiers such as control, route and driver IDs remain locked even inside editable grouped records.
- inert OT control evidence and inactive employee/customer fields remain read-only and are labelled as non-quantitative/inactive.
- the machine coverage test resolves every inventory entry to exactly one domain-appropriate Phase 4A screen.
- sector selection is resolved through `config/sector_pack_registry.json`; a
  domain/sector/pack mismatch is a blocking validation error.
- demo submission is limited to the two packs with approved Phase 4B result
  artifacts (IT Financial Services and OT Power Generation). Other registered
  OT workflows remain navigable but require real API mode to run, preventing
  Power Generation results from being relabelled as another pack.

## Data and API adapters

`DemoRunApi` uses the approved repository examples and exercises the exact persisted lifecycle:

```text
QUEUED -> RUNNING -> COMPLETED
                  -> FAILED (supported terminal contract)
```

`HttpRunApi` calls only:

- `POST /v1/assessments/run` with `Idempotency-Key`;
- `GET /v1/runs/{run_id}`;
- `GET /v1/runs/{run_id}/result`.

The Review page shows `SUBMITTING`; the run page polls every 2.5 seconds while non-terminal, uses bounded 5-second transport retry, stops on terminal state and fetches `CRQResult` before routing to results. Result components are identical in demo and API mode.

## Results mapping evidence

All 69 entries in `contracts/mappings/engine-output-to-crq-result.json` are covered by the nine screen-prefix rules in `contracts/frontend/frontend-placement.json`. Frontend tests fail if any output mapping loses a screen. Values are selected and formatted only; the frontend never calculates AAL, VaR, TVaR, frequency, probabilities, treatment reductions or insurance recoveries. Missing optional families, including insurance in the current approved examples, show an explicit “not returned” state rather than zero or an inferred value.

## Design tokens and accessibility

The tokens are in `frontend/src/styles/global.css`:

- neutral canvas `#090B10`;
- glass surfaces at 3.5–13% white with an opaque fallback;
- primary text `#F4F6FA` and AA-oriented secondary contrast;
- restrained indigo/cyan accents;
- semantic green, amber and red only for state/risk meaning;
- 10/17/24 px radii and consistent spacing;
- visible focus rings, semantic navigation, labels, live errors and a skip link;
- tabular/compact financial formatting and data-table alternatives;
- 1180, 900 and 640 px responsive breakpoints.

Queued/running, warnings, evidence review and AI placeholder can pulse at the governed 1.8/2.4-second cadence. `prefers-reduced-motion` collapses all repeated animation to a static state. Blur has a solid-surface fallback.

## Verification

The implementation adds Vitest/Testing Library checks for:

- complete input placement;
- governed/inactive editability barriers;
- active input rendering;
- demo run lifecycle;
- exact HTTP route/idempotency behavior;
- all 69 result mapping families;
- canonical headline and AI placeholder rendering;
- responsive breakpoints, reduced motion and non-blur fallback.

The Review & Run gate validates the full submission with AJV against both
`assessment-run-request.schema.json` and its referenced
`crq-assessment.schema.json`. Approved IT and OT requests pass; blocking
schema errors are listed and disable submission. Displayed engine,
methodology, bundle and sector-pack versions come from approved result
provenance rather than UI constants.

Verification completed on 2026-09-07:

| Command | Outcome |
|---|---|
| `cd frontend && npm test` | 5 files, 17 tests passed |
| `cd frontend && npm run build` | TypeScript and Vite production build passed |
| `.venv/bin/pytest` | 203 passed, 1 skipped in 311.67 seconds |

The Vite build reports a large-chunk warning because the approved OT result
artifact is intentionally embedded for offline demo mode. It is not a test or
build failure and is retained as a deployment blocker below.

The production build type-checks before bundling. Browser review covered login, portfolio, OT controls, Review & Run, lifecycle completion, executive Overview, Risk Drivers, Attack Paths and the supported 400 CSS-pixel mobile layout. The responsive check found no horizontal overflow at the supported mobile viewport.

## Deferred blockers before Cognito/S3-backed deployment

1. Implement and deploy the Phase 4A API Lambda, SQS worker, S3 state machine and conditional/idempotent writes.
2. Add Cognito and tenant-scoped authorization before exposing any endpoint or persisted assessment.
3. Decide cross-session assessment listing/draft persistence; the current dashboard is approved-demo/current-session only.
4. Generate typed clients from the final deployed OpenAPI URL and add authenticated error/renewal handling.
5. Add CSP, production CORS, rate limits, WAF/abuse controls, S3 encryption/versioning/retention and operational alarms.
6. Return server-authoritative bundle resolution and validation metadata/errors; client validation is an early usability gate, not an authority boundary.
7. Add governed report/export generation; current buttons are presentation placeholders.
8. Define the deterministic narrative endpoint and verifier in a later phase; the AI panel remains placeholder-only.
9. Code-split or server-fetch the large approved OT demo artifact before public deployment. The current gzip bundle is acceptable for local governed demonstration but should not be the final delivery strategy.
10. Add assessment currency to the canonical result or status projection. The
    approved IT request supplies USD while the approved OT request leaves
    currency null; the UI now says “currency units/not specified” when the
    contract has no currency and never substitutes AED or another currency.

No Cognito, RDS, S3, Lambda, SQS, GenAI, Step Functions, Fargate, quantitative formula, model assumption or deployment infrastructure is implemented in Phase 4B.
