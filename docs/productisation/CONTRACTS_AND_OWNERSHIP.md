# Productisation contracts and ownership

## Contract set

- `CRQAssessment`: `contracts/schemas/crq-assessment.schema.json`
- `ModelBundle`: `contracts/schemas/model-bundle.schema.json`
- `CRQResult`: `contracts/schemas/crq-result.schema.json`
- `NarrativeFactBundle`: `contracts/schemas/narrative-fact-bundle.schema.json`
- Machine-readable input mapping: `contracts/mappings/field-inventory.json`
- Machine-readable result mapping: `contracts/mappings/engine-output-to-crq-result.json`

These are draft V1 contracts. The existing engines do not consume or produce them in this phase.

## Definitive ownership matrix

| Information | Owner/classification | Frontend treatment | Current source |
|---|---|---|---|
| Organisation, facility, country/region, sector and scope | `USER_INPUT` | Editable subject to routing constraints | Run Setup; IT 03; OT 03 |
| Financial exposure and BIA quantities | `USER_INPUT` | Editable | IT 03; OT 05 |
| Architecture/topology responses | `USER_INPUT` | Editable; preserve Unknown separately from No/Closed | OT 03 and IT route applicability |
| Assessed control maturity and coverage | `USER_INPUT` | Editable | IT 05; OT 04 |
| Control test/evidence/rationale | `EVIDENCE_ONLY` | Editable evidence; never described as a quantitative control input | IT 05 and OT 04 |
| Client-specific rate/scenario/frequency adjustments | `PERMITTED_OVERRIDE` | Permissioned, attributed and evidence-backed | IT 06/07; OT prudence factor |
| Appetite and insurance programme | `USER_INPUT` | Editable policy/financing inputs | Sheet 06, with legacy fallbacks documented |
| Outside-in scan observations | `EVIDENCE_ONLY` | Read-only imported evidence | OI CSV |
| Approved OI quantitative adjustment | `PERMITTED_OVERRIDE` | Separate approval control and audit history | OI router overlay |
| Actor/scenario configuration | `GOVERNED_PACK_INPUT` | Read-only summary or hidden | IT pack; OT pack and OT core |
| Route/TTP and control mappings | `GOVERNED_PACK_INPUT` | Read-only methodology detail | Packs and OT core mappings |
| Stage priors, path caps/floors and dependency | `GOVERNED_PACK_INPUT` | Hidden from normal users; visible to model governors | IT pack; OT core |
| Frequency and severity priors | `GOVERNED_PACK_INPUT` | Read-only summary; never ordinary assessment input | Sector packs and OT core |
| Sector/asset multipliers | `GOVERNED_PACK_INPUT` | Read-only resolved bundle metadata | OT pack |
| Geography-to-actor multiplier table | `GOVERNED_PACK_INPUT` | Read-only; the client selects geography, not the multiplier | OT 06 core table |
| Pack sources, grades and limitations | `EVIDENCE_ONLY` | Visible methodology evidence | Pack sheets 16–18 and limitations register |
| Resolved engine/pack/version/status | `DERIVED` | Visible and read-only | Router/engine outputs |
| Instructions, dashboards and duplicate calculation displays | `DISPLAY_ONLY` | Recreated as product presentation if useful | Workbook display sheets |
| IT employees/customers and OT employees | `INACTIVE_LEGACY` | Read-only migration context or hidden; must not become active | IT 03 / OT 05 |

## Known source conflicts

- Appetite values may appear on Run Setup and sheet 06; a nonblank sheet-06 value currently wins.
- Insurance retention may exist in IT reporting, sheet 06 and the OT legacy tail area. The common programme wins for full insurance, while OT legacy-tail behavior remains separately wired.
- OT driver mappings/rates in sector-pack sheets 10/11 are reference copies. Runtime currently uses OT 05/core workbook values. These are model-owned even though they appear in the assessment workbook.
- OT scenario parameters displayed in OT 05 rows 58–62 are populated from the pack and are display-only.
- IT LEC return-period settings displayed in Excel are not the current engine source; code owns the active set.
- The OI v0.2 CSV header and OI 1.0 router claims do not yet form one enforceable schema.

## ModelBundle boundary

A published ModelBundle is immutable. It must materialize every actor, scenario, route/TTP, control mapping, severity prior, frequency prior, dependency, cap/floor, governed mapping, status and limitation needed by one domain run. References to workbook ranges are acceptable only during migration; the final published bundle must contain normalized values.

The bundle hash is calculated over canonical JSON excluding the `bundle_hash` field. A calculation worker receives a complete assessment, one complete bundle, and run configuration. It cannot resolve mutable defaults from a workbook or database during calculation.

Required reproducibility identity:

```text
assessment hash + model-bundle hash + seed + run configuration + engine artifact digest
    = reproducible CRQResult
```

## CRQResult boundary

The result schema normalizes best/prudent metrics, formation, decomposition, AEP/OEP, impacts, architecture, treatments, sensitivity, uncertainty, insurance and limitations. Domain-specific structures remain under explicit IT/OT fields. Until every existing engine key is mapped, adapters must preserve unknown keys under a versioned `legacy_engine_extension`; dropping an output is prohibited.

## NarrativeFactBundle boundary

The fact bundle is a deterministic projection of `CRQResult`. Each fact carries a stable JSON Pointer to its source. Numeric facts also appear in `numeric_allowlist` with raw value, unit and approved rendered form.

The future narrative verifier must reject unsupported numeric claims. The LLM is prohibited from calculating or inferring AAL, VaR, TVaR, probabilities, frequency, treatment reduction or insurance recovery. Missing metrics remain missing; the LLM cannot fill them.
