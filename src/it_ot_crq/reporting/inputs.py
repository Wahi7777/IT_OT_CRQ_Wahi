"""Read appetite and insurance programme inputs from the combined workbook."""

from __future__ import annotations

from crq.appetite import APPETITE_INPUT_KEYS, parse_appetite_inputs
from crq.insurance import parse_programme
from it_ot_crq.reporting import APPETITE_INPUT_LABELS
from it_ot_crq.reporting.layout import write_cell
from openpyxl.styles import Font, Alignment, PatternFill

INPUT_FILL = PatternFill("solid", fgColor="FFF2CC")


def ensure_appetite_inputs_on_run_setup(wb) -> None:
    """Add optional appetite input block on Run Setup (no defaults)."""
    if "00 COMMON - Run Setup" not in wb.sheetnames:
        return
    ws = wb["00 COMMON - Run Setup"]
    if ws["A50"].value == "RISK APPETITE (optional)":
        return
    # Prefer rows far below the routing contract to avoid template merges.
    ws["A50"] = "RISK APPETITE (optional)"
    ws["A50"].font = Font(name="Carlito", bold=True, size=11, color="1F4E79")
    ws["A51"] = (
        "Leave blank when unset. These thresholds are independent of insurance retention. "
        "Blank → Tolerance not set."
    )
    ws["A51"].alignment = Alignment(wrap_text=True)
    ws["A52"] = "Parameter"
    ws["B52"] = "Description"
    ws["C52"] = "Value"
    for i, (key, label) in enumerate(APPETITE_INPUT_LABELS):
        row = 53 + i
        ws.cell(row, 1, key)
        ws.cell(row, 2, label)
        if ws.cell(row, 3).value is None:
            ws.cell(row, 3).value = None
        ws.cell(row, 3).fill = INPUT_FILL


def read_appetite_inputs(wb) -> dict:
    out = {}
    if "00 COMMON - Run Setup" in wb.sheetnames:
        ws = wb["00 COMMON - Run Setup"]
        for row in list(range(53, 58)) + list(range(43, 48)):
            key = str(ws.cell(row, 1).value or "").strip()
            if key in APPETITE_INPUT_KEYS:
                out[key] = ws.cell(row, 3).value
    # Sheet 06 may override
    if "06 Appetite & Insurance" in wb.sheetnames:
        ws = wb["06 Appetite & Insurance"]
        for row in range(5, 12):
            key = str(ws.cell(row, 1).value or "").strip()
            if key in APPETITE_INPUT_KEYS and ws.cell(row, 2).value not in (None, ""):
                out[key] = ws.cell(row, 2).value
    return parse_appetite_inputs(out)


def ensure_insurance_inputs(wb) -> None:
    """Yellow input cells for insurance programme on sheet 06."""
    if "06 Appetite & Insurance" not in wb.sheetnames:
        return
    ws = wb["06 Appetite & Insurance"]
    if ws["A20"].value == "INSURANCE PROGRAMME INPUTS":
        return
    from it_ot_crq.reporting.layout import section_header, _title, _subtitle

    # Only seed structure if sheet is empty-ish
    if ws["A1"].value in (None, ""):
        _title(ws, "06 — Appetite & Insurance")
        _subtitle(
            ws,
            "Risk-appetite thresholds are organisational policy inputs. "
            "Insurance programme terms are risk-financing inputs — not pricing.",
        )
    section_header(ws, 4, "RISK APPETITE INPUTS (optional — leave blank if unset)")
    write_cell(ws, 5, 1, "Parameter", bold=True)
    write_cell(ws, 5, 2, "Value", bold=True)
    for i, (key, label) in enumerate(APPETITE_INPUT_LABELS):
        write_cell(ws, 6 + i, 1, key)
        write_cell(ws, 6 + i, 3, label)
        write_cell(ws, 6 + i, 2, None, input_cell=True)

    section_header(ws, 12, "INSURANCE PROGRAMME INPUTS (risk-financing — not pricing)")
    write_cell(ws, 13, 1, "INSURANCE_RETENTION", bold=True)
    write_cell(ws, 13, 2, 0, r"$#,##0", input_cell=True)
    write_cell(ws, 14, 1, "PRIMARY_LIMIT", bold=True)
    write_cell(ws, 14, 2, None, r"$#,##0", input_cell=True)
    write_cell(ws, 15, 1, "AGGREGATE_PROGRAMME_LIMIT", bold=True)
    write_cell(ws, 15, 2, None, r"$#,##0", input_cell=True)
    write_cell(ws, 17, 1, "Layer", bold=True)
    write_cell(ws, 17, 2, "Attachment", bold=True)
    write_cell(ws, 17, 3, "Limit", bold=True)
    write_cell(ws, 17, 4, "Coinsurance", bold=True)
    for i, name in enumerate(("Primary", "Excess 1", "Excess 2", "Excess 3"), start=18):
        write_cell(ws, i, 1, name, input_cell=True)
        write_cell(ws, i, 2, None, r"$#,##0", input_cell=True)
        write_cell(ws, i, 3, None, r"$#,##0", input_cell=True)
        write_cell(ws, i, 4, 1.0, "0%", input_cell=True)

    ws["A20"] = "INSURANCE PROGRAMME INPUTS"


def read_insurance_programme(wb) -> dict:
    """Build programme dict from sheet 06 and IT/OT retention fallbacks."""
    raw: dict = {"layers": []}
    # Domain retention (insurance only)
    if "IT 08 - Reporting Settings" in wb.sheetnames:
        try:
            raw["INSURANCE_RETENTION"] = wb["IT 08 - Reporting Settings"]["B18"].value
        except Exception:
            pass
    if "06 Appetite & Insurance" in wb.sheetnames:
        ws = wb["06 Appetite & Insurance"]
        ret = ws["B13"].value
        if ret not in (None, ""):
            raw["INSURANCE_RETENTION"] = ret
        prim = ws["B14"].value
        if prim not in (None, ""):
            raw["PRIMARY_LIMIT"] = prim
        agg = ws["B15"].value
        if agg not in (None, ""):
            raw["AGGREGATE_PROGRAMME_LIMIT"] = agg
        for row in range(18, 22):
            name = ws.cell(row, 1).value
            att = ws.cell(row, 2).value
            lim = ws.cell(row, 3).value
            coin = ws.cell(row, 4).value
            if lim in (None, "") or float(lim or 0) <= 0:
                continue
            raw["layers"].append(
                {
                    "name": str(name or f"Layer {row - 17}"),
                    "attachment": float(att or 0),
                    "limit": float(lim),
                    "coinsurance": 1.0 if coin in (None, "") else float(coin),
                }
            )
    return raw


def read_revenue(wb, domain: str) -> float | None:
    try:
        if domain == "IT" and "IT 03 - Organisation Inputs" in wb.sheetnames:
            ws = wb["IT 03 - Organisation Inputs"]
            for r in range(16, 40):
                if str(ws.cell(r, 1).value or "").strip() == "ANNUAL_REVENUE_AT_RISK":
                    v = ws.cell(r, 3).value
                    return float(v) if v not in (None, "") else None
        if domain == "OT" and "OT 05 - Impact & BIA" in wb.sheetnames:
            ws = wb["OT 05 - Impact & BIA"]
            for r in range(16, 25):
                if str(ws.cell(r, 1).value or "").strip() == "ANNUAL_REVENUE_AT_RISK":
                    v = ws.cell(r, 3).value
                    return float(v) if v not in (None, "") else None
    except Exception:
        return None
    return None
