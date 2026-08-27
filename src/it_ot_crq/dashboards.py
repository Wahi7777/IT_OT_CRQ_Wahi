"""Populate common dashboards after an IT or OT engine run."""

from __future__ import annotations

import math
from collections import defaultdict

from openpyxl.chart import ScatterChart, Series, Reference
from openpyxl.chart.data_source import NumData, NumFmt, NumVal, StrData, StrVal
from openpyxl.chart.marker import Marker
from openpyxl.chart.shapes import GraphicalProperties
from openpyxl.drawing.line import LineProperties
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation

CURRENCY = r"$#,##0"
PCT = "0.0%"
YELLOW = PatternFill("solid", fgColor="FFF2CC")
LEC_AEP_COLOR = "1F4E79"
LEC_OEP_COLOR = "C45911"
LEC_LINE_WIDTH = 25000
IT_ACTORS = ("Nation-state", "Cybercriminal", "Malicious insider", "Hacktivist")
IT_SCENARIOS = (
    "Critical business-service disruption",
    "Sensitive-data compromise",
    "Data or transaction-integrity compromise",
    "Cyber-enabled theft or fraud",
)
OT_ACTORS = ("Nation State", "Cybercriminal", "Malicious Insider")
OT_SCENARIOS = (
    "Operational Disruption",
    "Loss of Control or Visibility",
    "Process Manipulation",
    "Safety System Compromise",
    "Destructive or Integrity Attack",
)
OT_STAGES = {
    "S1": "Initial access",
    "S2": "Establish presence",
    "S3": "Lateral movement / process access",
    "S4": "Understand the process",
    "S5": "Achieve adverse outcome",
}


def populate_common_dashboards(wb, result: dict, meta: dict) -> None:
    domain = str(meta.get("domain") or "").strip()
    view = str(meta.get("reporting_view") or "Prudent").strip()
    _write_lec_bridge(wb, domain)
    _format_executive_dashboard(wb, result, view)
    _populate_risk_drivers(wb, domain)
    _populate_loss_analysis(wb, domain)
    _cleanup_whatif(wb)
    _fix_risk_transfer(wb, view)
    _refresh_chart_caches(wb, view, result)


def _write_cell(ws, row, col, value, number_format=None):
    cell = ws.cell(row, col)
    if cell.__class__.__name__ == "MergedCell":
        return
    cell.value = value
    if number_format:
        cell.number_format = number_format


def _write_lec_bridge(wb, domain: str) -> None:
    ws = wb["00 COMMON - Output Bridge"]
    _write_cell(ws, 41, 1, "AGGREGATE LOSS-EXCEEDANCE DATA")
    _write_cell(ws, 42, 1, "Exceedance probability")
    _write_cell(ws, 42, 2, "Best AEP")
    _write_cell(ws, 42, 3, "Best OEP")
    _write_cell(ws, 42, 4, "Prudent AEP")
    _write_cell(ws, 42, 5, "Prudent OEP")
    rows = _lec_rows(wb, domain)
    for i in range(11):
        dest = 43 + i
        if i < len(rows):
            prob, best_aep, best_oep, pr_aep, pr_oep = rows[i]
            _write_cell(ws, dest, 1, prob, PCT)
            _write_cell(ws, dest, 2, best_aep, CURRENCY)
            _write_cell(ws, dest, 3, best_oep, CURRENCY)
            _write_cell(ws, dest, 4, pr_aep, CURRENCY)
            _write_cell(ws, dest, 5, pr_oep, CURRENCY)
        else:
            for c in range(1, 6):
                _write_cell(ws, dest, c, None)


def _lec_rows(wb, domain: str) -> list[tuple]:
    if domain == "IT" and "IT CALC - Aggregate LECs" in wb.sheetnames:
        src = wb["IT CALC - Aggregate LECs"]
        rows = []
        for r in range(16, 27):
            prob = src.cell(r, 2).value
            if prob in (None, ""):
                continue
            rows.append(
                (
                    float(prob),
                    src.cell(r, 3).value,
                    src.cell(r, 4).value,
                    src.cell(r, 5).value,
                    src.cell(r, 6).value,
                )
            )
        return rows
    if "OT CALC - Aggregate LECs" in wb.sheetnames:
        src = wb["OT CALC - Aggregate LECs"]
        rows = []
        for r in range(16, 27):
            prob = src.cell(r, 1).value
            if prob in (None, ""):
                continue
            rows.append(
                (
                    float(prob),
                    src.cell(r, 2).value,
                    src.cell(r, 3).value,
                    src.cell(r, 4).value,
                    src.cell(r, 5).value,
                )
            )
        return rows
    return []


