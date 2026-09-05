# Guided IT/OT CRQ

One Excel front end and one launcher. Two governed engines that are never blended:

| Domain | Engine | Unit of analysis | Sector pack |
| --- | --- | --- | --- |
| **IT** | v1.1.1 | Organisation | Financial Services (`FS-v1.1.1`) |
| **OT** | v1.7.1 | Facility | Power Generation (`PG-v1.6`), Energy Assets (`EA-v1.0`), Manufacturing (`MF-v1.0`) |

On `00 COMMON - Run Setup`, **C6** (IT or OT) and **C7** (sector) select the engine and the pack listed in `config/sector_pack_registry.json`. Pack files under `sector_packs/` supply sector calibration. Core methodology stays in the combined workbook plus `src/it_crq` / `src/ot_crq`.

**Breach impact:** Balbix cost drivers are adapted into a unified catalogue (`src/crq/impact/`). Sector packs select and calibrate applicable drivers; facility/organisation workbooks supply exposures. Reporting rolls drivers into Balbix major categories (not control-channel loss blocks). See [docs/methodology/UNIFIED_BALBIX_IMPACT.md](docs/methodology/UNIFIED_BALBIX_IMPACT.md).

**Acceptance status (unified Balbix impact):** **Outcome A — model frozen** (2026-08-27, release **1.2.0**). VaR 95 / VaR 99 precision exception documented. See [docs/validation/BALBIX_UNIFIED_IMPACT_ACCEPTANCE.md](docs/validation/BALBIX_UNIFIED_IMPACT_ACCEPTANCE.md).

**Release packaging:** See [docs/release_notes/PRODUCTION_READINESS_REPORT.md](docs/release_notes/PRODUCTION_READINESS_REPORT.md). Excel visual UAT is operator-owned.

## Repository layout

```text
.
├── README.md                 # this file
├── CHANGELOG.md              # package history
├── pyproject.toml            # canonical packaging, pytest, ruff
├── requirements.txt          # runtime pin file for pip / pip-audit (must match pyproject)
├── config/                   # pack registry and router documentation JSON
├── sector_packs/             # four governed pack workbooks (do not edit for a run)
│   ├── IT/                   # Financial Services
│   └── OT/                   # Power Generation, Energy Assets, Manufacturing
├── src/                      # Python engines and combined router
├── model/                    # canonical Excel templates (never overwrite on a live run)
│   ├── Guided_IT_OT_CRQ_Model_v1_0.xlsx   # current combined workbook
│   ├── it/                   # native IT template staged by the router
│   └── ot/                   # standalone OT workbook (not used by python -m crq)
├── tests/                    # unit, integration, regression; fixtures/ holds goldens
├── docs/                     # methodology, user guide, validation, security, release notes
├── evidence/                 # Outside-In schema / provenance
├── assessments/              # your copies of the template (user inputs)
├── outputs/                  # generated results; retain balbix_acceptance/ evidence
├── scripts/                  # validation / acceptance harnesses (maintainers)
└── _work/                    # freeze/staging workspace (local)
```

## Current model and sector packs

| Role | Path |
| --- | --- |
| Combined workbook template | `model/Guided_IT_OT_CRQ_Model_v1_0.xlsx` |
| Financial Services pack | `sector_packs/IT/IT_CRQ_Sector_Pack_Financial_Services_v1_1_1.xlsx` |
| Power Generation pack | `sector_packs/OT/OT_CRQ_Sector_Pack_Power_Generation_v1_6.xlsx` |
| Energy Assets pack | `sector_packs/OT/OT_CRQ_Sector_Pack_Energy_Assets_v1_0.xlsx` |
| Manufacturing pack | `sector_packs/OT/OT_CRQ_Sector_Pack_Manufacturing_v1_0.xlsx` |

## What you may edit

| You edit | System-managed |
| --- | --- |
| A copy of the template under `assessments/` | `model/` templates |
| FILL IT or FILL OT tabs for the selected domain | Pack/core/calc sheets labelled Advanced / Read Only |
| `00 COMMON - Run Setup` C6–C8 (and simulation years if needed; production standard is **500,000**) | `sector_packs/` (calibration; not per-assessment) |
| Optional `00 COMMON - Outside-In` | `src/` engines and router |
| Optional reporting settings on IT/OT assessment tabs | Golden fixtures under `tests/fixtures/` (re-freeze only with explicit approval) |

