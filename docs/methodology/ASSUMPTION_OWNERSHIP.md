# Assumption ownership matrix

Layers: Assessment input → selected sector pack → permitted core default. Missing mandatory pack values fail closed.

| Group | Domain | Sector | Layer | Location | Owner | Editable in assessment? | Authoritative |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Common setup | Common | All | Assessment | 00 COMMON - Run Setup | Assessment Team | Yes | Workbook C6 domain, C7 sector, C8 asset |
| Common setup | Common | All | Optional evidence | 00 COMMON - Outside-In | Assessment Team | Optional | Approved CSV |
| IT assessment | IT | FS | Required | IT 03, IT 05, IT 08 | Assessment Team | Yes | Combined IT input sheets |
| IT assessment | IT | FS | Optional override | IT 04, IT 06, IT 07 | Assessment Team | Optional | Blank keeps pack |
| Core IT | IT | All IT | Methodology | src/it_crq + IT CORE/CALC | Core IT Model Owner | No | Python |
| FS pack | IT | Financial Services | Calibration | sector_packs/IT/IT_CRQ_Sector_Pack_Financial_Services_v1_1_1.xlsx | Sector Pack Owner | No | External pack FS-v1.1.1 |
| OT assessment | OT | Selected | Required | OT 03, OT 04, OT 05, OT 06 | Assessment Team | Yes | Combined OT input sheets |
| Core OT | OT | All OT | Methodology | src/ot_crq + OT CORE | Core OT Model Owner | No | Python (λ method, stages, floors) |
| PG pack | OT | Power Generation | Calibration | sector_packs/OT/OT_CRQ_Sector_Pack_Power_Generation_v1_6.xlsx | Sector Pack Owner | No | External pack PG-v1.6 |
| EA pack | OT | Energy Assets | Calibration | sector_packs/OT/OT_CRQ_Sector_Pack_Energy_Assets_v1_0.xlsx | Sector Pack Owner | No | External pack EA-v1.0 |
| MF pack | OT | Manufacturing | Calibration | sector_packs/OT/OT_CRQ_Sector_Pack_Manufacturing_v1_0.xlsx | Sector Pack Owner | No | External pack MF-v1.0 |
| Outputs | Common | All | Calculated | Dashboards / Engine Results | Python | No | 00 COMMON - Engine Results |

Unambiguous owner could not be assigned for: OT actor campaign shares on OT 06 (rows 27–29). They remain on the assessment-facing frequency sheet because the engine still reads that range as core+assessment together; they are labelled not-for-pack-edit. Actor-to-scenario propensity is owned by each OT pack sheet `03 Actor Scenario`. Sector actor multipliers live on `02 Actor Weights`. Scenario downtime days and capacity affected are owned by each OT pack sheet `09 Scenario Parameters` (row-oriented `DOWNTIME_DAYS` / `CAPACITY_AFFECTED`). OT 05 still holds facility financial panel, driver rates and the impact-driver matrix.