def _unmerge_kpi_region(dash) -> None:
    for merged in list(dash.merged_cells.ranges):
        if merged.min_row in (7, 8, 9, 10) and merged.max_row <= 11:
            dash.unmerge_cells(str(merged))


def _kpi_formula(bridge_row: int, currency: bool = False) -> str:
    return (
        f'=IF(\'00 COMMON - Run Setup\'!C9="Best Estimate",'
        f"'00 COMMON - Output Bridge'!B{bridge_row},"
        f"'00 COMMON - Output Bridge'!C{bridge_row})"
    )


def _format_executive_dashboard(wb, result: dict, view: str) -> None:
    dash = wb["00 Dashboard"]
    dash.row_dimensions[4].height = 22
    for col, width in (
        ("A", 14), ("B", 14), ("C", 12), ("D", 14), ("E", 14), ("F", 12),
        ("G", 14), ("H", 14), ("I", 12), ("J", 14), ("K", 14), ("L", 12),
        ("M", 16), ("N", 16),
    ):
        dash.column_dimensions[col].width = width

    _unmerge_kpi_region(dash)
    # Eight headline cards across two rows (labels on 7/9, values on 8/10).
    row1 = [
        (1, "P(ANY SUCCESSFUL EVENT / YR)", _kpi_formula(20), PCT),
        (4, "AAL", _kpi_formula(15), CURRENCY),
        (7, "VaR 95", _kpi_formula(16), CURRENCY),
        (10, "TVaR 95", _kpi_formula(17), CURRENCY),
    ]
    row2 = [
        (1, "VaR 99", _kpi_formula(18), CURRENCY),
        (4, "TVaR 99", _kpi_formula(19), CURRENCY),
        (7, "P(LOSS > TOLERANCE)", _kpi_formula(23), PCT),
        (10, "RISK-APPETITE STATUS", "='00 COMMON - Output Bridge'!B24", None),
    ]
    for start, label, formula, fmt in row1:
        end = start + 2
        dash.merge_cells(start_row=7, start_column=start, end_row=7, end_column=end)
        dash.merge_cells(start_row=8, start_column=start, end_row=8, end_column=end)
        _write_cell(dash, 7, start, label)
        dash.cell(7, start).font = Font(name="Carlito", bold=True, size=9, color="5B6B7A")
        _write_cell(dash, 8, start, formula, fmt)
        dash.cell(8, start).font = Font(name="Carlito", bold=True, size=14, color="0F2A44")
    for start, label, formula, fmt in row2:
        end = start + 2
        dash.merge_cells(start_row=9, start_column=start, end_row=9, end_column=end)
        dash.merge_cells(start_row=10, start_column=start, end_row=10, end_column=end)
        _write_cell(dash, 9, start, label)
        dash.cell(9, start).font = Font(name="Carlito", bold=True, size=9, color="5B6B7A")
        _write_cell(dash, 10, start, formula, fmt)
        dash.cell(10, start).font = Font(name="Carlito", bold=True, size=14, color="0F2A44")

    # Secondary context + dynamic executive narrative.
    narrative = result.get("executive_narrative") or "Run the model to generate the Executive Risk Story."
    p3 = result.get("prudent_pany_3y") if view != "Best Estimate" else result.get("best_pany_3y")
    p5 = result.get("prudent_pany_5y") if view != "Best Estimate" else result.get("best_pany_5y")
    secondary = (
        "Common decision view from the last Python run. "
        f"3-year successful-event probability: {None if p3 is None else f'{100*float(p3):.1f}%'}; "
        f"5-year: {None if p5 is None else f'{100*float(p5):.1f}%'}. "
        f"Largest AAL contributor: {result.get('top_aal_contributor') or '—'}. "
        f"Largest TVaR 99 contributor: {result.get('top_tvar99_contributor') or '—'}."
    )
    _write_cell(dash, 2, 1, secondary)
    try:
        dash.merge_cells("A11:N11")
    except ValueError:
        pass
    _write_cell(dash, 11, 1, narrative)
    dash.cell(11, 1).alignment = Alignment(wrap_text=True, vertical="center")
    dash.cell(11, 1).font = Font(name="Carlito", size=10, color="0F2A44")
    dash.row_dimensions[11].height = 48

    actors = list((result.get("actor_aal") or {}).items())
    scenarios = list((result.get("scenario_aal") or {}).items())
    for i in range(4):
        row = 31 + i
        if i < len(actors):
            _write_cell(dash, row, 1, actors[i][0])
            _write_cell(dash, row, 2, actors[i][1], CURRENCY)
        if i < len(scenarios):
            _write_cell(dash, row, 9, scenarios[i][0])
            _write_cell(dash, row, 10, scenarios[i][1], CURRENCY)
        dash.cell(row, 1).font = Font(name="Carlito", size=9)
        dash.cell(row, 2).font = Font(name="Carlito", size=9)
        dash.cell(row, 9).font = Font(name="Carlito", size=9)
        dash.cell(row, 9).alignment = Alignment(wrap_text=True)
        dash.cell(row, 10).font = Font(name="Carlito", size=9)
    if len(scenarios) < 5:
        for col in range(9, 12):
            _write_cell(dash, 35, col, None)
    probs, aep, oep = _selected_lec(wb, view)
    for i in range(11):
        row = 14 + i
        if i < len(probs):
            _write_cell(dash, row, 1, probs[i], PCT)
            _write_cell(dash, row, 2, aep[i], CURRENCY)
            _write_cell(dash, row, 3, oep[i], CURRENCY)
        else:
            for c in range(1, 4):
                _write_cell(dash, row, c, None)
    _write_cell(dash, 12, 1, "ANNUAL AGGREGATE LOSS EXCEEDANCE CURVE")
    pick = "best" if view == "Best Estimate" else "prudent"
    var95 = result.get(f"{pick}_var95")
    var99 = result.get(f"{pick}_var99")
    _write_cell(dash, 26, 1, "VaR 95 (marked)")
    _write_cell(dash, 26, 2, var95, CURRENCY)
    _write_cell(dash, 26, 3, 0.05, PCT)
    _write_cell(dash, 27, 1, "VaR 99 (marked)")
    _write_cell(dash, 27, 2, var99, CURRENCY)
    _write_cell(dash, 27, 3, 0.01, PCT)
    _write_cell(
        dash,
        28,
        1,
        "TVaR 95 / TVaR 99 are average losses in the respective upper tails — not points on this exceedance curve. "
        "AEP = annual exceedance from the annual aggregate loss distribution (incl. zero-loss years). "
        "OEP = occurrence exceedance from the maximum single-event loss in each simulated year.",
    )
    dash.cell(28, 1).alignment = Alignment(wrap_text=True, vertical="top")
    dash.row_dimensions[28].height = 54
