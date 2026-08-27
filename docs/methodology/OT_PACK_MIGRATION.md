# Embedded OT pack → external pack migration

Extraction: `python -m crq rebuild-workbook` (`ot_crq.packs.extract_ot_packs`).

Values were copied, not recalibrated. Combined sheets 28–33 are **ENGINE-LOADED audit views** and are not used by the OT engine.

| Assumption | Old location | New pack location | Owner | Value changed? |
| --- | --- | --- | --- | --- |
| Pack identity PG/EA/MF | 28 Sector Pack Registry A16:H18 | 01 Pack Metadata + registry JSON | Pack owner | No |
| Asset archetypes | 28 A25:G39 | 05 Actor Route (A1 titled Asset Archetypes; FS tab name kept) | Pack owner | No |
| Asset-type frequency overlays | 28 A45:I59 | 02 Actor Weights rows 24+ | Pack owner | No |
| Sector actor multipliers | 06 Frequency Assumptions A73:G75 | 02 Actor Weights Weight column | Pack owner | No |
| TTP rationale / applicability / gates | 29 Sector TTP Rationale | 12 TTP Catalogue | Pack owner | No |
| Sector BIA scenario downtime/capacity | Combined OT 05 A58:G62 | 09 Scenario Parameters (row-oriented; engine-loaded) | Pack owner | No (values preserved; layout transposed; IT columns removed) |
| Sector BIA / driver tables | Combined OT 05 | 10 Driver Rates, 11 Impact Driver Matrix | Pack owner | No (values copied; reference until a later pack-load change) |
| Reference λ 0.55 | 06 A16 | Remains OT 06 / core method | Core OT | No |
| Actor shares / S1–S5 | 06 A27:J29 | Remains OT 06 (core calibration on assessment sheet) | Core OT | No |
| Facility exposure map | 06 A53:F66 | Remains OT 06 | Core OT | No |
| Geography overlays | 06 A82:E85 | Remains OT 06 assessment | Assessment | No |
| Prudence / seed / N | 06 A17:A20 | OT 06 assessment | Assessment | No |

Duplicates resolved: sector multipliers no longer authoritative on the combined 06 sheet for engine load. Combined 28/29 are not read by `ot_crq.engine._load_sector_pack`.

Registry: `config/sector_pack_registry.json`.

Pack schema OT: `CRQ-OT-PACK-1.0`. IT: `CRQ-PACK-1.1`.

Regression: fast suite (`pytest -m "not production"`) passed after extraction. Re-run `python -m crq validate-release --production` to confirm 500k goldens (campaign frequency, AAL, VaR, TVaR, P(any), actor/scenario AAL) with identical seeds.
