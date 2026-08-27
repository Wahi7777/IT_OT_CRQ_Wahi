# Microsoft Excel UAT checklist — recorded results

Python cannot evaluate dashboard `IF`/`XLOOKUP` display. Complete this in Excel on the freeze workbooks.

**Agent environment (23 Aug 2026):** Excel.app is installed. AppleScript open/recalc failed (`Connection invalid` / compile error). **Live Excel UAT is therefore NOT recorded as PASS.** Operators must execute the table below.

Freeze workbooks (after `freeze_goldens.py`):

| Sector | File |
| --- | --- |
| Financial Services | `_work/golden_freeze/out_regression_it_fs_500k.xlsx` |
| Power Generation | `_work/golden_freeze/out_regression_ot_power_generation.xlsx` |
| Energy Assets | `_work/golden_freeze/out_regression_ot_energy_assets.xlsx` |
| Manufacturing | `_work/golden_freeze/out_regression_ot_manufacturing.xlsx` |

## Already evidenced in Python (do not retick as Excel)

| Check | Result 23 Aug 2026 |
| --- | --- |
| Freeze workbooks open in openpyxl | PASS |
| `#REF!` `#VALUE!` `#DIV/0!` `#NAME?` `#N/A` in cell **values** | PASS (0 hits, all four outputs) |
| Output Bridge B15/C15 numeric ENGINE_WRITTEN | PASS (PG example: Best 1,323,497.77 / Prudent 1,935,742.98) |
| Dashboard A8 formula | `=IF('00 Run Setup'!C9="Best Estimate",'00 Output Bridge'!B15,'00 Output Bridge'!C15)` |
| Dashboard selected-view cache B71 | Equals Prudent AAL (PG 1,935,742.98) |
| Canonical overwrite protection | PASS (CLI) |
| Tab order on **template** | PASS vs `EXPECTED_TAB_ORDER` |
| Result workbooks extra sheet | `00 Engine Results` appended (70 sheets) |

## Operator Excel (not executed here)

For each freeze file: open without repair; Full Calculation; confirm Dashboard A8 equals Bridge C15 (Prudent); TVaR95/99 selectors; no broken links; no unexpected macros; Run Setup sector/asset filters; Outside-In Yes/No; actor/scenario charts readable.

- [ ] FS displayed KPIs
- [ ] PG displayed KPIs
- [ ] EA displayed KPIs
- [ ] MF displayed KPIs