def _populate_risk_drivers(wb, domain: str) -> None:
    ws = wb["00 Risk Drivers"]
    ws.data_validations.dataValidation.clear()
    for col, width in (("A", 28), ("B", 18), ("C", 16), ("D", 42), ("E", 16), ("F", 16), ("G", 28), ("H", 22)):
        ws.column_dimensions[col].width = width
    if domain == "IT":
        actors, scenarios = IT_ACTORS, IT_SCENARIOS
        _write_cell(ws, 2, 1, "IT view: selected actor × scenario, then the organisation attack routes that contribute AAL. This is not the OT five-stage ICS path.")
        _write_lists(ws, actors, scenarios)
        _write_cell(ws, 4, 2, actors[1])
        _write_cell(ws, 4, 4, scenarios[0])
        ws["B4"].fill = YELLOW
        ws["D4"].fill = YELLOW
        freq = "'IT CALC - Frequency and Success'"
        _write_cell(ws, 8, 2, f"=SUMIFS({freq}!D16:D400,{freq}!A16:A400,$B$4,{freq}!B16:B400,$D$4)")
        _write_cell(ws, 8, 4, f'=IFERROR(SUMIFS({freq}!F16:F400,{freq}!A16:A400,$B$4,{freq}!B16:B400,$D$4)/B8,"")')
        _write_cell(ws, 8, 6, f"=SUMIFS({freq}!F16:F400,{freq}!A16:A400,$B$4,{freq}!B16:B400,$D$4)")
        _write_cell(ws, 8, 8, f"=SUMIFS({freq}!J16:J400,{freq}!A16:A400,$B$4,{freq}!B16:B400,$D$4)", CURRENCY)
        ws["B8"].number_format = "0.000"
        ws["D8"].number_format = "0.0%"
        ws["F8"].number_format = "0.000"
        _write_cell(ws, 12, 1, "ATTACK ROUTES (selected actor × scenario)")
        headers = ["Route", "Path valid", "Attempts / yr", "P(success)", "Events / yr", "AAL", "Notes"]
        for c, h in enumerate(headers, 1):
            _write_cell(ws, 13, c, h)
        routes = _it_routes(wb, actors[1], scenarios[0])
        for i in range(8):
            row = 14 + i
            if i < len(routes):
                rec = routes[i]
                for c, val in enumerate(rec, 1):
                    _write_cell(ws, row, c, val, CURRENCY if c == 6 else None)
                ws.cell(row, 3).number_format = "0.000"
                ws.cell(row, 4).number_format = "0.0%"
                ws.cell(row, 5).number_format = "0.000"
            else:
                for c in range(1, 8):
                    _write_cell(ws, row, c, None)
        _apply_dropdown(ws, "B4", "IT_Dash_Actors")
        _apply_dropdown(ws, "D4", "IT_Dash_Scenarios")
        return

    actors, scenarios = OT_ACTORS, OT_SCENARIOS
    _write_cell(ws, 2, 1, "OT view: selected actor × scenario through the five composite stages of the facility attack path.")
    _write_lists(ws, actors, scenarios)
    _write_cell(ws, 4, 2, actors[1])
    _write_cell(ws, 4, 4, scenarios[0])
    ws["B4"].fill = YELLOW
    ws["D4"].fill = YELLOW
    _write_cell(ws, 12, 1, "COMPOSITE ATTACK-PATH STAGES")
    _write_cell(ws, 13, 1, "Stage")
    _write_cell(ws, 13, 7, "Interpretation")
    for i, (sid, meaning) in enumerate(OT_STAGES.items()):
        _write_cell(ws, 14 + i, 1, sid)
        _write_cell(ws, 14 + i, 7, meaning)
    _apply_dropdown(ws, "B4", "OT_Dash_Actors")
    _apply_dropdown(ws, "D4", "OT_Dash_Scenarios")