## Install

Python 3.11 or newer.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export PYTHONPATH="$PWD/src:."
```

Dev checks (pytest, ruff, bandit, pip-audit): `pip install -e ".[dev]"`.

Canonical runtime entry point: **`python -m crq`** (same as the `crq` console script). Do not use `python -m it_crq` or `python -m ot_crq` for combined assessments.

## Run an assessment (standard 500k)

1. Copy `model/Guided_IT_OT_CRQ_Model_v1_0.xlsx` to `assessments/<name>.xlsx`.
2. Set **C6** domain, **C7** sector, **C8** asset or organisation on `00 COMMON - Run Setup`.
3. Confirm **SIMULATION_YEARS = 500000** (production standard) and the intended seed on the organisation / facility inputs.
4. Complete only the FILL tabs for that domain.
5. Optionally hide the unused domain:

```bash
python -m crq prepare --model assessments/<name>.xlsx
```

6. Run (writes a **separate** output; never pass `model/` as `--out`):

```bash
python -m crq run --model assessments/<name>.xlsx --out outputs/<name>_results.xlsx
```

Control What-If is on unless you pass `--no-whatifs`. Results go to `--out` (default under `outputs/` with a timestamp).

Workbook structure and packs can be regenerated with `python -m crq rebuild-workbook` (maintainers).

## Inputs, outputs, tests, validation

| Location | Purpose |
| --- | --- |
| `assessments/` | User assessment workbooks (edit here) |
| `outputs/` | Generated results; keep customer outputs you need |
| `outputs/balbix_acceptance/` | Unified-impact acceptance evidence (JSON + production 500k workbooks) |
| `tests/fixtures/` | Golden fixtures (do not alter without approval) |
| `docs/methodology/` | Current methodology (including unified Balbix impact) |
| `docs/user_guide/` | Operator / Excel guidance |
| `docs/validation/` | Acceptance, QA, gap analysis, cleanup manifest |

## Tests

```bash
export PYTHONPATH="$PWD/src:."
python -m pytest tests
python -m crq validate-release                 # fast CI + ruff + bandit + pip-audit
python -m crq validate-release --production    # execute approved 500k baselines; never regenerate them
```

## Documentation

- [Unified Balbix impact acceptance](docs/validation/BALBIX_UNIFIED_IMPACT_ACCEPTANCE.md)
- [Unified Balbix impact methodology](docs/methodology/UNIFIED_BALBIX_IMPACT.md)
- [Business impact (user guide)](docs/user_guide/BUSINESS_IMPACT.md)
- [User Excel UAT](docs/user_guide/EXCEL_UAT_CHECKLIST.md)
- [Assumption ownership](docs/methodology/ASSUMPTION_OWNERSHIP.md)
- [QA tiers](docs/validation/QA_VALIDATION.md)
- [Cleanup manifest](docs/validation/CLEANUP_MANIFEST.md)
- [Security review](docs/security/SECURITY_REVIEW.md)
- [Engine changelog](docs/release_notes/MODEL_CHANGELOG.md)
- [Productisation contracts and ownership](docs/productisation/CONTRACTS_AND_OWNERSHIP.md)
- [Machine-readable field inventory](contracts/mappings/field-inventory.json)
- [Immutable baseline policy](docs/productisation/BASELINE_POLICY.md)
- [Version model](docs/productisation/VERSION_MODEL.md)
- [Lambda benchmark](docs/productisation/LAMBDA_BENCHMARK.md)
- [OT VaR drift investigation](docs/productisation/OT_VAR_DRIFT_INVESTIGATION.md)
- [Phase 2 structured execution boundary](docs/productisation/PHASE2_STRUCTURED_EXECUTION.md)
- [Phase 3A runtime-neutral application service](docs/productisation/PHASE3A_APPLICATION_SERVICE.md)
