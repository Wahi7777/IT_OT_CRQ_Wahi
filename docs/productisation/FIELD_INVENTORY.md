# Workbook, pack and configuration field inventory

The authoritative machine-readable inventory is `contracts/mappings/field-inventory.json`. Its expansion rule creates one canonical field for each listed item/parameter key. Every entry has exactly one ownership classification and records its source, location, datatype, allowed values, required/default behavior, validation, Python consumer, affected result family, frontend visibility and inert status.

## Common assessment fields

Run Setup `C6:C11` maps to domain, sector, asset type, reporting basis and outside-in state. Appetite maps from sheet 06 `B6:B10`, with legacy Run Setup values recorded as lower-precedence duplicates. Insurance maps from `B13:B15` and `A18:D21`.

## IT assessment fields

- IT 03 `C16:C31`: identity, financial scale, exposure-model selection and runtime.
- IT 04 `C16:V21`: six routes, applicability/feasibility, opportunity, S1–S5 and impact factors, plus evidence metadata.
- IT 05 `E16:I30`: fifteen control maturity/coverage assessments and evidence.
- IT 06: eight rate P50/P99 overrides and four scenarios by seventeen parameter P50/P99 overrides.
- IT 07: organisation, geography, prudence and four actor-activity multipliers.
- IT 08: reporting view, TVaR display selection and legacy insurance fallback.

`EMPLOYEES` and `CUSTOMERS` remain inactive. Evidence/rationale does not alter the quantitative result. Pack reference maturity, routes, actor/scenario matrices, stage priors, driver priors and mappings remain model-owned.

## OT assessment fields

- OT 03 `C16:C29`: identity, sector/asset and seven facility topology responses.
- OT 04 `D16:H67`: 52 controls. Only maturity and coverage affect mathematics; tested/result/evidence are evidence-only.
- OT 05 `C16:C20`: financial exposure. Employees remain inactive.
- OT 05 `D29:J53` and `C67:H84`: 18-driver applicability, rates, quantities and formula/scaling metadata. These are currently workbook-sourced but classified as governed model inputs.
- OT 06: simulation/seed, reference frequency, prudence, actor configuration, scenario difficulty, exposure mapping and geography multipliers.

Only client-specific geography adjustment is treated as a permitted override. Core actor configuration, reference campaigns, scenario difficulty and exposure mappings are governed assumptions even where the workbook currently labels or styles them as editable.

## Sector packs and core configuration

The IT engine actively loads pack sheets 01–15. Sheets 16–18 carry evidence and validation metadata. The OT engine actively loads metadata, actor/asset multipliers, actor-scenario propensity, scenario impact parameters and TTP applicability. OT pack sheets retained as IT-format placeholders or reference copies are classified `DISPLAY_ONLY`; the active OT core mappings remain governed inputs to the future ModelBundle.

The pack registry and router configuration map to bundle identity/applicability, not to client assessment fields.

## Excel adapter requirement

The later adapter must implement both directions without invoking calculations:

```text
Excel workbook + selected immutable ModelBundle → validated CRQAssessment
CRQResult + compatible workbook template → Excel export
```

Workbook coordinates are adapter metadata. They are not part of either calculation contract.