def _it_routes(wb, actor: str, scenario: str) -> list[list]:
    if "IT CALC - Frequency and Success" not in wb.sheetnames:
        return []
    freq = wb["IT CALC - Frequency and Success"]
    rows = []
    for r in range(16, (freq.max_row or 16) + 1):
        if str(freq.cell(r, 1).value or "").strip() != actor:
            continue
        if str(freq.cell(r, 2).value or "").strip() != scenario:
            continue
        rows.append(
            [
                freq.cell(r, 3).value,
                "Yes",
                freq.cell(r, 4).value,
                freq.cell(r, 5).value,
                freq.cell(r, 6).value,
                freq.cell(r, 10).value,
                "IT composite route",
            ]
        )
    rows.sort(key=lambda x: float(x[5] or 0), reverse=True)
    return rows[:8]


def _populate_loss_analysis(wb, domain: str) -> None:
    ws = wb["00 Loss Analysis"]
    ws.data_validations.dataValidation.clear()
    for col, width in (("A", 28), ("B", 16), ("C", 16), ("D", 42)):
        ws.column_dimensions[col].width = width
    if domain != "IT":
        _write_cell(ws, 4, 2, OT_ACTORS[0])
        _write_cell(ws, 4, 4, OT_SCENARIOS[0])
        ws["B4"].fill = YELLOW
        ws["D4"].fill = YELLOW
        return

    actor, scenario = IT_ACTORS[1], IT_SCENARIOS[0]
    _write_cell(ws, 2, 1, "IT Business Impact view. Annual-aggregate AAL for the selection is shown below; event-level amounts are diagnostics only.")
    _write_cell(ws, 4, 2, actor)
    _write_cell(ws, 4, 4, scenario)
    ws["B4"].fill = YELLOW
    ws["D4"].fill = YELLOW
    freq = "'IT CALC - Frequency and Success'"
    _write_cell(ws, 7, 1, "Successful-Event Consequence Diagnostics")
    _write_cell(
        ws,
        8,
        1,
        "These describe loss severity when an event occurs. They are not annual aggregate VaR or TVaR.",
    )
    _write_cell(ws, 9, 1, "Loss severity per successful event (P50)")
    _write_cell(ws, 9, 2, f"=AVERAGEIFS({freq}!G16:G400,{freq}!A16:A400,$B$4,{freq}!B16:B400,$D$4)", CURRENCY)
    _write_cell(ws, 9, 3, None)
    _write_cell(ws, 9, 4, "Mean P50 event severity across contributing IT routes")
    _write_cell(ws, 10, 1, "Loss severity per successful event (P99)")
    _write_cell(ws, 10, 2, f"=AVERAGEIFS({freq}!H16:H400,{freq}!A16:A400,$B$4,{freq}!B16:B400,$D$4)", CURRENCY)
    _write_cell(ws, 10, 3, None)
    _write_cell(ws, 10, 4, "Mean P99 event severity across contributing IT routes")
    _write_cell(ws, 11, 1, "AAL contribution")
    _write_cell(ws, 11, 2, f"=SUMIFS({freq}!J16:J400,{freq}!A16:A400,$B$4,{freq}!B16:B400,$D$4)", CURRENCY)
    _write_cell(ws, 11, 3, None)
    _write_cell(ws, 11, 4, "Sum of route AAL for the selection (annual aggregate)")
    _write_cell(ws, 14, 1, "LOSS-BLOCK DECOMPOSITION (event severity P50 / P99)")
    _write_cell(ws, 15, 1, "Loss block")
    _write_cell(ws, 15, 2, "P50")
    _write_cell(ws, 15, 3, "P99")
    blocks = _it_loss_blocks(wb, actor, scenario)
    for i in range(8):
        row = 16 + i
        if i < len(blocks):
            name, p50, p99 = blocks[i]
            _write_cell(ws, row, 1, name)
            _write_cell(ws, row, 2, p50, CURRENCY)
            _write_cell(ws, row, 3, p99, CURRENCY)
        else:
            for c in range(1, 4):
                _write_cell(ws, row, c, None)
    _apply_dropdown(ws, "B4", "IT_Dash_Actors")
    _apply_dropdown(ws, "D4", "IT_Dash_Scenarios")


