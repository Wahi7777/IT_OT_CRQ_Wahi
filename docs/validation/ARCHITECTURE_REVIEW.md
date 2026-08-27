# Architecture review (code-verified)

Historical review dated 23 Aug 2026. Several paths in the tables below were true at inspection and have been superseded: the canonical combined workbook is `model/Guided_IT_OT_CRQ_Model_v1_0.xlsx`; tests and `docs/` now exist; OT packs live under `sector_packs/OT/`. Prefer README and `config/sector_pack_registry.json` for current layout.

Inspected 23 Aug 2026 against the live tree. README, QA validation notes and workbook comments were treated as claims only.

## What the code actually does

```text
User
  ↓
python -m it_ot_crq run  (combined router)
  ↓
Copy combined workbook to outputs/ (canonical template is not the write target)
  ↓
Read 00 Run Setup!C6  → sector
  ↓
SECTOR_DOMAIN dict
  ├── Financial Services → domain IT → stage native IT schema → it_crq.engine.refresh
  └── Power Generation | Energy Assets | Manufacturing
        → write sector/asset into 03 Facility Inputs
        → ot_crq.engine.refresh (xlsx_backend; OT_CRQ_USE_XLSX_BACKEND=1)
  ↓
Optional CSV snapshot + approved-row conditioning (facility / org / IT exposure fields only)
  ↓
Engine writes native result sheets
  ↓
Excel formulas on 00 Output Bridge / 00 Dashboard (not recalculated by Python)
```

This matches the intended “one UX, two methodologies” shape. There is **no hybrid calculation engine**. The router does not multiply IT and OT paths together.

## Directory map (as found)

| Path | Role |
|---|---|
| `src/it_ot_crq/` | Combined router + CLI (`run_combined`) |
| `src/it_crq/engine.py` | Organisation-level IT CRQ v1.1.1 |
| `src/ot_crq/engine.py` | Facility-level OT CRQ v1.7 (`ENGINE_VERSION = "1.7"`) |
| `src/ot_crq/xlsx_backend.py` | openpyxl shim replacing `artifact_tool` |
| `src/ot_crq/dashboard.py` | No-op presentation adapter |
| `model/Guided_IT_OT_CRQ_Combined_Model_v0_3.xlsx` | Combined 69-sheet workbook |
| `model/it/Guided_IT_CRQ_Model_v1_1_1_Dashboard.xlsx` | Governed IT template staged by the router |
| `model/ot/Guided_OT_CRQ_Model_v1_8_Sector_Packs.xlsx` | Standalone OT workbook (not used by combined runner) |
| `sector_packs/IT_CRQ_Sector_Pack_Financial_Services_v1_1_1.xlsx` | External IT pack |
| `config/sector_router_config.json` | Documentation JSON; **not read by Python** |
| `evidence/outside_in/` | Schema CSV only (no real findings) |
| `tests/` | **Absent** |
| `docs/` | Absent at inspection |

## Routing contract (code)

`SECTOR_DOMAIN` in `src/it_ot_crq/router.py`:

- Financial Services → IT
- Power Generation, Energy Assets, Manufacturing → OT
- Any other sector → `ValueError` (fail closed)

Excel `00 Run Setup!C7` is `=IF(C6="Financial Services","IT","OT")`. That is **not** fail-closed: an unknown sector would display OT in the workbook even though Python refuses to run it.

OT facility cells C20/C21 are Excel formulas. The router overwrites them with literals before `ot_crq.refresh` because the Python engine cannot use cached formula values.

IT always forces staged `03 Organisation Inputs!C19 = Financial Services`.

OT packs are **embedded** (sheets 28–33). The `--sector-pack-dir` argument is unused for OT. IT requires the FS pack file.

## IT methodology (engine)

Confirmed in `it_crq.engine`:

- Organisation inputs, four actors (including Hacktivist), pack-driven routes
- Attempt frequency = reference × org × geo × weighted actor activity; route shares renormalised over valid paths
- `event_rate = attempt × P(success)`
- Staged product of through-probabilities; unrequired stages contribute 1.0
- Control aggregation: diminishing incremental credit + barrier cap
- Log-normal loss blocks; Poisson years; CRN via `default_rng(seed)` per view
- AAL, VaR (numpy `method="higher"`), fractional Expected Shortfall, AEP/OEP, actor/scenario decomp
- Control what-ifs are **analytic AAL**, not a second Monte Carlo

Default `SIMULATION_YEARS` in the combined IT inputs is 500,000.

## OT methodology (engine)

Confirmed in `ot_crq.engine.refresh`:

- 3 actors × 5 scenarios = 15 cells
- Composite S1–S5: `P(success|campaign) = product(required stage-throughs)`
- Malicious Insider S1 is not required (`through = 1`)
- S5 requires a scenario-defining TTP
- ATT&CK relevance = scenario ∩ actor ∩ sector rationale ∩ facility gate
- Barriers averaged across relevant TTPs; missing Prevent maps contribute 0
- Frequency separate from success; CRN context reused for control what-ifs
- **Hard requirement** `N == 500_000`
- Dashboard writer is a no-op; native OT summary sheets are still written

Workbook version constant is `"1.7"` while the file on disk is named v1.8. Combined runner labels OT as v1.7.

## Outside-in (code)

- Optional. Run Setup C10 not in `{yes,true,1}` → no file.
- Only rows with `approved` and `quantitative_target` are applied.
- Targets: OT `facility_input`, IT `organisation_input`, IT `exposure_route`.
- No generic AAL multiplier.
- Gaps: no path confinement; CSV text written as-is (formula injection); no polarity / double-counting rules; rationale columns are a subset of the mandated audit fields; unapproved files with `Apply=Yes` still fail if the path is missing.

## Output Bridge / dashboards

`00 Dashboard` KPIs are Excel `IF` formulas against `00 Output Bridge`, which in turn `IF`s IT vs OT engine sheets. Python does not write the bridge. openpyxl will not evaluate those formulas, so **Python cannot independently prove dashboard = engine without a formula evaluator or by writing cached values**.

OT campaign-frequency bridge cells reconstruct λ from summary products and, on the Prudent side, multiply by `06 Frequency Assumptions!D17`. That is extra quantitative logic and can diverge from engine λ.

Risk Transfer sheet labels itself as an indicative diagnostic (`TVaR − retention`). That matches the engines (neither simulates policy terms).

## Combined workbook groups

Physical order matches the five logical groups (divider sheets + domain sheets). Engine-critical OT names (`03 Facility Inputs`, `15 Attack Path Calc`, …) and IT prefixed names (`IT 03 Organisation Inputs`, …) are preserved.

## Fail-closed gaps found in code (pre-remediation)

| Location | Behaviour | Classification |
|---|---|---|
| OT `canonical_geography` empty → `"UAE / GCC"` | Dangerous silent fallback | Must fail closed |
| OT `facility_ttp_feasible` unknown code → `True` | Fail-open gate | Must fail closed |
| OT `exposure_map.get(key, 1.0)` | Silent 1.00 | Dangerous if a required pair is missing |
| OT `_number(None) → 0.0` | Silent zero for blank financials | Dangerous silent fallback |
| Excel unknown sector → OT | Presentation fail-open | Must fail closed |
| Router outside-in path | No traversal / symlink guards | Security |
| Unpinned `requirements.txt` (`numpy`, `openpyxl`) | Uncontrolled supply chain | Release |

## Tests and release controls (pre-remediation)

- No pytest suite, no `pyproject.toml`, no `python -m crq`.
- QA_VALIDATION.md claims four-sector PASS with no artefacts in `outputs/`.
- `config/sector_router_config.json` still names v0.2 workbook.

## Conclusion of inspection

The repository **is** a router over two separate governed engines, not a blended model. It is **not** a complete production v1.0 package: missing tests, unpinned dependencies, Excel/Python routing mismatch, silent OT fallbacks, untrusted-file handling, and no Python-owned Output Bridge snapshot.
