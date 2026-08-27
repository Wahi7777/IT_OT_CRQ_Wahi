# Unified Balbix impact architecture — pre-refactor gap analysis

**Status:** Gap analysis complete; implementation delivered; **acceptance validation = Outcome B** (do not re-freeze yet). See `BALBIX_UNIFIED_IMPACT_ACCEPTANCE.md`.  
**Balbix source:** `/Users/sidharthwahi/Documents/Cyber Ins - UAE/Balbix Breach Impact Model.xlsx`  
**Date:** 2026-08-26

## 1. Root cause of implausible “Incident response” (69% of TVaR 99)

### What the FS pack actually calculates

`src/it_crq/engine.py` `_severity()` already computes **14 Balbix-style driver amounts** (forensics, fraud, BI, notification, etc.) using pack rates × scenario parameters × facility exposures.

### What goes wrong

1. Drivers are **summed into three loss blocks** (`Duration` / `Exposure` / `Direct`) before fitting severity.
2. Monte Carlo draws **one lognormal per block**, not per driver — driver identity is destroyed in the trial arrays.
3. Reporting maps blocks with `IT_BLOCK_TO_COMPONENT`:

| Block | Reported label | Drivers actually placed in that block by FS pack sheet 11 |
| --- | --- | --- |
| Duration | **Business interruption** | IR_FORENSICS, EXTERNAL_RESPONSE, LEGAL_RESPONSE, RESTORATION, BUSINESS_INTERRUPTION, ENDPOINT_RECOVERY, SERVER_RECOVERY |
| Exposure | Data/privacy costs | NOTIFICATION, CREDIT_MONITORING, REGULATORY, CUSTOMER_ATTRITION |
| Direct | **Incident response** | **FRAUD_NET_RECOVERY, EXTORTION, POST_EVENT_UPLIFT** |

So **monetary theft / fraud** is reported as **Incident response**. True incident-response costs sit inside Duration and are reported as **Business interruption**.

### Why RAKBANK’s Direct block dominates the tail

RAKBANK facility inputs include `ANNUAL_PAYMENT_VALUE = $76,500,000,000`.  
`FRAUD_NET_RECOVERY = payment/365 × PAYMENT_FLOW_DAYS × DIVERTED_SHARE × (1 − FRAUD_RECOVERY_RATE)` produces very large Direct-block severity. That mass is labelled Incident response → ~69% of TVaR 99.

**This is a grouping/labelling and aggregation defect, not evidence that forensic IR costs are $96m.**

## 2. Root cause of the earlier “$45m scenario TVaR 99 gap”

Already closed in a prior pass: portfolio scenario TVaR 99 contributions **did reconcile**. Cyber-enabled theft contribution is **$94.2m**, not $49.2m. No methodology change required for that item.

## 3. Balbix driver catalogue (authoritative)

From Balbix **Model Control Panel** (Cost Category / Cost driver / Cost Types / scenario flags / equation):

| # | Balbix cost driver | Balbix major category | Cost Types (secondary — do not use for roll-up) | Formula (Balbix) |
| --- | --- | --- | --- | --- |
| 1 | Notification costs | Incident & response costs | Notification | customers × % affected × cost/customer |
| 2 | Credit monitoring costs | Incident & response costs | Post Breach response | customers × % affected × monitoring cost |
| 3 | Card replacement costs | Incident & response costs | Post Breach response | customers × % affected × card cost |
| 4 | Forensic investigation costs | Incident & response costs | Detection & Escalation | daily forensic × days |
| 5 | Public relations cost | Incident & response costs | Post Breach response | daily PR × days |
| 6 | Average employee training costs | Incident & response costs | Post Breach response | awareness cost × employees |
| 7 | External cyber experts cost | Incident & response costs | Notification | daily external cyber × days |
| 8 | Ransom payment costs | Data Recovery & Restoration costs | Post Breach response | user input |
| 9 | Data restoration costs | Data Recovery & Restoration costs | Post Breach response | daily restoration × days |
| 10 | Business downtime costs | Business Interruption costs | Lost Business | (revenue × margin / working days) × downtime days |
| 11 | Monetary Theft | Direct Loss of Funds costs | Post Breach response | user input |
| 12 | PCI/PHI/PII/GDPR/Other regulatory fine | Fines | Post Breach response | revenue × % fine |
| 13 | Legal guidance & defence costs | Legal and Defence costs | Post Breach response | daily legal × days |
| 14 | PCI/PHI/PII Consumer Settlement | Legal and Defence costs | Post Breach response | records × cost/record × % affected |
| 15 | Fraud reimbursement costs (customer) | Financial Fraud | Post Breach response | user input |
| 16 | Endpoint replacement costs | Physical Damage Costs | Post Breach response | endpoints × unit cost × affected |
| 17 | Server replacement costs | Physical Damage Costs | Post Breach response | servers × unit cost × affected |
| 18 | Cyber security investment costs | Indirect Losses | Post Breach response | user input |
| 19 | Customer churn costs | Indirect Losses | Lost Business | margin per customer × churned customers |

**Critical Balbix rule:** *Cost Types* (e.g. “Post Breach response”) is **not** the economic category. Monetary Theft’s secondary type is Post Breach response; its category is **Direct Loss of Funds**.

## 4. Crosswalk — Balbix → current FS pack / engine