def _it_loss_blocks(wb, actor: str, scenario: str) -> list[tuple]:
    if "IT CALC - Consequence" not in wb.sheetnames:
        return []
    src = wb["IT CALC - Consequence"]
    p50 = defaultdict(float)
    p99 = defaultdict(float)
    for r in range(16, (src.max_row or 16) + 1):
        if str(src.cell(r, 1).value or "").strip() != actor:
            continue
        if str(src.cell(r, 3).value or "").strip() != scenario:
            continue
        applicable = src.cell(r, 8).value
        if applicable in (False, "FALSE", "No", "no", 0):
            continue
        block = str(src.cell(r, 4).value or "").strip() or "Other"
        q = str(src.cell(r, 6).value or "").strip().upper()
        amt = src.cell(r, 7).value
        try:
            amount = float(amt or 0)
        except (TypeError, ValueError):
            continue
        if q == "P50":
            p50[block] += amount
        elif q == "P99":
            p99[block] += amount
    names = sorted(set(p50) | set(p99), key=lambda n: -(p50[n] + p99[n]))
    return [(n, p50[n], p99[n]) for n in names[:8]]


def _write_lists(ws, actors, scenarios) -> None:
    for i, name in enumerate(actors):
        ws.cell(5, 27, None)
        ws.cell(5 + i, 27).value = name
    for i, name in enumerate(scenarios):
        ws.cell(5 + i, 28).value = name
    parent = ws.parent
    existing = {str(n) for n in parent.defined_names}
    if tuple(actors) == IT_ACTORS:
        names = {
            "IT_Dash_Actors": f"'{ws.title}'!$AA$5:$AA${4 + len(actors)}",
            "IT_Dash_Scenarios": f"'{ws.title}'!$AB$5:$AB${4 + len(scenarios)}",
        }
    else:
        names = {
            "OT_Dash_Actors": f"'{ws.title}'!$AA$5:$AA${4 + len(actors)}",
            "OT_Dash_Scenarios": f"'{ws.title}'!$AB$5:$AB${4 + len(scenarios)}",
        }
    from openpyxl.workbook.defined_name import DefinedName
    for name, attr in names.items():
        if name in existing:
            del parent.defined_names[name]
        parent.defined_names.add(DefinedName(name=name, attr_text=attr))


def _apply_dropdown(ws, cell, named_range: str) -> None:
    dv = DataValidation(type="list", formula1=f"{named_range}", allow_blank=False)
    ws.add_data_validation(dv)
    dv.add(cell)


def _cleanup_whatif(wb) -> None:
    ws = wb["00 What-If"]
    _write_cell(ws, 4, 3, "Source")
    _write_cell(ws, 4, 4, "00 COMMON - Engine Results")
    for row in range(21, 24):
        if str(ws.cell(row, 1).value or "").startswith("='OT CALC"):
            for c in range(1, 11):
                _write_cell(ws, row, c, None)


