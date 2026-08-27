# Unified Balbix IT/OT impact-driver framework

The Balbix Breach Impact Model cost-driver structure is adapted into one
version-controlled catalogue and simulation core used for IT and OT assessments.

See also: `docs/validation/BALBIX_UNIFIED_IMPACT_GAP_ANALYSIS.md`.

## Separation of responsibilities

| Layer | Owns |
| --- | --- |
| **Core** (`src/crq/impact/`) | Driver schema, formula types, P50/P99 lognormal fitting, event loss generation, correlation, driver→category→scenario→portfolio aggregation, AAL/VaR/TVaR, tail contributions, reconciliation, generic reporting structures |
| **Sector pack** | Which drivers are enabled, scenario applicability, P50/P99 and unit rates, evidence / rationale, sector input requirements, calibrated vs prior vs user-supplied, scenario overrides |
| **Facility / organisation workbook** | Exposure inputs required by enabled drivers (revenue, payment value, records, endpoints, production value, etc.) |

There is **one** impact engine path for IT severity. OT retains its facility BIA
calculation for currently governed drivers; Balbix analogues map into the same
category taxonomy for reporting. OT-only consequences without a Balbix driver ID
are **flagged as gaps** — they are not invented as new catalogue entries.

## Catalogue rules

* Domain relevance (IT / OT / both) is informational only.
* A driver enters simulation only when the sector pack enables it **and** the
  actor×scenario applicability matrix selects it.
* Inapplicable drivers are omitted from Business Impact tables (not shown as zeros).
* Reporting uses **Balbix major cost categories**, never Balbix “Cost Types”
  (e.g. Monetary Theft must not appear as Incident response).
* Loss blocks `Duration` / `Exposure` / `Direct` remain **control-channel**
  factors only (REDUCE_DURATION / EXPOSURE / CONSEQUENCE). They are not
  economic categories.

## Hierarchy

1. Individual impact driver  
2. Balbix major category (sum of drivers)  
3. Scenario  
4. Actor (where attribution is meaningful)  
5. Annual portfolio loss  

Every simulated IT event retains domain, sector pack, scenario, actor, driver ID,
category, driver loss and total event loss through annual aggregation and
portfolio-tail allocation (same tail mask for all contribution views).

## Reconciliation

For each assessment:

* Applicable drivers sum to event / annual portfolio loss  
* Driver and category AAL each sum to portfolio AAL  
* Driver and category TVaR contributions each reconcile to aggregate TVaR  

## Dependency (Monte Carlo)

IT successful events use **channel-comonotonic Gaussian** dependence: one latent per Duration/Exposure/Direct channel; drivers in a channel share that latent; channels are equicorrelated at pack `LOSS_BLOCK_RHO`. See `src/crq/impact/dependency.py` and `docs/validation/BALBIX_UNIFIED_IMPACT_ACCEPTANCE.md`.

## Formula library

Reusable types in `src/crq/impact/formulas.py` (examples):
`daily_rate_x_duration`, `revenue_per_day_x_duration_x_share_x_margin`,
`records_x_share_x_unit`, `payment_value_x_compromised_x_unrecovered`,
`asset_count_x_share_x_unit`, `direct_amount`. Sector packs select a type and
supply calibration; they do not add engine branches unless economics cannot be
expressed by the library.
