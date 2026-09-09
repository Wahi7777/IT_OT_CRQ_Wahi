# Phase 6A — Mandatory product-owner response re-review

## Review status

**PENDING PRODUCT OWNER REVIEW**

Six previously rejected responses have been corrected. The four previously accepted responses are included unchanged in substance as regression controls. This file records deterministic verification only and does not self-approve response quality.

Acceptance criteria: factually faithful, useful to a business user, concise, no invented ranking or recommendation, no unsupported qualitative or quantitative claim, canonical metric labels, normal business-facing number formats, and no internal fact identifier in prose.

| Case | Prior decision | Deterministic status | Current human decision | Reviewer / date |
|---|---|---:|---|---|
| IT Overview | Rejected — corrected | VERIFIED | ☐ Accept ☐ Reject | |
| IT Risk Drivers | Accepted — regression control | VERIFIED | Previously accepted | |
| IT Attack Paths | Rejected — corrected | VERIFIED | ☐ Accept ☐ Reject | |
| IT Treatment | Rejected — corrected | VERIFIED | ☐ Accept ☐ Reject | |
| IT Evidence | Accepted — regression control | VERIFIED | Previously accepted | |
| OT Overview | Rejected — corrected | VERIFIED | ☐ Accept ☐ Reject | |
| OT Scenarios | Rejected — corrected | VERIFIED | ☐ Accept ☐ Reject | |
| OT Attack Paths | Rejected — corrected | VERIFIED | ☐ Accept ☐ Reject | |
| OT Business Impact | Accepted — regression control | VERIFIED | Previously accepted | |
| OT Evidence | Accepted — regression control | VERIFIED | Previously accepted | |

## Responses for review

### 1. IT — Overview

**User question:** Explain headline metrics.

**Exact user-facing response:**

> Expected annual loss (AAL) is $1.16M, while severe-loss outcomes are larger in absolute terms: VaR99 is $23.33M and TVaR99 is $49.65M. This means expected annual loss is smaller than the losses represented in the tail of the distribution. The modelled probability of at least one material event during the year, P(Material Event), is 12.76%.

**Deterministic verification:** VERIFIED.

**Supporting governed facts:** Prudent AAL is $1.16M; VaR99 is $23.33M; TVaR99 is $49.65M; P(Material Event) is 12.76%. The governed comparisons confirm that VaR99 is greater than AAL and TVaR99 is greater than VaR99.

**Caveat/refusal reason:** None.

### 2. IT — Risk Drivers

**User question:** What drives this result?

**Exact user-facing response:**

> The dominant actor is Cybercriminal, the dominant scenario is Critical business-service disruption, and the largest AAL loss driver is Business downtime costs.

**Deterministic verification:** VERIFIED.

**Supporting governed facts:** The returned actor ranking identifies Cybercriminal first; the returned scenario ranking identifies Critical business-service disruption first; the returned AAL loss-driver ordering identifies Business downtime costs first.

**Caveat/refusal reason:** None. This previously accepted response is retained as a regression control.

### 3. IT — Attack Paths

**User question:** Why is this route open?

**Exact user-facing response:**

> The current result does not contain a governed path-state value for Identity and credential compromise, so I cannot determine whether it is OPEN or CLOSED. I can still explain its returned probability facts, but this result provides no architecture-gate, barrier or control-state facts that explain a path state.

**Deterministic verification:** VERIFIED.

**Supporting governed facts:** Identity and credential compromise is a returned route with probability and AAL records. None of the approved route records contains a path-state field. The approved barrier, feasibility, applicability, relevant-TTP, and stage-progression collections are empty.

**Caveat/refusal reason:** No path state has been inferred. The canonical result does not contain the facts required to explain an OPEN, CLOSED, CONDITIONAL, or UNKNOWN state.

### 4. IT — Treatment

**User question:** Why is this treatment prioritised?

**Exact user-facing response:**

> The modelled AAL reduction for Asset and vulnerability management is $0.00. On that basis, the current result does not support prioritising this treatment for AAL reduction.

**Deterministic verification:** VERIFIED.

**Supporting governed facts:** The returned treatment is Asset and vulnerability management. Its prudent AAL reduction is $0.00.

**Caveat/refusal reason:** No implementation cost, return on investment, control quality, or practical priority has been inferred. Other treatment metrics are not represented by the AAL statement.

### 5. IT — Evidence

**User question:** Where is the assessment weakest?

**Exact user-facing response:**

> The current result does not contain an explicit governed evidence-quality ranking, so I cannot identify a weakest evidence area.

**Deterministic verification:** VERIFIED.

**Supporting governed facts:** Evidence records are present, but the current result contains no governed evidence-quality ranking.