def _fix_risk_transfer(wb, view: str) -> None:
    ws = wb["00 Risk Transfer"]
    basis = (
        '=IF(\'00 COMMON - Run Setup\'!C6="IT",\'IT 08 - Reporting Settings\'!B16,'
        "'00 COMMON - Run Setup'!C9)"
    )
    _write_cell(ws, 4, 2, basis)
    _write_cell(ws, 4, 4, '=IF(\'00 COMMON - Run Setup\'!C6="IT",\'IT 08 - Reporting Settings\'!B18,0)')
    _write_cell(ws, 4, 6, '=IF(\'00 COMMON - Run Setup\'!C6="IT",\'IT 08 - Reporting Settings\'!B17,"TVaR 99")')
    _write_cell(ws, 2, 1, (
        "Indicative financing diagnostics using annual aggregate AAL / VaR / TVaR. "
        "This is not a policy-pricing engine."
    ))
    _write_cell(ws, 8, 1, "SELECTED TAIL METRIC (ANNUAL AGGREGATE)")
    _write_cell(ws, 10, 1, "=F4")
    _write_cell(
        ws,
        10,
        2,
        '=IF(OR(F4="TVaR 95",F4="TVaR 95%"),'
        'IF($B$4="Best Estimate",\'00 COMMON - Output Bridge\'!B17,\'00 COMMON - Output Bridge\'!C17),'
        'IF($B$4="Best Estimate",\'00 COMMON - Output Bridge\'!B19,\'00 COMMON - Output Bridge\'!C19))',
        CURRENCY,
    )
    _write_cell(ws, 11, 1, "Selected TVaR minus illustrative retention")
    _write_cell(ws, 11, 2, "=MAX(B10-$D$4,0)", CURRENCY)
    _write_cell(ws, 11, 3, "Indicative only — not expected insured loss.")
    _write_cell(ws, 12, 2, '=IF($B$4="Best Estimate",\'00 COMMON - Output Bridge\'!B20,\'00 COMMON - Output Bridge\'!C20)', PCT)
    _write_cell(ws, 15, 1, "ANNUAL AGGREGATE LOSS EXCEEDANCE (AEP)")
    _write_cell(ws, 16, 1, "Return period (secondary)")
    _write_cell(ws, 16, 2, "Exceedance probability")
    _write_cell(ws, 16, 3, "AEP loss")
    _write_cell(ws, 16, 4, "Loss above retention")
    for i, row in enumerate(range(17, 27)):
        _write_cell(ws, row, 2, f"='00 COMMON - Output Bridge'!A{43 + i}", PCT)
        _write_cell(
            ws,
            row,
            3,
            '=IF($B$4="Best Estimate",\'00 COMMON - Output Bridge\'!B'
            + str(43 + i)
            + ",'00 COMMON - Output Bridge'!D"
            + str(43 + i)
            + ")",
            CURRENCY,
        )
        _write_cell(ws, row, 4, f"=MAX(C{row}-$D$4,0)", CURRENCY)
    if "00 Dashboard" in wb.sheetnames:
        dash = wb["00 Dashboard"]
        _write_cell(dash, 4, 8, basis)


def _selected_lec(wb, view: str):
    """Return numeric (probability, AEP, OEP) rows for the selected reporting basis."""
    br = wb["00 COMMON - Output Bridge"]
    probs, aep, oep = [], [], []
    aep_col = 2 if view == "Best Estimate" else 4
    oep_col = 3 if view == "Best Estimate" else 5
    for r in range(43, 54):
        prob = br.cell(r, 1).value
        if prob in (None, ""):
            continue
        probs.append(float(prob))
        aep.append(float(br.cell(r, aep_col).value or 0))
        oep.append(float(br.cell(r, oep_col).value or 0))
    return probs, aep, oep


def _aal_pairs(wb, name_col, val_col, start, n):
    br = wb["00 COMMON - Output Bridge"]
    names, vals = [], []
    view = str(wb["00 COMMON - Run Setup"]["C9"].value or "Prudent")
    vcol = 2 if view == "Best Estimate" else 3
    for i in range(n):
        name = br.cell(start + i, 1).value
        if not name or str(name).startswith("="):
            continue
        names.append(str(name))
        vals.append(float(br.cell(start + i, vcol).value or 0))
    return names, vals


def _exceedance_axis_max(p_max: float) -> float:
    p_max = float(p_max or 0.0)
    if p_max <= 0:
        return 1.0
    snapped = math.ceil((p_max * 1.1) / 0.05) * 0.05
    return float(min(1.0, max(snapped, 0.05)))


def _style_lec_series(series, color: str) -> None:
    series.marker = Marker(symbol="none")
    series.graphicalProperties = GraphicalProperties(
        ln=LineProperties(w=LEC_LINE_WIDTH, solidFill=color, prstDash="solid")
    )


def _cache_xy_series(series, x_values, y_values, x_fmt=CURRENCY, y_fmt="0.0%") -> None:
    if series.xVal is not None and series.xVal.numRef is not None:
        series.xVal.numRef.numCache = NumData(
            ptCount=len(x_values),
            formatCode=x_fmt,
            pt=[NumVal(idx=i, v=str(float(v or 0))) for i, v in enumerate(x_values)],
        )
    if series.yVal is not None and series.yVal.numRef is not None:
        series.yVal.numRef.numCache = NumData(
            ptCount=len(y_values),
            formatCode=y_fmt,
            pt=[NumVal(idx=i, v=str(float(v or 0))) for i, v in enumerate(y_values)],
        )