| Balbix driver | Balbix category | Current ID | Current block | Current formula | Implemented correctly? | Gap/action |
| --- | --- | --- | --- | --- | --- | --- |
| Notification | Incident & response | NOTIFICATION | Exposure→Data/privacy | records×share×rate | Formula OK; **wrong category** | Remap category; keep driver trials |
| Credit monitoring | Incident & response | CREDIT_MONITORING | Exposure→Data/privacy | records×share×takeup×rate | Formula OK; wrong category | Remap |
| Card replacement | Incident & response | — | — | — | **Missing** | Catalogue only until pack enables |
| Forensic investigation | Incident & response | IR_FORENSICS | Duration→BI | days×rate | Formula OK; **wrong category** | Remap; driver-level trials |
| Public relations | Incident & response | — | — | — | **Missing** | Catalogue only until pack enables |
| Employee training | Incident & response | — | — | — | **Missing** | Catalogue only until pack enables |
| External cyber experts | Incident & response | EXTERNAL_RESPONSE | Duration→BI | days×rate | Formula OK; wrong category | Remap |
| Ransom payment | Recovery & restoration | EXTORTION | Direct→IR | direct amount | Formula OK; wrong category | Remap to Recovery |
| Data restoration | Recovery & restoration | RESTORATION | Duration→BI | days×rate | Formula OK; wrong category | Remap |
| Business downtime | Business interruption | BUSINESS_INTERRUPTION | Duration→BI | revenue/365×days×share×BI | Approx (margin not separate) | Keep; category=BI |
| Monetary Theft / fraud net | Direct Loss of Funds / Financial Fraud | FRAUD_NET_RECOVERY | Direct→IR | payment flow formula | **Mislabelled as IR** | Remap to Direct financial theft/fraud |
| Regulatory fines | Fines | REGULATORY | Exposure→Data/privacy | revenue×share | Simplified single fine | Remap to Fines |
| Legal defence | Legal and Defence | LEGAL_RESPONSE | Duration→BI | days×rate | Formula OK; wrong category | Remap |
| Consumer settlements | Legal and Defence | — | — | — | **Missing** | Catalogue only until pack enables |
| Fraud reimbursement | Financial Fraud | (inside FRAUD_NET) | Direct→IR | net of recovery | Combined with theft | Report under fraud/funds |
| Endpoint replacement | Physical Damage | ENDPOINT_RECOVERY | Duration→BI | count×share×rate | Formula OK; wrong category | Remap |
| Server replacement | Physical Damage | SERVER_RECOVERY | Duration→BI | count×share×rate | Formula OK; wrong category | Remap |
| Cyber security investment | Indirect | POST_EVENT_UPLIFT | Direct→IR | revenue×share | Formula OK; wrong category | Remap |
| Customer churn | Indirect | CUSTOMER_ATTRITION | Exposure→Data/privacy | revenue×share | Simplified | Remap |

## 5. OT comparison (duplication & Balbix gaps)

OT already has an **18-driver BIA matrix** with formula types (`DAILY_X_DAYS`, `BI_SCENARIO`, …) but:

- Separate engine path from IT (`ot_crq.engine` vs `it_crq.engine`).
- Reporting collapses non-BI into proportional category weights — **not** driver-level trial losses.
- Several OT drivers are **not in Balbix** (flag as gaps; do not invent Balbix IDs):

| OT driver | In Balbix? | Action |
| --- | --- | --- |
| IR-01/02 forensics / external cyber | Yes (analogues) | Map to Balbix IDs in unified catalogue |
| IR-03 crisis communications | Yes (PR) | Map to Public relations |
| RC-01/02/03 restoration / OEM / config | Partial (data restoration only) | OEM/engineering = **gap** |
| BI-01 / OP-01 | Yes / related | Map carefully |
| OP-02 alternative supply / penalties | **No** | **Gap** |
| EX-01 extortion | Yes (ransom) | Map |
| LG-01/02 legal / fines | Yes | Map |
| SF-01 safety response | **No** | **Gap** |
| EN-01 environmental | **No** | **Gap** |
| PD-01/02 endpoint/server | Yes | Map |
| PD-03 major equipment | **No** | **Gap** |
| IN-01 post-event uplift | Yes | Map |

## 6. Proposed unified architecture

### Core owns (`src/crq/impact/`)

- Balbix-only driver catalogue (stable IDs, Balbix names, major categories, formula types).
- Formula library.
- Event generation: per-driver lognormals with shared correlation.
- Driver → category → scenario → portfolio aggregation.
- Tail contributions on the **same portfolio-tail mask**.
- Reconciliation helpers.

### Sector packs own

- Enabled drivers + scenario applicability + P50/P99 + evidence (sheets 09–11).
- No driver activates merely by existing in the catalogue.

### Facility owns

- Revenue, payment value, records, customers, endpoints, servers, BI factor, etc.

### Reporting hierarchy

1. Individual Balbix driver (AAL / TVaR contrib).  
2. Balbix major category (sum of drivers only).  
3. Scenario / actor / portfolio.

## 7. Implementation sequence

1. Add `src/crq/impact/` catalogue + category map (Balbix names).
2. Change IT simulation to retain **per-driver** annual trials; stop three-block reporting labels.
3. Update Business Impact + Executive headlines for driver and category.
4. Add reconciliation tests.
5. Preserve OT likelihood/path/control engines; document OT Balbix gaps.
6. Rerun RAKBANK; **do not re-freeze goldens** until review/acceptance.

## 8. Non-goals this pass

- Inventing OT-only drivers as Balbix IDs.
- Changing campaign frequency, routes, or control maturity maths.
- Forcing revised AAL/VaR/TVaR to match prior RAKBANK totals.
