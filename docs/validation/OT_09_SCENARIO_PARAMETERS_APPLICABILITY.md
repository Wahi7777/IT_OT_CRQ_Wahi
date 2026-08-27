# OT pack `09 Scenario Parameters` — applicability review

Date: 26 August 2026  
Scope: All OT sector packs (Power Generation PG-v1.6, Energy Assets EA-v1.0, Manufacturing MF-v1.0).  
**IT / Financial Services pack was not modified.**

## Context (discovered)

| Item | Finding |
| --- | --- |
| OT packs | `sector_packs/OT/OT_CRQ_Sector_Pack_{Power_Generation_v1_6,Energy_Assets_v1_0,Manufacturing_v1_0}.xlsx` |
| Scenarios (all OT packs) | Operational Disruption; Loss of Control or Visibility; Process Manipulation; Safety System Compromise; Destructive or Integrity Attack |
| Pre-change sheet 09 | Columns A–H: OT downtime/capacity (authoritative content). Columns I–AL: **IT enterprise parameter headers** (`RESTORE_DAYS_*`, `AFFECTED_RECORD_SHARE_*`, fraud/payment/churn, etc.) pasted from the FS pack format; **not read by `ot_crq.engine`** |
| OT engine loss path | Assessment `OT 05 - Impact & BIA` A58:G62 (downtime/capacity) + driver matrix A28:L53 + rates A67:L84. Pack sheet 09 was documentation-only before this change |
| IT engine | Reads IT pack `09 Scenario Parameters` as a wide table keyed by `*_P50` / `*_P99`. Untouched |

OT consequence math uses scenario **downtime days** and **capacity affected** for BI and for `DAILY_X_SCENARIO_DAYS` drivers. Restoration effort, extortion, endpoint/server replacement, regulatory fines and post-event uplift are **driver rates / matrix toggles** on OT 05 (and pack sheets 10–11), not IT-style scenario parameter columns.

## Decision table (applies to PG, EA, and MF unless noted)

Each sector was reviewed against the same five OT scenarios and the same OT BIA driver set. Scenario downtime/capacity values were identical across the three packs before this change.

| Parameter | Scenarios | Loss component | Decision | Rationale | Dependency | Evidence / source | Replacement |
| --- | --- | --- | --- | --- | --- | --- | --- |
| DOWNTIME_DAYS (P50/P99) | All five | BI-01; OP-01; OP-02 | **KEEP** | Period of lost/reduced operation | Pack 09 → engine `scenario_impact` | OT 05 A58:G62 / SRC-OT-01 | — |
| CAPACITY_AFFECTED (P50/P99) | All five | BI-01 (scales revenue×days) | **KEEP** (OT name; not IT `AFFECTED_SERVICE_SHARE`) | Share of capacity/output affected | Pack 09 → engine | OT 05 capacity columns / SRC-OT-01 | Replaces informal “P50 capacity affected” labels |
| Evidence grade / Source ID | All kept rows | Metadata | **KEEP** | Traceability | Pack 09 columns | Pack convention grade D / SRC-OT-01 | — |
| RESTORE_DAYS_* | — | — | **REMOVE** from 09 | Restoration days live on driver quantities RC-01/02/03 (`DAILY_X_DAYS`), not scenario params | Pack 10 / OT 05 rates | SRC-OT-01 | Sheet 10 Driver Rates |
| AFFECTED_SERVICE_SHARE_* | — | — | **REMOVE** (IT name) | OT uses `CAPACITY_AFFECTED` | — | — | `CAPACITY_AFFECTED` |
| AFFECTED_RECORD_SHARE_* | — | Notification / monitoring (IT) | **REMOVE** | No OT record-breach pathway | None in `ot_crq` | — | — |
| AFFECTED_ENDPOINT_SHARE_* | — | — | **REMOVE** from 09 | OT endpoint/controller share is PD-01 qty on rates | Pack 10 / OT 05 PD-01 | SRC-OT-01 | Sheet 10 `PD-01` |
| AFFECTED_SERVER_SHARE_* | — | — | **REMOVE** from 09 | OT server/engineering share is PD-02 qty | Pack 10 / OT 05 PD-02 | SRC-OT-01 | Sheet 10 `PD-02` |
| REGULATORY_REVENUE_SHARE_* | — | — | **REMOVE** from 09 | LG-02 uses `REVENUE_X_SHARE` qty on rates | Pack 10 / OT 05 LG-02 | SRC-OT-01 | Sheet 10 `LG-02` |
| PAYMENT_FLOW_DAYS_* | — | IT fraud | **REMOVE** | No OT payment-flow pathway | None | — | — |
| DIVERTED_SHARE_* | — | IT fraud | **REMOVE** | No OT diverted-payment pathway | None | — | — |
| FRAUD_RECOVERY_RATE_* | — | IT fraud | **REMOVE** | No OT fraud pathway | None | — | — |
| MONITORING_TAKEUP_* | — | IT credit monitoring | **REMOVE** | No OT monitoring pathway | None | — | — |
| EXTORTION_DIRECT_* | Cybercriminal; Operational Disruption & Destructive (matrix) | EX-01 | **REMOVE** from 09 | Extortion is EX-01 `DIRECT` USD on rates; actor gate Cybercriminal; scenario toggles on matrix | Pack 10–11 / OT 05 EX-01 | SRC-OT-01 | Sheet 10 `EX-01` + sheet 11 |
| POST_EVENT_REVENUE_SHARE_* | — | — | **REMOVE** from 09 | IN-01 post-event uplift is `REVENUE_X_SHARE` on rates | Pack 10 / OT 05 IN-01 | SRC-OT-01 | Sheet 10 `IN-01` |
| CHURN_REVENUE_SHARE_* | — | IT attrition | **REMOVE** | No OT customer-churn pathway | None | — | — |

No sector-specific divergence: EA and MF use the same OT BIA schema and the same five scenarios; none of the removed IT parameters had an active OT loss pathway in code.

## Target sheet shape (row-oriented)

| Scenario ID | Scenario | Parameter ID | P50 | P99 | Unit | Applies? | Evidence grade | Source ID | Description / rationale |

Two active parameter IDs per scenario (`DOWNTIME_DAYS`, `CAPACITY_AFFECTED`). `Applies?` = Yes for all five scenarios. Inactive IT columns are deleted, not zeroed.

## Engine integration after this change

- `load_ot_pack` requires sheet `09 Scenario Parameters` and returns `scenario_impact`.
- `ot_crq.engine` uses pack `scenario_impact` (fail-closed); no longer authoritative on OT 05 A58:G62 for those four numbers.
- Facility financial panel on OT 05 (revenue, BI factor, driver rates/matrix) remains assessment/core as before.
- IT pack and `it_crq` loaders unchanged.