def _rebuild_lec_scatter(dash, probs, aep, oep, var95=None, var99=None) -> None:
    """Replace the aggregate LEC chart: Impact on X, exceedance probability on Y."""
    if not probs:
        return
    # Drop pure zero-loss points from the plotted series so the axis focuses on the loss tail.
    plot_probs, plot_aep, plot_oep = [], [], []
    for p, a, o in zip(probs, aep, oep):
        if float(a or 0) > 0 or float(o or 0) > 0:
            plot_probs.append(p)
            plot_aep.append(a)
            plot_oep.append(o)
    if not plot_probs:
        plot_probs, plot_aep, plot_oep = list(probs), list(aep), list(oep)

    # Write filtered series into columns E–G (chart source) while A–C retain full bridge copy.
    _write_cell(dash, 13, 5, "Plot P")
    _write_cell(dash, 13, 6, "Plot AEP")
    _write_cell(dash, 13, 7, "Plot OEP")
    for i in range(11):
        row = 14 + i
        if i < len(plot_probs):
            _write_cell(dash, row, 5, plot_probs[i], PCT)
            _write_cell(dash, row, 6, plot_aep[i], CURRENCY)
            _write_cell(dash, row, 7, plot_oep[i], CURRENCY)
        else:
            for c in range(5, 8):
                _write_cell(dash, row, c, None)

    last = 13 + len(plot_probs)
    anchor = dash._charts[0].anchor if dash._charts else None
    chart = ScatterChart()
    chart.title = "Annual Aggregate Loss Exceedance Curve"
    chart.scatterStyle = "lineMarker"
    chart.style = 10
    chart.legend.position = "b"
    chart.x_axis.title = "Annual aggregate loss ($)"
    chart.y_axis.title = "Annual exceedance probability"
    chart.x_axis.axPos = "b"
    chart.x_axis.crosses = "min"
    chart.x_axis.numFmt = NumFmt(formatCode=CURRENCY, sourceLinked=False)
    chart.y_axis.axPos = "l"
    chart.y_axis.crosses = "min"
    y_max = _exceedance_axis_max(max(plot_probs) if plot_probs else max(probs))
    chart.y_axis.scaling.min = 0.0
    chart.y_axis.scaling.max = y_max
    chart.y_axis.numFmt = NumFmt(formatCode="0%", sourceLinked=False)
    if y_max <= 0.2:
        chart.y_axis.majorUnit = 0.05
    elif y_max <= 0.5:
        chart.y_axis.majorUnit = 0.1
    else:
        chart.y_axis.majorUnit = 0.2
    positive_aep = [float(x) for x in plot_aep if float(x or 0) > 0]
    if positive_aep:
        chart.x_axis.scaling.min = min(positive_aep) * 0.85

    y_ref = Reference(dash, min_col=5, min_row=14, max_row=last)
    aep_x = Reference(dash, min_col=6, min_row=14, max_row=last)
    oep_x = Reference(dash, min_col=7, min_row=14, max_row=last)
    aep_series = Series(y_ref, aep_x, title="AEP")
    oep_series = Series(y_ref, oep_x, title="OEP")
    _style_lec_series(aep_series, LEC_AEP_COLOR)
    _style_lec_series(oep_series, LEC_OEP_COLOR)
    chart.series.append(aep_series)
    chart.series.append(oep_series)
    _cache_xy_series(chart.series[0], plot_aep, plot_probs)
    _cache_xy_series(chart.series[1], plot_oep, plot_probs)

    # VaR marker points (single-point series) — rows 40–41 keep clear of LEC plot block
    _write_cell(dash, 40, 5, "VaR marker P")
    _write_cell(dash, 40, 6, "VaR loss $")
    if var95 is not None:
        _write_cell(dash, 41, 5, 0.05, PCT)
        _write_cell(dash, 41, 6, float(var95), CURRENCY)
        var95_series = Series(
            Reference(dash, min_col=5, min_row=41, max_row=41),
            Reference(dash, min_col=6, min_row=41, max_row=41),
            title=f"VaR 95 (${float(var95):,.0f})",
        )
        var95_series.marker = Marker(symbol="diamond", size=10)
        var95_series.graphicalProperties = GraphicalProperties(
            ln=LineProperties(w=1, solidFill="FFFFFF", prstDash="solid")
        )
        chart.series.append(var95_series)
        _cache_xy_series(chart.series[-1], [float(var95)], [0.05])
    if var99 is not None:
        _write_cell(dash, 42, 5, 0.01, PCT)
        _write_cell(dash, 42, 6, float(var99), CURRENCY)
        var99_series = Series(
            Reference(dash, min_col=5, min_row=42, max_row=42),
            Reference(dash, min_col=6, min_row=42, max_row=42),
            title=f"VaR 99 (${float(var99):,.0f})",
        )
        var99_series.marker = Marker(symbol="triangle", size=10)
        var99_series.graphicalProperties = GraphicalProperties(
            ln=LineProperties(w=1, solidFill="FFFFFF", prstDash="solid")
        )
        chart.series.append(var99_series)
        _cache_xy_series(chart.series[-1], [float(var99)], [0.01])

    if anchor is not None:
        chart.anchor = anchor
    if dash._charts:
        dash._charts[0] = chart
    else:
        dash.add_chart(chart, "E13")


