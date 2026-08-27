# Combined workbook sheet-name mapping

Old combined-workbook names → new names. Engine-critical OT native names remain in `model/ot/` with legacy aliases in `ot_crq.engine.LEGACY_SHEETS`.

See `src/crq/sheet_names.py` (`OLD_TO_NEW`) as the code source of truth.

| Old | New |
| --- | --- |
| 00 Run Setup | 00 COMMON - Run Setup |
| 00 Outside-In | 00 COMMON - Outside-In |
| 00 Output Bridge | 00 COMMON - Output Bridge |
| 00 OI Adjustment Rationale | 00 COMMON - OI Audit Trail |
| 03 Facility Inputs | OT 03 - Facility Inputs |
| 04 Control Assessment | OT 04 - Control Assessment |
| 05 Impact and BIA | OT 05 - Impact & BIA |
| 06 Frequency Assumptions | OT 06 - Assessment Adjustments |
| 07 Control Assumptions | OT CORE - Control Method |
| 08 Scenario Definitions | OT CORE - Scenario Definitions |
| 09 Scenario-TTP Map | OT CORE - Scenario-TTP Map |
| 11 Actor-TTP Applicability | OT CORE - Actor-TTP Map |
| 12 Facility Feasibility | OT CORE - Facility Feasibility |
| 13 TTP-Control Map | OT CORE - TTP-Control Map |
| 28–33 pack sheets | OT PACK * Loaded * (audit, not authoritative) |
| IT 03 Organisation Inputs | IT 03 - Organisation Inputs |
| IT 04 Exposure Adjustments | IT 04 - Exposure Adjustments |
| IT 05 Control Assessment | IT 05 - Control Assessment |
| IT 06 Impact and BIA | IT 06 - Impact & BIA Overrides |
| IT 07 Frequency Assumptions | IT 07 - Assessment Adjustments |
| IT 08 Tail Risk Settings | IT 08 - Reporting Settings |
| 2 User Inputs | 2 User-input navigation |
| 3 Key Assumptions | 3 Assumption Ownership |
| 5 Other | 5 Advanced - Governed |

Excel forbids `/` in sheet titles and limits titles to 31 characters, so a few spec names were shortened (for example `OT CALC - Threat Frequency`).
