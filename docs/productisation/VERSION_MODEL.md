# CRQ version model

## Authoritative future identifiers

| Identifier | Meaning | Change rule | Current authority |
|---|---|---|---|
| `platform_version` | Repository/product release containing contracts, adapters and application code | Product-level semantic version | `pyproject.toml` and `crq.versions.PLATFORM_VERSION` |
| `engine_version` | Quantitative implementation for one domain | Change for any quantitative implementation or execution-semantics change | `it_crq.engine.ENGINE_VERSION` or `ot_crq.engine.ENGINE_VERSION` |
| `methodology_version` | Governed mathematical methodology, independent of software packaging | Change only through model-governance approval | Currently historical name `unified_balbix_impact`; future draft identifier in `crq.versions` |
| `input_schema_version` | `CRQAssessment` JSON contract | Change under schema compatibility rules | `crq.versions` plus assessment schema `$id` |
| `output_schema_version` | `CRQResult` JSON contract | Change under schema compatibility rules | `crq.versions` plus result schema `$id` |
| `model_bundle_version` | Immutable publication of all assumptions needed by one engine/pack combination | New version for any governed content change | ModelBundle manifest; draft contract only in this phase |
| `sector_pack_version` | Sector-specific calibration revision | New version for any sector-pack content/calibration change | `config/sector_pack_registry.json` and matching pack metadata |

Workbook and router versions remain historical compatibility identifiers. They must not be used as aliases for the platform or engine version.

## Current identifier inventory

| Current identifier | Source | Current value | Actual meaning | Authoritative now? | Stale or inconsistent? | Future identifier |
|---|---|---:|---|---|---|---|
| Project package version | `pyproject.toml` | `1.2.0` | Accepted repository/package release | Yes | Previously disagreed with `crq.__version__`; now safely centralized | `platform_version` |
| `crq.__version__` | `src/crq/__init__.py` | `1.2.0` | Python package release | Yes, delegated to `PLATFORM_VERSION` | Corrected without changing legacy workbook identifiers | `platform_version` |
| `COMBINED_MODEL_VERSION` | `src/crq/__init__.py` | `1.0.0` | Combined Excel compatibility format | Yes for the historical workbook | Not a platform version | Future `excel_adapter_version`, not one of the seven run identifiers |
| `ROUTER_VERSION` | `src/crq/__init__.py` | `1.0.0` | Existing Excel router | Yes for router behavior | Historical; must not label the platform | Platform adapter provenance |
| Combined workbook filename | `model/Guided_IT_OT_CRQ_Model_v1_0.xlsx` | `v1_0` | Workbook release label | Historical artifact | Does not equal package 1.2.0 | Excel adapter/template version |
| Router config schema | `config/sector_router_config.json` | `IT-OT-ROUTER-1.0` | Configuration-file format | Yes | Separate from input schema | Configuration schema version |
| Router config combined/router | same file | `1.0.0` / `1.0.0` | Workbook/router compatibility | Yes, historical | Not the platform release | Adapter provenance |
| IT engine | `src/it_crq/engine.py` | `1.1.1` | IT quantitative implementation | Yes | Consistent with IT package and registry minimum | `engine_version` |
| Native IT workbook filename | `model/it/Guided_IT_CRQ_Model_v1_1_1_Dashboard.xlsx` | `v1_1_1` | Native IT workbook/engine-era label | Historical | Aligned with IT engine | Excel adapter provenance |
| OT engine | `src/ot_crq/engine.py` | `1.7.1` | OT quantitative implementation | Yes | Some documentation still says 1.7 | `engine_version` |
| OT `WORKBOOK_VERSION` | `src/ot_crq/engine.py` | `1.7` | OT workbook metadata written by engine | Yes for legacy output | Differs from engine 1.7.1 and filename v1.8 | Excel adapter/template version |
| Native OT workbook filename | `model/ot/Guided_OT_CRQ_Model_v1_8_Sector_Packs.xlsx` | `v1_8` | Workbook release label | Historical | Differs from `WORKBOOK_VERSION` 1.7 | Excel adapter/template version |
| FS pack | pack registry and metadata | ID `FS-v1.1.1`, version `1.1.1` | IT Financial Services calibration | Yes | Working-prior status must remain visible | `sector_pack_version`; included by ModelBundle |
| PG pack | pack registry and metadata | ID `PG-v1.6`, version `1.6` | OT Power Generation calibration | Yes | Working/reference calibration | `sector_pack_version` |
| EA pack | pack registry and metadata | ID `EA-v1.0`, version `1.0` | OT Energy Assets calibration | Yes | Working calibration | `sector_pack_version` |
| MF pack | pack registry and metadata | ID `MF-v1.0`, version `1.0` | OT Manufacturing calibration | Yes | Working calibration | `sector_pack_version` |
| Pack registry schema | `config/sector_pack_registry.json` | `CRQ-PACK-REGISTRY-1.0` | Registry file shape | Yes | None identified | Configuration schema version |
| IT pack schema | engine/registry/pack metadata | `CRQ-PACK-1.1` | IT pack workbook format | Yes | None identified | ModelBundle ingestion schema |
| OT pack schema | registry/pack metadata | `CRQ-OT-PACK-1.0` | OT pack workbook format | Yes | None identified | ModelBundle ingestion schema |
| Impact catalogue | `src/crq/impact/catalogue.py` | `1.0.0` | Balbix-aligned driver catalogue | Yes for catalogue data | Not an engine/platform version | ModelBundle component version |
| Historical methodology | freeze fixtures and acceptance docs | `unified_balbix_impact` | Accepted methodology identity | Yes for the frozen baseline | No independent semantic version | `methodology_version` |
| Acceptance release | freeze record/docs | `1.2.0`, tag `v1.2.0` local only | Approved release record | Yes as documentary evidence | Tag is absent from current repository | `platform_version` plus approval record |
| OI CSV filename | `outside_in_schema_v0_2.csv` | `v0.2` | Physical sample/header revision | Historical | Conflicts with router `OI_SCHEMA_VERSION` | Future evidence schema version |
| OI router constant/config | `router.py`, router config | `1.0.0` | Claimed OI integration contract | Current code authority | Does not validate all claimed fields/version | Future evidence schema version |
| Production fixtures | `tests/fixtures/regression_*.json` | engine/pack-specific values | Accepted result snapshots | Yes through 2026-08-27 freeze hashes | Partial result surface; previously not engine-executed in tests | Approved baseline version/provenance |
| Generated output metadata | workbook bridge/results | combined 1.0, engine 1.1.1/1.7.1, pack IDs | Run provenance | Yes for that artifact | Fragmented vocabulary | CRQResult provenance identifiers |
| README examples | `README.md` | combined 1.0, IT 1.1.1, OT 1.7.1 | User-facing examples | Informational | IT example differs from current 500k accepted fixture | Derived documentation, never authority |
| Input contract | `contracts/schemas/crq-assessment.schema.json` | `1.0.0-draft` | Future structured assessment | Draft authority | Not yet consumed by engines | `input_schema_version` |
| Output contract | `contracts/schemas/crq-result.schema.json` | `1.0.0-draft` | Future structured result | Draft authority | Not yet produced by engines | `output_schema_version` |
| ModelBundle contract | `contracts/schemas/model-bundle.schema.json` | `1.0.0-draft` | Future immutable assumption bundle | Draft authority | Not yet materialized | `model_bundle_version` |

Historical workbooks, fixtures, acceptance files and release notes are intentionally unchanged.