**Caveat/refusal reason:** The Evidence view can still show returned records without assigning an unsupported priority. This previously accepted response is retained as a regression control.

### 6. OT — Overview

**User question:** Explain the tail risk.

**Exact user-facing response:**

> Expected annual loss (AAL) is $1.94M, while severe-loss outcomes are larger in absolute terms: VaR99 is $50.17M and TVaR99 is $128.23M. This means expected annual loss is smaller than the losses represented in the tail of the distribution. The modelled probability of at least one material event during the year, P(Material Event), is 5.05%.

**Deterministic verification:** VERIFIED.

**Supporting governed facts:** Prudent AAL is $1.94M; VaR99 is $50.17M; TVaR99 is $128.23M; P(Material Event) is 5.05%. The governed comparisons confirm that VaR99 is greater than AAL and TVaR99 is greater than VaR99.

**Caveat/refusal reason:** None.

### 7. OT — Scenarios

**User question:** Why is this scenario material?

**Exact user-facing response:**

> Destructive or Integrity Attack is the leading scenario in the returned ordering. It contributes $12.26M to TVaR95 and $55.21M to TVaR99, while its selected AAL contribution is $613.05K. Both tail-loss contributions are greater than its selected AAL contribution.

**Deterministic verification:** VERIFIED.

**Supporting governed facts:** Destructive or Integrity Attack is first in the returned scenario ordering. Its selected AAL contribution is $613.05K; its TVaR95 contribution is $12.26M; its TVaR99 contribution is $55.21M. Governed comparisons confirm that both tail contributions are greater than its selected AAL contribution.

**Caveat/refusal reason:** No route, impact-component, or implementation-priority inference is made.

### 8. OT — Attack Paths

**User question:** What is preventing this path from closing?

**Exact user-facing response:**

> The current result does not contain a governed path-state value for this path, so I cannot determine whether it is OPEN or CLOSED. I can still explain its returned probability facts, but this result provides no architecture-gate, barrier or control-state facts that explain a path state.

**Deterministic verification:** VERIFIED.

**Supporting governed facts:** The approved OT route/path records contain actor, scenario, event-frequency, success-probability, annual-event-probability, and AAL fields. They contain neither a route identifier nor a path-state field. The approved barrier, feasibility, applicability, relevant-TTP, and stage-progression collections are empty.

**Caveat/refusal reason:** No path state has been inferred. The canonical result does not contain the facts required to explain an OPEN, CLOSED, CONDITIONAL, or UNKNOWN state.

### 9. OT — Business Impact

**User question:** What drives the business impact?

**Exact user-facing response:**

> Business Interruption costs is the largest modelled loss category, contributing $924.04K to AAL. Within the underlying loss drivers, OT and digital forensic investigation is the largest individual contributor within Incident response costs.

**Deterministic verification:** VERIFIED.

**Supporting governed facts:** Business Interruption costs is first in the returned AAL loss-category ordering at $924.04K. OT and digital forensic investigation is first in the returned individual loss-driver ordering and is classified under Incident response costs.

**Caveat/refusal reason:** None. This previously accepted response is retained as a regression control.

### 10. OT — Evidence

**User question:** Which evidence gaps matter most?

**Exact user-facing response:**

> The current result does not contain an explicit governed evidence-quality ranking, so I cannot identify a weakest evidence area.

**Deterministic verification:** VERIFIED.

**Supporting governed facts:** Evidence records are present, but the current result contains no governed evidence-quality ranking.

**Caveat/refusal reason:** The Evidence view can still show returned records without assigning an unsupported priority. This previously accepted response is retained as a regression control.

## Correction evidence

- Governed evaluation: 14 of 14 cases VERIFIED; 0 REJECTED.
- Live Bedrock coverage: two additional free-form IT/OT cases invoked Amazon Nova Pro and passed the deterministic verifier.
- Adversarial verifier coverage rejects unsupported approximations, qualitative magnitude labels, ambiguous reductions, non-canonical metric labels, uncited entities, invented rankings, unsupported numbers, and invented path states.
- Full Python suite: 295 passed; 1 expected skip.
- Frontend suite: 27 passed across 7 files.
- TypeScript, frontend lint, production build, Ruff, Bandit, JSON validation, and whitespace checks passed.
- No quantitative baseline, methodology, sector pack, quantitative engine, API architecture, Cognito configuration, or AWS runtime was changed.

## Product-owner decision

- ☐ Accept the six corrected responses and Phase 6A response quality for the controlled dev pilot.
- ☐ Reject and record the exact cases and wording requiring further correction.

Reviewer:

Date:

Notes:
