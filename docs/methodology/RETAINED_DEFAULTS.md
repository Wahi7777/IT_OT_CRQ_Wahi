# Intentionally retained defaults

| Default | Classification | Why retained |
|---|---|---|
| IT / OT “Not Assessed” maturity → Developing (0.50) | Governed prior | Documented in both engines and pack settings. |
| OT blank coverage → DEFAULT_COVERAGE (75%) | Governed prior | Pack setting `DEFAULT_COVERAGE`. |
| OT unused driver operands blank → 0 | Acceptable default | Formula type does not consume that column (e.g. BI_SCENARIO rates). |
| IT `REPORTING_VIEW=Both` → Prudent for detailed sheets | Governed prior | Existing resolver. |
| Geography aliases UAE/GCC → `UAE / GCC` | User convenience | Only when a non-blank alias is supplied; blank still fails. |
| Combined CLI default model path | User convenience | Explicit `--model` recommended for assessments. |

Removed as dangerous silent fallbacks: blank geography → UAE; unknown TTP facility gate → True; missing sector multiplier → 1.00; blank financial `_number` → 0.