def _refresh_chart_caches(wb, view: str, result: dict | None = None) -> None:
    probs, aep, oep = _selected_lec(wb, view)
    dash = wb["00 Dashboard"]
    result = result or {}
    pick = "best" if view == "Best Estimate" else "prudent"
    var95 = result.get(f"{pick}_var95")
    var99 = result.get(f"{pick}_var99")
    _rebuild_lec_scatter(dash, probs, aep, oep, var95=var95, var99=var99)

    if dash._charts:
        actor_names, actor_vals = _aal_pairs(wb, 1, 2, 27, 4)
        if len(dash._charts) > 1 and actor_names:
            ch = dash._charts[1]
            if ch.series:
                ch.series[0].val.numRef.f = "'00 Dashboard'!$B$31:$B$34"
                ch.series[0].cat.strRef.f = "'00 Dashboard'!$A$31:$A$34"
                _cache_series(ch.series[0], actor_names, actor_vals)
        scen_names, scen_vals = _aal_pairs(wb, 1, 2, 34, 4)
        if len(dash._charts) > 2 and scen_names:
            ch = dash._charts[2]
            if ch.series:
                last = 30 + len(scen_names)
                ch.series[0].val.numRef.f = f"'00 Dashboard'!$J$31:$J${last}"
                ch.series[0].cat.strRef.f = f"'00 Dashboard'!$I$31:$I${last}"
                _cache_series(ch.series[0], scen_names, scen_vals)

    loss = wb["00 Loss Analysis"]
    if loss._charts:
        names = [loss.cell(r, 1).value for r in range(16, 18) if loss.cell(r, 1).value]
        p50 = [
            float(loss.cell(r, 2).value or 0)
            if not str(loss.cell(r, 2).value or "").startswith("=")
            else 0
            for r in range(16, 16 + len(names))
        ]
        p99 = [
            float(loss.cell(r, 3).value or 0)
            if not str(loss.cell(r, 3).value or "").startswith("=")
            else 0
            for r in range(16, 16 + len(names))
        ]
        if names and len(loss._charts[0].series) >= 2:
            last = 15 + len(names)
            loss._charts[0].series[0].val.numRef.f = f"'00 Loss Analysis'!$B$16:$B${last}"
            loss._charts[0].series[1].val.numRef.f = f"'00 Loss Analysis'!$C$16:$C${last}"
            _cache_series(loss._charts[0].series[0], names, p50)
            _cache_series(loss._charts[0].series[1], names, p99)

    transfer = wb["00 Risk Transfer"]
    if transfer._charts and probs:
        ch = transfer._charts[0]
        aep_col = 2 if view == "Best Estimate" else 4
        br = wb["00 COMMON - Output Bridge"]
        aep_vals = [float(br.cell(r, aep_col).value or 0) for r in range(43, 43 + len(probs))]
        periods = [str(transfer.cell(r, 1).value) for r in range(17, 17 + len(probs))]
        if ch.series:
            _cache_series(ch.series[-1] if len(ch.series) > 2 else ch.series[0], periods, aep_vals)


def _cache_series(series, cats, values) -> None:
    if series.val is not None and series.val.numRef is not None:
        series.val.numRef.numCache = NumData(
            ptCount=len(values),
            formatCode=CURRENCY,
            pt=[NumVal(idx=i, v=str(float(v or 0))) for i, v in enumerate(values)],
        )
    cat_src = series.cat
    if cat_src is not None and cat_src.strRef is not None:
        cat_src.strRef.strCache = StrData(
            ptCount=len(cats),
            pt=[StrVal(idx=i, v=str(c)) for i, c in enumerate(cats)],
        )
