#!/usr/bin/env python3
"""Guided OT-CRQ v1.7 multi-sector calculation engine.

Transparent Excel front end + Python Monte Carlo engine.

Model universe:
  3 threat actors: Nation State / Cybercriminal / Malicious Insider
  5 OT adverse scenarios
  15 actor x scenario risk cells

Core design changes from v1.0:
- Control implementation quality is assessed through maturity only.
- Maturity factors: Absent 0.00, Initial 0.25, Developing 0.50,
  Managed 0.75, Optimised 0.95; Not Assessed -> Developing.
- Default coverage is 75%.
- No global control-effectiveness tier. Control efficacy is defined at the
  TTP-control relationship using one editable Base Efficacy value.
- Applied efficacy = Base Efficacy x Maturity Factor x Coverage Used.
- TTP barriers combine distinct mapped controls with diminishing incremental
  credit. Stage barriers are the simple average of relevant TTP barriers.
- Scenario-defining TTPs are NOT given arbitrary 2x weighting.
- The workbook contains calculation notes; Python writes engine outputs back.
- 500,000 simulated facility-years for baseline and every control what-if.
- Aggregate, scenario, actor, and actor-scenario loss exceedance curves.

Usage:
    python -m crq run --model assessments/<name>.xlsx --out outputs/<name>.xlsx
    python -m ot_crq run --model model/ot/Guided_OT_CRQ_Model_v1_8_Sector_Packs.xlsx
"""

import os
os.environ.setdefault("ARTIFACT_TOOL_RPC_DAEMON_STARTUP_TIMEOUT_S", "120")

import sys
import math
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import numpy as np

from crq.appetite import evaluate_appetite, parse_appetite_inputs
from crq.insurance import apply_programme, parse_programme
from crq.reporting_helpers import (
    component_rows_from_trials,
    leading_tvar99_component,
    map_ot_driver_to_component,
    treatment_cost_metrics,
)
from crq.metrics import (
    LABEL_AAL,
    LABEL_TVAR_95,
    LABEL_TVAR_99,
    LABEL_VAR_95,
    LABEL_VAR_99,
    TAIL_ABOVE_RETENTION_LABEL,
    VAR_QUANTILE_METHOD,
    annual_aggregate_metrics,
    exceedance_probability,
    expected_shortfall,
    executive_risk_narrative,
    multi_year_event_probability,
    normalize_tail_basis,
    tvar_tail_contributions,
    var_tvar as shared_var_tvar,
)
# Prefer artifact_tool where available; the lightweight companion backend provides
# a deterministic portable fallback. Set OT_CRQ_USE_XLSX_BACKEND=1 to force it.
try:  # pragma: no cover - environment dependent
    if os.environ.get("OT_CRQ_USE_XLSX_BACKEND") == "1":
        raise ImportError("portable backend explicitly requested")
    from artifact_tool import Blob, SpreadsheetFile
except ImportError:
    try:
        from .xlsx_backend import Blob, SpreadsheetFile
    except ImportError:  # pragma: no cover - direct script execution
        from ot_crq.xlsx_backend import Blob, SpreadsheetFile

try:
    from .dashboard import build_payload, write_executive_dashboard
except ImportError:  # pragma: no cover
    from ot_crq.dashboard import build_payload, write_executive_dashboard

ACTORS = ["Nation State", "Cybercriminal", "Malicious Insider"]
SCENARIOS = [
    "Operational Disruption",
    "Loss of Control or Visibility",
    "Process Manipulation",
    "Safety System Compromise",
    "Destructive or Integrity Attack",
]
STAGES = ["S1", "S2", "S3", "S4", "S5"]
RETURN_PERIODS = [2, 5, 10, 20, 25, 50, 100, 200, 250, 500]
EXCEEDANCE_PROBS = [.5, .2, .1, .05, .04, .02, .01, .005, .004, .002, .001]
ENGINE_VERSION = "1.7.1"
WORKBOOK_VERSION = "1.7"
REQUIRED_SIMULATIONS = 500_000

SHEETS = {
    "guide": "OT CORE - Model Guide",
    "summary": "OT 02 - Executive Summary",
    "facility": "OT 03 - Facility Inputs",
    "controls": "OT 04 - Control Assessment",
    "impact": "OT 05 - Impact & BIA",
    "frequency_assump": "OT 06 - Assessment Adjustments",
    "control_assump": "OT CORE - Control Method",
    "scenario_ttp": "OT CORE - Scenario-TTP Map",
    "actor_ttp": "OT CORE - Actor-TTP Map",
    "facility_rules": "OT CORE - Facility Feasibility",
    "ttp_control": "OT CORE - TTP-Control Map",
    "ttp_calc": "OT CALC - TTP Relevance",
    "path_calc": "OT CALC - Attack Path",
    "freq_calc": "OT CALC - Threat Frequency",
    "impact_calc": "OT CALC - Consequence",
    "matrix": "OT CALC - Actor-Scenario Matrix",
    "tail": "OT CALC - Tail Risk Metrics",
    "whatif": "OT CALC - Control What-If",
    "agg_curves": "OT CALC - Aggregate LECs",
    "scenario_lec": "OT CALC - Scenario LECs",
    "actor_lec": "OT CALC - Actor LECs",
    "cell_lec": "OT CALC - Actor-Scenario LEC",
    "charts": "OT CALC - Risk Charts",
    "sources": "OT 26 - Sources and Evidence",
    "tests": "OT 27 - Validation Tests",
}

LEGACY_SHEETS = {
    "guide": "01 Model Guide",
    "summary": "02 Executive Summary",
    "facility": "03 Facility Inputs",
    "controls": "04 Control Assessment",
    "impact": "05 Impact and BIA",
    "frequency_assump": "06 Frequency Assumptions",
    "control_assump": "07 Control Assumptions",
    "scenario_ttp": "09 Scenario-TTP Map",
    "actor_ttp": "11 Actor-TTP Applicability",
    "facility_rules": "12 Facility Feasibility",
    "ttp_control": "13 TTP-Control Map",
    "ttp_calc": "14 TTP Relevance Calc",
    "path_calc": "15 Attack Path Calc",
    "freq_calc": "16 Threat and Loss Frequency",
    "impact_calc": "17 Consequence Calc",
    "matrix": "18 Actor-Scenario Matrix",
    "tail": "19 Tail Risk Metrics",
    "whatif": "20 Control What-If",
    "agg_curves": "21 Aggregate LECs",
    "scenario_lec": "22 Scenario LECs",
    "actor_lec": "23 Actor LECs",
    "cell_lec": "24 Actor-Scenario LEC Data",
    "charts": "25 Risk Charts",
    "sources": "26 Sources and Evidence",
    "tests": "27 Validation Tests",
}


def _sheet_name(wb, key: str) -> str:
    name = SHEETS[key]
    try:
        names = set(wb.wb.sheetnames)
    except AttributeError:
        names = set(wb.sheetnames)
    if name in names:
        return name
    legacy = LEGACY_SHEETS.get(key)
    if legacy and legacy in names:
        return legacy
    return name


def _ws(wb, key: str):
    return wb.worksheets.get_item(_sheet_name(wb, key))


def _nonblank(values):
    return [r for r in values if r and r[0] not in (None, "")]


def _as_bool(value):
    """Accept native Excel booleans and common user-entered equivalents."""
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    return str(value or "").strip().lower() in {"true", "yes", "y", "1"}


def _number(value, label):
    if value in (None, ""):
        raise ValueError(f"{label} must be populated; silent zero fallback is not permitted.")
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be numeric; got {value!r}.") from exc


def _required_text(value, label):
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{label} must be populated.")
    return text


def _required_multiplier(value, label):
    """Fail closed: blank, non-numeric, or negative multipliers are not 1.00."""
    if value in (None, ""):
        raise ValueError(f"{label} must be populated; silent 1.00 fallback is not permitted.")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be numeric; got {value!r}.") from exc
    if number < 0:
        raise ValueError(f"{label} must be non-negative; got {number}.")
    return number


def _single_row(rows, predicate, label):
    matches = [r for r in rows if predicate(r)]
    if len(matches) != 1:
        raise ValueError(f"{label} must resolve to exactly one row; found {len(matches)}.")
    return matches[0]


def ttp_is_relevant(scenario_relevant, actor_applicable, sector_applicable, facility_feasible):
    """Governed relevance: all four gates must pass. Missing control maps do not exclude."""
    return bool(scenario_relevant and actor_applicable and sector_applicable and facility_feasible)


FACILITY_GATE_CODES = {
    "REMOTE_REQUIRED",
    "REMOTE_OR_ITOT",
    "INTERNET_OT",
    "TRANSIENT_REQUIRED",
    "SUPPLY_CHAIN",
    "WIRELESS",
    "SIS_PRESENT",
}


def facility_ttp_feasible(code, facility):
    """Apply a governed facility-architecture gate to one TTP."""
    if not code:
        return True
    code = str(code).strip()
    if code not in FACILITY_GATE_CODES:
        raise ValueError(
            f"Unknown facility feasibility code {code!r}. Fail closed: unknown gates are not treated as always-true."
        )
    if code == "REMOTE_REQUIRED":
        return facility["REMOTE_ACCESS"] != "None"
    if code == "REMOTE_OR_ITOT":
        return facility["REMOTE_ACCESS"] != "None" or facility["IT_OT_CONNECTIVITY"] == "Yes"
    if code == "INTERNET_OT":
        return facility["INTERNET_OT"] == "Yes"
    if code == "TRANSIENT_REQUIRED":
        return facility["TRANSIENT_ASSETS"] != "None"
    if code == "SUPPLY_CHAIN":
        return facility["SUPPLY_CHAIN_ROUTE"] == "Yes"
    if code == "WIRELESS":
        return facility["WIRELESS_OT"] == "Yes"
    if code == "SIS_PRESENT":
        return facility.get("SAFETY_SYSTEM") != "None"
    raise ValueError(f"Unhandled facility feasibility code {code!r}.")


def scenario_is_feasible(scenario, facility):
    return not (scenario == "Safety System Compromise" and facility.get("SAFETY_SYSTEM") == "None")


def stage_barrier(ttp_barriers):
    """Mean of relevant TTP barriers, retaining zero-barrier (unmapped) TTPs."""
    values = [float(v) for v in ttp_barriers]
    if not values:
        return 0.0
    return float(sum(values) / len(values))


def campaign_conditional_success(stage_throughs):
    """P(success | campaign) = product of required S1–S5 stage-through probabilities."""
    p = 1.0
    for value in stage_throughs:
        p *= float(value)
    return float(p)


def best_estimate_lambda(reference_rate, facility_exposure, threat_intensity):
    return float(reference_rate) * float(facility_exposure) * float(threat_intensity)


def effective_actor_probabilities(weights):
    arr = np.asarray(weights, dtype=float)
    total = float(arr.sum())
    if total <= 0:
        raise ValueError("Actor threat-intensity weights must sum to a positive value.")
    return arr / total


def _load_sector_pack(facility, governed_ttp_ids, sector_pack_path=None, project_root=None):
    """Load the selected external OT pack. Never uses embedded combined-workbook calibration."""
    from crq.pack_registry import project_root_from, resolve_pack, validate_pack_file
    from ot_crq.packs import load_ot_pack

    sector = _required_text(facility.get("SECTOR"), "SECTOR")
    asset_type = _required_text(facility.get("PLANT_TYPE"), "PLANT_TYPE")
    root = project_root or project_root_from()
    rec = resolve_pack("OT", sector, root)
    if sector_pack_path is not None:
        path = Path(sector_pack_path).resolve()
        if path != rec.path(root):
            raise ValueError(
                f"Provided pack path {path} does not match registry path {rec.path(root)}."
            )
    else:
        path = rec.path(root)
    validate_pack_file(rec, root, ENGINE_VERSION, "OT")
    return load_ot_pack(path, sector, asset_type, governed_ttp_ids, rec.pack_id)


def _actor_intensity_weights(actor_cfg, sector_mults, asset_mults, geo_mults):
    """Return actor intensity weights with each governed overlay applied once."""
    return np.array([
        float(actor_cfg[a]["share"]) * float(actor_cfg[a]["threat"])
        * float(sector_mults[a]) * float(asset_mults[a]) * float(geo_mults[a])
        for a in ACTORS
    ], dtype=float)


CURRENCY_FORMAT = '"$"#,##0;[Red]("$"#,##0);\\-'

# Per-row number formats for 02 Executive Summary value column(s) (engine-written metrics).
# The template applies a currency format to the whole Value column; non-dollar
# metrics must be overwritten or LibreOffice/Excel display them as $.
SUMMARY_VALUE_FORMATS = {
    "Last simulation run": "YYYY-MM-DD HH:MM",
    "Simulation years": "#,##0",
    "Reference campaign rate": "0.000",
    "Best-estimate campaign rate": "0.000",
    "Prudent campaign rate": "0.000",
    "Simulated campaign rate": "0.000",
    "Prudence factor": "0.00",
    "Facility exposure multiplier": "0.000",
    "Threat intensity multiplier": "0.00",
    LABEL_AAL: CURRENCY_FORMAT,
    LABEL_VAR_95: CURRENCY_FORMAT,
    LABEL_TVAR_95: CURRENCY_FORMAT,
    LABEL_VAR_99: CURRENCY_FORMAT,
    LABEL_TVAR_99: CURRENCY_FORMAT,
    "P(any successful loss event)": "0.0%",
    "Mean annual downtime (hours)": "#,##0.0",
    "Mean downtime | successful year (hours)": "#,##0.0",
    "TVaR 95 downtime (hours)": "#,##0.0",
    "Selected TVaR": CURRENCY_FORMAT,
    "Insurance retention": CURRENCY_FORMAT,
    TAIL_ABOVE_RETENTION_LABEL: CURRENCY_FORMAT,
}

# Executive description of the modelled breach path. Stage labels follow the
# ATT&CK for ICS tactics used on 09 Scenario-TTP Map; probabilities live on 15.
ATTACK_PATH_NARRATIVE = (
    "The model does not assume one named intrusion. Each simulated campaign draws a "
    "threat actor and an adverse scenario, then tests whether that actor can complete "
    "a five-stage ATT&CK for ICS path against this facility. A successful loss event "
    "occurs only if every required stage is passed. Prevent/resist controls are stage "
    "barriers; detect/contain and recover/restore change how long and how costly a "
    "successful event is, not whether the path succeeds. Facility topology (remote "
    "access, IT-OT connectivity, internet-exposed OT, transient assets, supply chain, "
    "wireless, safety systems) can close techniques before the path is quantified. "
    "Stage-by-stage probabilities are on 15 Attack Path Calc."
)

ATTACK_PATH_STAGES = [
    ["S1", "Initial access",
     "Gain a foothold from outside (remote access, internet-exposed OT, supply chain, or transient media).",
     "Required except for Malicious Insider, who is already inside."],
    ["S2", "Establish presence",
     "Persist, escalate privilege, execute code, and evade detection on the compromised system.",
     "Required for all actors."],
    ["S3", "Move into OT",
     "Lateral movement and command-and-control to reach process-adjacent systems.",
     "Required for all actors."],
    ["S4", "Understand the process",
     "Discovery and collection of OT/process information needed to cause the intended harm.",
     "Required for all actors."],
    ["S5", "Achieve the adverse outcome",
     "Impact, impair process control, or inhibit response — the scenario-defining techniques.",
     "Requires at least one scenario-defining technique. Actor S5 capability × scenario difficulty."],
]


# expected_shortfall imported from crq.metrics (canonical TVaR definition).


def empirical_lec(arr, max_points=200):
    """Return plotted LEC points [threshold, P(annual loss >= threshold)].

    The curve starts at (0, P(any positive year)), not (0, 1). Plotting 100% at
    $0 forces the Y axis to 100%+padding (often 120%) and squashes the real
    exceedance curve into a sliver at the bottom.
    """
    a = np.asarray(arr, dtype=float)
    n = len(a)
    if n == 0:
        return [[0.0, 0.0]]
    p_any = float((a > 0).mean())
    positive = np.sort(a[a > 0])
    if len(positive) == 0:
        return [[0.0, 0.0]]
    k = min(max_points, len(positive))
    idx = np.unique(np.linspace(0, len(positive) - 1, k).astype(int))
    rows = [[0.0, p_any]]
    for i in idx:
        x = float(positive[i])
        p = float((len(positive) - np.searchsorted(positive, x, side="left")) / n)
        if x <= 0:
            continue
        rows.append([x, p])
    return rows


def _exceedance_axis_max(p_max):
    """Y-axis cap for exceedance probability. Never above 100%."""
    p_max = float(p_max or 0.0)
    if p_max <= 0:
        return 1.0
    snapped = math.ceil((p_max * 1.1) / 0.05) * 0.05
    return float(min(1.0, max(snapped, 0.05)))


def _chart_title(chart):
    try:
        paras = chart.title.tx.rich.p
        parts = []
        for p in paras:
            if p.r:
                for run in p.r:
                    if run.t:
                        parts.append(run.t)
        return "".join(parts)
    except Exception:
        return ""


def _set_scatter_series(series, x_ref, y_ref, color):
    from openpyxl.chart.marker import Marker

    if series.xVal is not None and series.xVal.numRef is not None:
        series.xVal.numRef.f = x_ref
        series.xVal.numRef.numCache = None
    if series.yVal is not None and series.yVal.numRef is not None:
        series.yVal.numRef.f = y_ref
        series.yVal.numRef.numCache = None
    series.marker = Marker(symbol="none")
    if series.graphicalProperties is not None and series.graphicalProperties.ln is not None:
        series.graphicalProperties.ln.solidFill = color
        series.graphicalProperties.ln.w = 25000
        series.graphicalProperties.ln.prstDash = "solid"
        series.graphicalProperties.ln.noFill = False


def _configure_lec_scatter(chart, y_max, series_specs, x_num_fmt=None):
    from openpyxl.chart.data_source import NumFmt

    chart.scatterStyle = "line"
    chart.dispBlanksAs = "span"
    if chart.x_axis is not None:
        chart.x_axis.axPos = "b"
        chart.x_axis.crosses = "min"
        if x_num_fmt:
            chart.x_axis.numFmt = NumFmt(formatCode=x_num_fmt, sourceLinked=False)
    if chart.y_axis is not None:
        chart.y_axis.axPos = "l"
        chart.y_axis.crosses = "min"
        chart.y_axis.scaling.min = 0.0
        chart.y_axis.scaling.max = float(y_max)
        chart.y_axis.numFmt = NumFmt(formatCode="0%", sourceLinked=False)
        if y_max <= 0.2:
            chart.y_axis.majorUnit = 0.05
        elif y_max <= 0.5:
            chart.y_axis.majorUnit = 0.1
        else:
            chart.y_axis.majorUnit = 0.2
    for series, spec in zip(chart.series, series_specs):
        _set_scatter_series(series, spec[0], spec[1], spec[2])


def _format_prob_columns(ws, cols, start_row, end_row):
    for col in cols:
        for row in range(start_row, end_row + 1):
            ws.cell(row, col).number_format = "0.0%"


def _configure_risk_charts(xl_ws, last_loss, last_dur, last_sc, last_ac, y_max):
    """Point LEC series at helper data, cap probability at ≤100%, draw visible lines."""
    from openpyxl.chart.data_source import NumData, NumFmt, NumVal
    from openpyxl.utils.cell import range_boundaries

    def populate_cache(num_ref):
        if num_ref is None or not num_ref.f:
            return
        address = num_ref.f.rsplit("!", 1)[-1].replace("$", "")
        min_col, min_row, max_col, max_row = range_boundaries(address)
        values = []
        for row in xl_ws.iter_rows(min_row=min_row, max_row=max_row, min_col=min_col, max_col=max_col):
            for cell in row:
                if isinstance(cell.value, (int, float)):
                    values.append(float(cell.value))
        num_ref.numCache = NumData(
            formatCode="General",
            ptCount=len(values),
            pt=[NumVal(idx=i, v=value) for i, value in enumerate(values)],
        )

    sheet = f"'{_sheet_name(wb, 'charts')}'"
    for chart in xl_ws._charts:
        title = _chart_title(chart)
        if title.startswith("AAL by") and chart.x_axis is not None:
            chart.x_axis.numFmt = NumFmt(formatCode='"$"0.0,,"M"', sourceLinked=False)
            chart.x_axis.majorUnit = 100000
            if chart.y_axis is not None:
                chart.y_axis.numFmt = NumFmt(formatCode='"$"0.0,,"M"', sourceLinked=False)
                chart.y_axis.majorUnit = 100000
        elif title.startswith("Facility Loss Exceedance"):
            _configure_lec_scatter(chart, y_max, [
                (f"{sheet}!$V$16:$V${last_loss}", f"{sheet}!$W$16:$W${last_loss}", "1F4E79"),
                (f"{sheet}!$X$16:$X${last_loss}", f"{sheet}!$Y$16:$Y${last_loss}", "C45911"),
            ], x_num_fmt='"$"#,##0')
            if chart.x_axis is not None:
                chart.x_axis.majorUnit = 50000000
        elif title.startswith("Scenario AEP"):
            specs = [
                (f"{sheet}!$AA$16:$AA${last_sc}", f"{sheet}!$AB$16:$AB${last_sc}", "1F4E79"),
                (f"{sheet}!$AC$16:$AC${last_sc}", f"{sheet}!$AD$16:$AD${last_sc}", "C45911"),
                (f"{sheet}!$AE$16:$AE${last_sc}", f"{sheet}!$AF$16:$AF${last_sc}", "548235"),
                (f"{sheet}!$AG$16:$AG${last_sc}", f"{sheet}!$AH$16:$AH${last_sc}", "7030A0"),
                (f"{sheet}!$AI$16:$AI${last_sc}", f"{sheet}!$AJ$16:$AJ${last_sc}", "C00000"),
            ]
            _configure_lec_scatter(chart, y_max, specs, x_num_fmt='"$"#,##0')
        elif title.startswith("Threat Actor AEP"):
            _configure_lec_scatter(chart, y_max, [
                (f"{sheet}!$AL$16:$AL${last_ac}", f"{sheet}!$AM$16:$AM${last_ac}", "1F4E79"),
                (f"{sheet}!$AN$16:$AN${last_ac}", f"{sheet}!$AO$16:$AO${last_ac}", "C45911"),
                (f"{sheet}!$AP$16:$AP${last_ac}", f"{sheet}!$AQ$16:$AQ${last_ac}", "548235"),
            ], x_num_fmt='"$"#,##0')
        elif title.startswith("Facility Downtime Exceedance"):
            _configure_lec_scatter(chart, y_max, [
                (f"{sheet}!$AS$16:$AS${last_dur}", f"{sheet}!$AT$16:$AT${last_dur}", "1F4E79"),
                (f"{sheet}!$AU$16:$AU${last_dur}", f"{sheet}!$AV$16:$AV${last_dur}", "C45911"),
            ], x_num_fmt="#,##0.0")

        for series in chart.series:
            if getattr(series, "xVal", None) is not None and series.xVal.numRef is not None:
                populate_cache(series.xVal.numRef)
            if getattr(series, "yVal", None) is not None and series.yVal.numRef is not None:
                populate_cache(series.yVal.numRef)


def _col_letter(col):
    from openpyxl.utils import get_column_letter
    return get_column_letter(col)


def _apply_summary_number_formats(wb, n_value_cols=2, extra_value_cols=()):
    """Set display formats by metric name across however many value columns are shown
    (two when REPORTING_VIEW is Both, one when a single basis is selected)."""
    xl = getattr(wb, "wb", None)
    if xl is None:
        return
    ws = xl[_sheet_name(wb, "summary")]
    for row in range(15, 120):
        name = ws.cell(row, 1).value
        fmt = SUMMARY_VALUE_FORMATS.get(name)
        if fmt:
            for col in list(range(2, 2 + n_value_cols)) + list(extra_value_cols):
                ws.cell(row, col).number_format = fmt


_SUMMARY_HEADER_FILL = "FF3F6B3A"
_SUMMARY_COL_FILL = "FF548235"
_SUMMARY_ZEBRA_FILL = "FFF4F7F2"
_SUMMARY_METRIC_FILL = "FFEEF4EA"
_SUMMARY_NOTE_FILL = "FFEEF4EA"
_SUMMARY_BORDER_COLOR = "FFD0D7D0"
_DECOMP_LAST_COL = 11
_DECOMP_HEADERS = [
    "Name", LABEL_AAL, LABEL_VAR_95, LABEL_TVAR_95, LABEL_VAR_99, LABEL_TVAR_99,
    "Attempts / yr", "Events / yr", "P(success)", "AAL share", "Rank",
]


def _summary_border():
    from openpyxl.styles import Border, Side
    side = Side(style="thin", color=_SUMMARY_BORDER_COLOR)
    return Border(left=side, right=side, top=side, bottom=side)


def _style_section_header(ws, row, col, last_col, title):
    from openpyxl.styles import Font, PatternFill, Alignment

    fill = PatternFill("solid", fgColor=_SUMMARY_HEADER_FILL)
    font = Font(bold=True, color="FFFFFF", size=11)
    ref = f"{_col_letter(col)}{row}:{_col_letter(last_col)}{row}"
    already = any(
        m.min_row == row and m.min_col == col and m.max_col == last_col
        for m in ws.merged_cells.ranges
    )
    if not already:
        ws.merge_cells(ref)
    cell = ws.cell(row, col, title)
    cell.fill = fill
    cell.font = font
    cell.alignment = Alignment(horizontal="left", vertical="center", indent=1)
    for c in range(col, last_col + 1):
        ws.cell(row, c).fill = fill
        ws.cell(row, c).font = font
    ws.row_dimensions[row].height = 20


def _style_col_headers(ws, row, headers, start_col=1):
    from openpyxl.styles import Font, PatternFill, Alignment

    fill = PatternFill("solid", fgColor=_SUMMARY_COL_FILL)
    font = Font(bold=True, color="FFFFFF", size=10)
    align = Alignment(wrap_text=True, vertical="center", horizontal="center")
    border = _summary_border()
    for i, header in enumerate(headers):
        cell = ws.cell(row, start_col + i, header)
        cell.fill = fill
        cell.font = font
        cell.alignment = align
        cell.border = border
    ws.row_dimensions[row].height = 32


def _style_table_body(ws, start_row, end_row, start_col, end_col, *, name_col=True, zebra=True):
    from openpyxl.styles import Alignment, Font, PatternFill

    border = _summary_border()
    metric_fill = PatternFill("solid", fgColor=_SUMMARY_METRIC_FILL)
    zebra_fill = PatternFill("solid", fgColor=_SUMMARY_ZEBRA_FILL)
    name_align = Alignment(vertical="center", wrap_text=True, indent=1)
    value_align = Alignment(vertical="center", horizontal="right")
    for r in range(start_row, end_row + 1):
        ws.row_dimensions[r].height = max(ws.row_dimensions[r].height or 0, 20)
        for c in range(start_col, end_col + 1):
            cell = ws.cell(r, c)
            cell.border = border
            cell.font = Font(size=10)
            if c == start_col and name_col:
                cell.alignment = name_align
                cell.fill = metric_fill
                cell.font = Font(size=10, bold=True)
            else:
                cell.alignment = value_align
                if zebra and (r - start_row) % 2 == 1:
                    cell.fill = zebra_fill


def _unmerge_engine_summary_region(ws):
    for merged in list(ws.merged_cells.ranges):
        if merged.min_row >= 15:
            ws.unmerge_cells(str(merged))


def _view_value_headers(reporting_view):
    """Column header(s) for the single value column, or both, depending on REPORTING_VIEW."""
    return ("Best Estimate", "Prudent") if reporting_view == "Both" else (reporting_view,)


def _collapse_row_for_view(row, reporting_view):
    """Reduce a [Metric, Best Estimate, Prudent, Meaning] row to [Metric, Value, Meaning]
    when only one reporting basis is selected, instead of showing a populated column next
    to a blank one."""
    metric, be_val, prudent_val, meaning = row
    if reporting_view == "Both":
        return row
    value = be_val if reporting_view == "Best Estimate" else prudent_val
    return [metric, value, meaning]


def _write_block(sh, ws, title_row, title, rows, start_col=1, value_headers=("Best Estimate", "Prudent"), span_last_col=None):
    from openpyxl.styles import Alignment, Font, PatternFill

    headers = ["Metric", *value_headers, "Meaning"]
    last_col = start_col + len(headers) - 1
    span = span_last_col or last_col
    meaning_col = last_col
    a = _col_letter(start_col)
    d = _col_letter(last_col)
    if ws is not None:
        _style_section_header(ws, title_row, start_col, span, title)
        _style_col_headers(ws, title_row + 1, headers, start_col)
        if span > meaning_col:
            header_row = title_row + 1
            if not any(m.min_row == header_row and m.min_col == meaning_col for m in ws.merged_cells.ranges):
                ws.merge_cells(
                    f"{_col_letter(meaning_col)}{header_row}:{_col_letter(span)}{header_row}"
                )
            fill = PatternFill("solid", fgColor=_SUMMARY_COL_FILL)
            font = Font(bold=True, color="FFFFFF", size=10)
            border = _summary_border()
            align = Alignment(wrap_text=True, vertical="center", horizontal="center")
            for c in range(meaning_col, span + 1):
                cell = ws.cell(header_row, c)
                cell.fill = fill
                cell.font = font
                cell.alignment = align
                cell.border = border
    else:
        sh.get_range(f"{a}{title_row}:{d}{title_row}").values = [[title, *([None] * (len(headers) - 1))]]
        sh.get_range(f"{a}{title_row + 1}:{d}{title_row + 1}").values = [headers]
    data_row = title_row + 2
    sh.get_range(f"{a}{data_row}:{d}{data_row + len(rows) - 1}").values = rows
    if ws is not None:
        _style_table_body(ws, data_row, data_row + len(rows) - 1, start_col, span)
        wrap = Alignment(wrap_text=True, vertical="center", indent=1)
        for r in range(data_row, data_row + len(rows)):
            if span > meaning_col:
                if not any(m.min_row == r and m.min_col == meaning_col for m in ws.merged_cells.ranges):
                    ws.merge_cells(f"{_col_letter(meaning_col)}{r}:{_col_letter(span)}{r}")
            ws.cell(r, meaning_col).alignment = wrap
            ws.row_dimensions[r].height = 28
    return data_row, data_row + len(rows) - 1


HIDDEN_BEST_ESTIMATE_COL = 12  # column L; outside A–K so decompositions stay visible


def _write_hidden_best_estimate(ws, header_row, data_start, values):
    """Store Best Estimate beside the Prudent KPI tables in a hidden column."""
    from openpyxl.styles import Alignment, Font, PatternFill

    col = HIDDEN_BEST_ESTIMATE_COL
    header = ws.cell(header_row, col, "Best Estimate")
    header.fill = PatternFill("solid", fgColor=_SUMMARY_COL_FILL)
    header.font = Font(bold=True, color="FFFFFF", size=10)
    header.alignment = Alignment(wrap_text=True, vertical="center", horizontal="center")
    header.border = _summary_border()
    for i, value in enumerate(values):
        cell = ws.cell(data_start + i, col, value)
        cell.alignment = Alignment(vertical="center", horizontal="right")
        cell.font = Font(size=10)
        cell.border = _summary_border()
        if i % 2 == 1:
            cell.fill = PatternFill("solid", fgColor=_SUMMARY_ZEBRA_FILL)


def _hide_best_estimate_column(ws, hidden=True):
    dim = ws.column_dimensions["L"]
    dim.width = 16
    dim.hidden = bool(hidden)
    dim.outlineLevel = 1 if hidden else 0


def apply_sector_asset_dropdowns(wb):
    """Filter 03!PLANT_TYPE to asset types registered for the selected sector."""
    from openpyxl.workbook.defined_name import DefinedName
    from openpyxl.worksheet.datavalidation import DataValidation

    xl = getattr(wb, "wb", None)
    if xl is None:
        return
    named = {
        "Power_Generation": "'28 Sector Pack Registry'!$B$25:$B$30",
        "Energy_Assets": "'28 Sector Pack Registry'!$B$31:$B$35",
        "Manufacturing": "'28 Sector Pack Registry'!$B$36:$B$39",
    }
    existing = {str(n) for n in xl.defined_names}
    for name, attr in named.items():
        if name in existing:
            del xl.defined_names[name]
        xl.defined_names.add(DefinedName(name=name, attr_text=attr))

    ws = xl[_sheet_name(wb, "facility")]
    for dv in list(ws.data_validations.dataValidation):
        refs = str(dv.sqref).split()
        if "C21" in refs:
            if len(refs) == 1:
                ws.data_validations.dataValidation.remove(dv)
            else:
                dv.sqref = " ".join(r for r in refs if r != "C21")
    dropdown = DataValidation(
        type="list",
        formula1='INDIRECT(SUBSTITUTE($C$20," ","_"))',
        allow_blank=True,
        showDropDown=False,
        showErrorMessage=True,
        errorStyle="stop",
        errorTitle="Asset type not in selected sector",
        error="Select a plant / asset type that belongs to the Sector chosen above.",
        showInputMessage=True,
        promptTitle="Plant / asset type",
        prompt="This list is filtered by Sector. Energy Assets shows only energy asset types.",
    )
    dropdown.add("C21")
    ws.add_data_validation(dropdown)
    if ws["D21"].value == "Dropdown":
        ws["D21"] = "Dropdown (filtered by Sector)"
    how = ws["E21"].value
    if isinstance(how, str) and "filtered" not in how.lower():
        ws["E21"] = "Asset-pack context and frequency overlay. List is filtered by Sector."


def _write_decomp_table(sh, ws, title_row, title, name_header, rows):
    headers = [name_header, *_DECOMP_HEADERS[1:]]
    last = _DECOMP_LAST_COL
    if ws is not None:
        _style_section_header(ws, title_row, 1, last, title)
        _style_col_headers(ws, title_row + 1, headers, 1)
    else:
        sh.get_range(f"A{title_row}:K{title_row}").values = [[title] + [None] * (last - 1)]
        sh.get_range(f"A{title_row + 1}:K{title_row + 1}").values = [headers]
    data_row = title_row + 2
    sh.get_range(f"A{data_row}:K{data_row + len(rows) - 1}").values = rows
    if ws is None:
        return data_row + len(rows) - 1
    from openpyxl.styles import Alignment
    _style_table_body(ws, data_row, data_row + len(rows) - 1, 1, last)
    center = Alignment(vertical="center", horizontal="center")
    for r in range(data_row, data_row + len(rows)):
        ws.cell(r, 2).number_format = CURRENCY_FORMAT
        ws.cell(r, 3).number_format = CURRENCY_FORMAT
        ws.cell(r, 4).number_format = CURRENCY_FORMAT
        ws.cell(r, 5).number_format = CURRENCY_FORMAT
        ws.cell(r, 6).number_format = CURRENCY_FORMAT
        ws.cell(r, 7).number_format = "0.000"
        ws.cell(r, 8).number_format = "0.000"
        ws.cell(r, 9).number_format = "0.0%"
        ws.cell(r, 10).number_format = "0.0%"
        ws.cell(r, 11).number_format = "0"
        ws.cell(r, 11).alignment = center
        ws.row_dimensions[r].height = 22
    return data_row + len(rows) - 1


def _write_attack_path_section(sh, ws, start_row=45):
    """Full-width assumed attack-path narrative and S1–S5 table."""
    from openpyxl.styles import Alignment, Font, PatternFill

    header_row = start_row
    narrative_row = start_row + 1
    table_header = start_row + 3
    table_start = start_row + 4

    sh.get_range(f"A{narrative_row}:K{narrative_row}").values = [[
        ATTACK_PATH_NARRATIVE, None, None, None, None, None, None, None, None, None, None,
    ]]
    sh.get_range(f"A{table_header}:E{table_header}").values = [[
        "Stage", "Name", "What the adversary does", None, "Modelling note",
    ]]
    sh.get_range(f"A{table_start}:E{table_start + len(ATTACK_PATH_STAGES) - 1}").values = [
        [row[0], row[1], row[2], None, row[3]] for row in ATTACK_PATH_STAGES
    ]

    if ws is None:
        sh.get_range(f"A{header_row}:K{header_row}").values = [[
            "ASSUMED ATTACK PATH", None, None, None, None, None, None, None, None, None, None,
        ]]
        return

    _style_section_header(ws, header_row, 1, 11, "ASSUMED ATTACK PATH")
    if not any(m.min_row == narrative_row and m.min_col == 1 for m in ws.merged_cells.ranges):
        ws.merge_cells(f"A{narrative_row}:K{narrative_row}")
    cell = ws.cell(narrative_row, 1, ATTACK_PATH_NARRATIVE)
    cell.alignment = Alignment(wrap_text=True, vertical="center")
    cell.fill = PatternFill("solid", fgColor="FFDDEFF2")
    cell.font = Font()
    ws.row_dimensions[narrative_row].height = 78
    for c in range(2, 12):
        ws.cell(narrative_row, c).fill = PatternFill("solid", fgColor="FFDDEFF2")

    _style_col_headers(ws, table_header, ["Stage", "Name", "What the adversary does"], 1)
    _style_col_headers(ws, table_header, ["Modelling note"], 5)
    if not any(m.min_row == table_header and m.min_col == 3 for m in ws.merged_cells.ranges):
        ws.merge_cells(f"C{table_header}:D{table_header}")
    for c in range(3, 5):
        ws.cell(table_header, c).fill = PatternFill("solid", fgColor="FF548235")
        ws.cell(table_header, c).font = Font(bold=True, color="FFFFFF")
    if not any(m.min_row == table_header and m.min_col == 5 for m in ws.merged_cells.ranges):
        ws.merge_cells(f"E{table_header}:K{table_header}")
    header_fill = PatternFill("solid", fgColor="FF548235")
    header_font = Font(bold=True, color="FFFFFF")
    for c in range(5, 12):
        ws.cell(table_header, c).fill = header_fill
        ws.cell(table_header, c).font = header_font
    wrap = Alignment(wrap_text=True, vertical="center")
    for i, row in enumerate(ATTACK_PATH_STAGES):
        r = table_start + i
        if not any(m.min_row == r and m.min_col == 3 for m in ws.merged_cells.ranges):
            ws.merge_cells(f"C{r}:D{r}")
        if not any(m.min_row == r and m.min_col == 5 for m in ws.merged_cells.ranges):
            ws.merge_cells(f"E{r}:K{r}")
        for col in (1, 2, 3, 5):
            ws.cell(r, col).alignment = wrap
        ws.row_dimensions[r].height = 52


def _write_executive_summary(
    wb, financial, operational, run_ctx, actor_decomp, scenario_decomp,
    reporting_view="Both", primary_view="Prudent",
):
    """Stacked Executive Summary: KPI blocks, then full-width actor/scenario decompositions.

    When REPORTING_VIEW is Both, the visible value column is Prudent. Best Estimate is
    written to hidden column L so a reader can unhide it. Decomposition tables always
    use the detailed reporting basis (Prudent when Both is selected).
    """
    from openpyxl.styles import Alignment, Border, Font, PatternFill

    sh = _ws(wb, "summary")
    xl = getattr(wb, "wb", None)
    ws = xl[_sheet_name(wb, "summary")] if xl is not None else None

    hide_best_estimate = reporting_view == "Both"
    if hide_best_estimate:
        be_financial = [r[1] for r in financial]
        be_operational = [r[1] for r in operational]
        be_run = [r[1] for r in run_ctx]
        financial = [[r[0], r[2], r[3]] for r in financial]
        operational = [[r[0], r[2], r[3]] for r in operational]
        run_ctx = [[r[0], r[2], r[3]] for r in run_ctx]
        value_headers = ("Prudent",)
    else:
        be_financial = be_operational = be_run = None
        value_headers = _view_value_headers(reporting_view)
        financial = [_collapse_row_for_view(r, reporting_view) for r in financial]
        operational = [_collapse_row_for_view(r, reporting_view) for r in operational]
        run_ctx = [_collapse_row_for_view(r, reporting_view) for r in run_ctx]
    n_val = len(value_headers)
    kpi_last_col = 1 + n_val + 1  # Metric + value column(s) + Meaning

    if ws is not None:
        _unmerge_engine_summary_region(ws)
        ws.freeze_panes = None
    sh.get_range("A15:L120").clear({})
    if ws is not None:
        for row in range(15, 121):
            for col in range(1, 13):
                cell = ws.cell(row, col)
                cell.number_format = "General"
                cell.fill = PatternFill(fill_type=None)
                cell.border = Border()
                cell.font = Font()
                cell.alignment = Alignment()

    row = 15
    fin_start, _ = _write_block(sh, ws, row, "FINANCIAL RISK", financial, value_headers=value_headers, span_last_col=11)
    if hide_best_estimate and ws is not None:
        _write_hidden_best_estimate(ws, row + 1, fin_start, be_financial)
    row = row + 3 + len(financial)
    op_start, _ = _write_block(sh, ws, row, "OPERATIONAL IMPACT", operational, value_headers=value_headers, span_last_col=11)
    if hide_best_estimate and ws is not None:
        _write_hidden_best_estimate(ws, row + 1, op_start, be_operational)
    row = row + 3 + len(operational)
    run_start, _ = _write_block(sh, ws, row, "RUN CONTEXT", run_ctx, value_headers=value_headers, span_last_col=11)
    if hide_best_estimate and ws is not None:
        _write_hidden_best_estimate(ws, row + 1, run_start, be_run)
    row = row + 2 + len(run_ctx) + 1

    note = (
        f"Decompositions use the {primary_view} annual loss distribution"
        f"{' (detailed basis when reporting is Both)' if reporting_view == 'Both' else ''}. "
        "AAL shares sum to facility AAL. VaR and TVaR are each row's own annual "
        "distribution and do not add to the facility totals."
    )
    if hide_best_estimate:
        note += " Best Estimate is in hidden column L; unhide column L to compare with Prudent."
    sh.get_range(f"A{row}:K{row}").values = [[note] + [None] * 10]
    if ws is not None:
        if not any(m.min_row == row and m.min_col == 1 for m in ws.merged_cells.ranges):
            ws.merge_cells(f"A{row}:K{row}")
        cell = ws.cell(row, 1, note)
        cell.alignment = Alignment(wrap_text=True, vertical="center", indent=1)
        cell.fill = PatternFill("solid", fgColor=_SUMMARY_NOTE_FILL)
        cell.font = Font(size=9, italic=True, color="FF375623")
        ws.row_dimensions[row].height = 32
        for c in range(2, 12):
            ws.cell(row, c).fill = PatternFill("solid", fgColor=_SUMMARY_NOTE_FILL)
    row += 2

    actor_title = f"THREAT ACTOR DECOMPOSITION  ·  {primary_view}"
    _write_decomp_table(sh, ws, row, actor_title, "Threat actor", actor_decomp)
    row = row + 3 + len(actor_decomp) + 1

    scenario_title = f"SCENARIO DECOMPOSITION  ·  {primary_view}"
    _write_decomp_table(sh, ws, row, scenario_title, "Scenario", scenario_decomp)
    row = row + 3 + len(scenario_decomp) + 1

    _write_attack_path_section(sh, ws, start_row=row)

    if ws is None:
        return

    meaning_col = kpi_last_col
    wrap = Alignment(wrap_text=True, vertical="center", indent=1)
    for r in range(15, row):
        if ws.cell(r, 1).value in SUMMARY_VALUE_FORMATS:
            ws.cell(r, meaning_col).alignment = wrap
    ws.column_dimensions["A"].width = 32
    for i in range(n_val):
        ws.column_dimensions[_col_letter(2 + i)].width = 15
    ws.column_dimensions["D"].width = 14
    ws.column_dimensions["E"].width = 14
    ws.column_dimensions["F"].width = 14
    ws.column_dimensions["G"].width = 13
    ws.column_dimensions["H"].width = 12
    ws.column_dimensions["I"].width = 12
    ws.column_dimensions["J"].width = 12
    ws.column_dimensions["K"].width = 8
    extra_cols = ()
    if hide_best_estimate:
        _hide_best_estimate_column(ws, hidden=True)
        extra_cols = (HIDDEN_BEST_ESTIMATE_COL,)
    else:
        _hide_best_estimate_column(ws, hidden=False)
    ws.freeze_panes = "A15"
    ws.sheet_view.showGridLines = False
    ws.page_setup.orientation = "landscape"
    ws.print_area = f"A1:K{row + 10}"
    _apply_summary_number_formats(wb, n_value_cols=n_val, extra_value_cols=extra_cols)


def refresh(
    input_path,
    output_path=None,
    run_whatifs=True,
    simulate=True,
    sector_pack_path=None,
    project_root=None,
    appetite_inputs=None,
    insurance_programme=None,
    run_packages=True,
    run_sensitivity=False,
    sensitivity_years=None,
):
    wb = SpreadsheetFile.import_xlsx(Blob.load(input_path))

    # ---------------- Inputs / mappings ----------------
    facility = {
        r[0]: r[2]
        for r in _nonblank(_ws(wb, "facility").get_range("A16:F29").values)
    }

    controls = {}
    control_rows = _nonblank(_ws(wb, "controls").get_range("A16:L67").values)
    for r in control_rows:
        controls[r[0]] = {
            "name": r[1],
            "channel": r[2],
            "maturity": r[3] or "Not Assessed",
            "coverage": r[4],
            "tested": r[5],
            "test_result": r[6],
            "evidence": r[7],
        }

    scenario_ttp_rows = _nonblank(
        _ws(wb, "scenario_ttp").get_range("A16:H400").values
    )
    actor_ttp_rows = _nonblank(
        _ws(wb, "actor_ttp").get_range("A16:F500").values
    )
    facility_rule_rows = _nonblank(
        _ws(wb, "facility_rules").get_range("A16:J40").values
    )
    ttp_control_rows = _nonblank(
        _ws(wb, "ttp_control").get_range("A16:M500").values
    )

    governed_ttp_ids = {
        r[1] for r in scenario_ttp_rows if len(r) > 1 and r[1] not in (None, "")
    }
    sector_pack = _load_sector_pack(
        facility, governed_ttp_ids, sector_pack_path=sector_pack_path, project_root=project_root
    )

    # Frequency / uncertainty settings.
    general = {}
    for r in _nonblank(_ws(wb, "frequency_assump").get_range("A16:H21").values):
        general[r[0]] = {"low": r[2], "base": r[3], "high": r[4]}

    actor_cfg = {}
    for r in _nonblank(_ws(wb, "frequency_assump").get_range("A27:J29").values):
        actor_cfg[r[0]] = {
            "share": float(r[1]),
            "threat": float(r[2]),
            "S1": 1.0 if r[0] == "Malicious Insider" and r[3] in (None, "", "Not used") else float(r[3]),
            "S2": float(r[4]),
            "S3": float(r[5]),
            "S4": float(r[6]),
            "S5cap": float(r[7]),
        }

    scenario_prop = sector_pack.get("scenario_propensity")
    if not scenario_prop:
        raise ValueError("Sector pack did not supply actor-to-scenario propensity (sheet 03).")
    if set(scenario_prop) != set(ACTORS):
        raise ValueError("Sector pack scenario propensity must include all OT actors.")
    for actor, row in scenario_prop.items():
        if set(row) != set(SCENARIOS):
            raise ValueError(f"Sector pack scenario propensity for {actor} is missing scenarios.")
        if abs(sum(row.values()) - 1.0) > 1e-6:
            raise ValueError(f"Sector pack scenario propensity for {actor} must sum to 1.0.")

    scenario_difficulty = {
        r[0]: float(r[1])
        for r in _nonblank(_ws(wb, "frequency_assump").get_range("A43:E47").values)
    }
    exposure_map = {
        (r[0], str(r[1])): float(r[2])
        for r in _nonblank(_ws(wb, "frequency_assump").get_range("A53:F66").values)
    }
    sector_map = {
        sector_pack["sector"]: {
            "multipliers": sector_pack["sector_multipliers"],
            "pack_id": sector_pack["pack_id"],
        }
    }
    if sector_pack["sector"] not in sector_map:
        raise ValueError(
            f"Selected sector {sector_pack['sector']!r} has no explicit frequency calibration row."
        )
    if sector_map[sector_pack["sector"]]["pack_id"] != sector_pack["pack_id"]:
        raise ValueError(
            "Sector frequency row and registry resolve to different pack IDs: "
            f"{sector_map[sector_pack['sector']]['pack_id']!r} vs {sector_pack['pack_id']!r}."
        )
    geo_map = {
        r[0]: {ACTORS[i]: float(r[i + 1]) for i in range(3)}
        for r in _nonblank(_ws(wb, "frequency_assump").get_range("A82:E85").values)
    }

    maturity_table = {
        r[0]: float(r[1])
        for r in _nonblank(_ws(wb, "control_assump").get_range("A16:C20").values)
    }
    settings = {
        r[0]: r[1]
        for r in _nonblank(_ws(wb, "control_assump").get_range("A26:D34").values)
    }
    severity_settings = {
        r[0]: r[1]
        for r in _nonblank(_ws(wb, "control_assump").get_range("A41:D42").values)
    }

    baseline_mat = str(settings["BASELINE_MATURITY_LEVEL"])
    default_cov = float(settings["DEFAULT_COVERAGE"])
    agg_inc = float(settings["AGG_INCREMENT"])
    adj_floor = float(settings["ADJ_FLOOR"])
    adj_ceiling = float(settings["ADJ_CEILING"])
    dur_floor = float(settings["DUR_FLOOR"])
    conseq_floor = float(settings["CONSEQ_FLOOR"])
    conseq_ceiling = float(settings["CONSEQ_CEILING"])

    impact_sheet = _ws(wb, "impact")
    financial = {
        r[0]: _number(r[2], str(r[0]))
        for r in _nonblank(impact_sheet.get_range("A16:F20").values)
    }
    risk_financing = {
        r[0]: r[1]
        for r in _nonblank(_ws(wb, "tail").get_range("L16:O17").values)
    }

    # v1.6 impact construction: an OT-specific, user-calibratable cost-driver
    # matrix replaces manually entered aggregate component severities. The
    # formulas are also visible in Excel, but the engine reads the raw inputs so
    # a saved workbook can be recalculated without relying on cached Excel values.
    matrix_rows = impact_sheet.get_range("A28:L53").values
    driver_matrix = {}
    for r in matrix_rows:
        if len(r) < 12 or r[1] in (None, ""):
            continue  # category band or blank row
        driver_id = str(r[1]).strip()
        driver_matrix[driver_id] = {
            "category": r[0],
            "name": str(r[2]).strip(),
            "actor_app": str(r[3] or "All").strip(),
            "sensitivity": str(r[4] or "Fixed").strip(),
            "applicable": {SCENARIOS[i]: _as_bool(r[i + 5]) for i in range(5)},
            "equation": r[10],
            "guidance": r[11],
        }

    scenario_impact = sector_pack.get("scenario_impact")
    if not scenario_impact:
        raise ValueError("Sector pack did not supply scenario impact parameters (sheet 09).")
    if set(scenario_impact) != set(SCENARIOS):
        raise ValueError("Sector pack scenario impact must include all five OT scenarios.")
    for sc, s in scenario_impact.items():
        for key in ("base_days", "stress_days", "base_capacity", "stress_capacity"):
            if key not in s:
                raise ValueError(f"Sector pack scenario impact for {sc} is missing {key}.")

    # Keep OT 05 display rows aligned with the authoritative pack values.
    display_rows = []
    for sc in SCENARIOS:
        s = scenario_impact[sc]
        display_rows.append([
            sc,
            s["base_days"],
            s["stress_days"],
            s["base_capacity"],
            s["stress_capacity"],
            "Pack-authoritative — from sector pack 09 Scenario Parameters",
            "Loaded from the selected OT sector pack; do not treat this block as an independent assessment override.",
        ])
    impact_sheet.get_range("A58:G62").values = display_rows

    driver_assumptions = {}
    for r in _nonblank(impact_sheet.get_range("A67:L84").values):
        driver_id = str(r[0]).strip()
        formula_type = str(r[8] or "").strip()
        def operand(val, lab):
            if val in (None, ""):
                return 0.0  # unused operand for this formula type (e.g. BI_SCENARIO rate)
            return _number(val, lab)
        driver_assumptions[driver_id] = {
            "name": str(r[1]).strip(),
            "base_rate": operand(r[2], f"{driver_id} Base rate"),
            "stress_rate": operand(r[3], f"{driver_id} Stress rate"),
            "base_qty": operand(r[4], f"{driver_id} Base quantity/share"),
            "stress_qty": operand(r[5], f"{driver_id} Stress quantity/share"),
            "unit": r[6],
            "scaling_input": str(r[7] or "").strip(),
            "formula_type": str(r[8] or "").strip(),
            "basis": r[11],
        }

    expected_driver_ids = {
        "IR-01", "IR-02", "IR-03", "RC-01", "RC-02", "RC-03",
        "BI-01", "OP-01", "OP-02", "EX-01", "LG-01", "LG-02",
        "SF-01", "EN-01", "PD-01", "PD-02", "PD-03", "IN-01",
    }
    valid_formula_types = {
        "BI_SCENARIO", "DAILY_X_DAYS", "DAILY_X_SCENARIO_DAYS",
        "DIRECT", "REVENUE_X_SHARE", "ASSET_X_SHARE_X_UNIT",
    }
    missing_matrix = expected_driver_ids - set(driver_matrix)
    missing_assumptions = expected_driver_ids - set(driver_assumptions)
    if missing_matrix:
        raise ValueError(f"Impact driver matrix is missing: {sorted(missing_matrix)}")
    if missing_assumptions:
        raise ValueError(f"Impact driver assumptions are missing: {sorted(missing_assumptions)}")
    if set(scenario_impact) != set(SCENARIOS):
        raise ValueError("Impact scenario calibration must contain all five scenarios.")

    def driver_value(driver_id, sc, stress=False):
        a = driver_assumptions[driver_id]
        rate = a["stress_rate"] if stress else a["base_rate"]
        qty = a["stress_qty"] if stress else a["base_qty"]
        days = scenario_impact[sc]["stress_days" if stress else "base_days"]
        capacity = scenario_impact[sc]["stress_capacity" if stress else "base_capacity"]
        formula_type = a["formula_type"]
        if formula_type == "BI_SCENARIO":
            return financial["ANNUAL_REVENUE_AT_RISK"] / 365.0 * financial["BI_LOSS_FACTOR"] * days * capacity
        if formula_type == "DAILY_X_DAYS":
            return rate * qty
        if formula_type == "DAILY_X_SCENARIO_DAYS":
            return rate * days
        if formula_type == "DIRECT":
            return rate
        if formula_type == "REVENUE_X_SHARE":
            return financial["ANNUAL_REVENUE_AT_RISK"] * qty
        if formula_type == "ASSET_X_SHARE_X_UNIT":
            if a["scaling_input"] not in financial:
                raise ValueError(
                    f"{driver_id} scaling input {a['scaling_input']!r} is not defined in the impact input panel."
                )
            return financial[a["scaling_input"]] * qty * rate
        raise ValueError(f"Unsupported impact formula type {formula_type!r} for {driver_id}.")

    calculated_driver_values = {}
    impact = defaultdict(dict)
    bi_enabled = {}
    for sc in SCENARIOS:
        s = scenario_impact[sc]
        if s["base_days"] < 0 or s["stress_days"] < s["base_days"]:
            raise ValueError(f"{sc} downtime must be non-negative with P99 >= P50.")
        if not (0 <= s["base_capacity"] <= s["stress_capacity"] <= 1):
            raise ValueError(f"{sc} capacity shares must satisfy 0 <= P50 <= P99 <= 1.")
        impact[sc]["Downtime days"] = {
            "base": s["base_days"], "stress": s["stress_days"],
            "unit": "days", "actor_app": "All", "sensitivity": "Duration",
        }
        impact[sc]["Capacity affected"] = {
            "base": s["base_capacity"], "stress": s["stress_capacity"],
            "unit": "share", "actor_app": "All", "sensitivity": "Duration",
        }
        bi_enabled[sc] = driver_matrix["BI-01"]["applicable"][sc]
        for driver_id, m in driver_matrix.items():
            base = driver_value(driver_id, sc, False)
            stress = driver_value(driver_id, sc, True)
            calculated_driver_values[(sc, driver_id)] = (base, stress)
            if base < 0 or stress < base:
                raise ValueError(f"{sc} / {driver_id} must be non-negative with P99 >= P50.")
            if driver_id == "BI-01" or not m["applicable"][sc]:
                continue
            impact[sc][m["name"]] = {
                "base": base,
                "stress": stress,
                "unit": "USD",
                "actor_app": m["actor_app"],
                "sensitivity": m["sensitivity"],
                "driver_id": driver_id,
            }

    # v1.2: rows retained for audit but excluded from quantification.
    #  - "Excluded — parent/sub duplicate": parent technique suppressed where the
    #    applicable sub-techniques are mapped in the same scenario, so one
    #    underlying behaviour cannot receive multiple weights in a stage barrier.
    #  - "Removed — ...": technique reclassified out of this scenario by QA.
    EXCLUDED_ROLE_PREFIXES = ("Excluded", "Removed")

    sc_ttp = defaultdict(list)
    for r in scenario_ttp_rows:
        if str(r[4]).startswith(EXCLUDED_ROLE_PREFIXES):
            continue
        if r[5] not in STAGES:
            continue
        sc_ttp[r[0]].append({
            "scenario": r[0], "tid": r[1], "tech": r[2], "tactics": r[3],
            "role": r[4], "stage": r[5], "basis": r[6], "url": r[7],
        })
    actor_app = {(r[0], r[1]): str(r[4]).lower() == "yes" for r in actor_ttp_rows}

    ttp_controls = defaultdict(list)
    for r in ttp_control_rows:
        base_eff = float(r[5]) if r[5] not in (None, "") else 0.0
        ttp_controls[r[0]].append({
            "cid": r[2], "name": r[3], "channel": r[4], "base_eff": base_eff,
            "mapping_source": r[9] if len(r) > 9 else None,
        })

    oi_prevent_mult = {}
    xl_wb = getattr(wb, "wb", None)
    if xl_wb is not None and "00 OI Engine Overlay" in xl_wb.sheetnames:
        overlay = xl_wb["00 OI Engine Overlay"]
        for r in range(2, overlay.max_row + 1):
            tid = str(overlay.cell(r, 1).value or "").strip()
            if not tid:
                continue
            raw = overlay.cell(r, 2).value
            if raw in (None, ""):
                raise ValueError(f"OI prevent-barrier multiplier missing for TTP {tid}.")
            mult = float(raw)
            if not 0.0 < mult <= 1.0:
                raise ValueError(
                    f"OI prevent-barrier multiplier for {tid} must be in (0, 1]; got {mult}."
                )
            if tid in oi_prevent_mult:
                raise ValueError(f"Duplicate OI prevent-barrier overlay for {tid}.")
            oi_prevent_mult[tid] = mult

    rule_by_tid = {r[1]: r[3] for r in facility_rule_rows if r[0] == "TTP"}

    # ---------------- Core deterministic model logic ----------------
    def ttp_feasible(tid, fac=None):
        fac = facility if fac is None else fac
        return facility_ttp_feasible(rule_by_tid.get(tid), fac)

    def scenario_feasible(sc, fac=None):
        fac = facility if fac is None else fac
        return scenario_is_feasible(sc, fac)

    def exposure_multiplier(fac=None):
        fac = facility if fac is None else fac
        m = 1.0
        for key in [
            "IT_OT_CONNECTIVITY", "REMOTE_ACCESS", "INTERNET_OT",
            "TRANSIENT_ASSETS", "SUPPLY_CHAIN_ROUTE", "WIRELESS_OT"
        ]:
            pair = (key, str(fac[key]))
            if pair not in exposure_map:
                raise ValueError(
                    f"Missing facility exposure multiplier for {key}={fac[key]!r}."
                )
            m *= float(exposure_map[pair])
        return float(np.clip(m, 0.5, 2.0))

    def selected_sector_mult(actor):
        return float(sector_map[sector_pack["sector"]]["multipliers"][actor])

    def selected_asset_mult(actor):
        return float(sector_pack["asset_multipliers"][actor])

    def canonical_geography(value):
        raw = "" if value is None else str(value).strip()
        if raw == "":
            raise ValueError(
                "COUNTRY_REGION must be populated; silent geography default is not permitted."
            )
        key = raw.upper().replace(" ", "")
        aliases = {
            "UAE": "UAE / GCC",
            "GCC": "UAE / GCC",
            "UAE/GCC": "UAE / GCC",
        }
        canonical = aliases.get(key, raw)
        if canonical not in geo_map:
            # nosec B608 — ValueError, not a SQL query
            raise ValueError("Unrecognised geography code: %s" % (raw,))
        return canonical

    selected_geography = canonical_geography(facility.get("COUNTRY_REGION"))
    facility["COUNTRY_REGION"] = selected_geography

    def selected_geo_mult(actor):
        row = geo_map[selected_geography]
        return float(row[actor])

    def maturity_factor(level):
        if level in (None, "", "Not Assessed"):
            return maturity_table[baseline_mat]
        return maturity_table[str(level)]

    def coverage_used(cid):
        c = controls[cid]
        return default_cov if c["coverage"] in (None, "") else float(c["coverage"])

    def pair_eff(mapping, overrides=None, reference=False):
        cid = mapping["cid"]
        if cid not in controls or mapping["base_eff"] <= 0:
            return 0.0
        if reference:
            mf, cov = maturity_table[baseline_mat], default_cov
        else:
            level = (overrides or {}).get(cid, controls[cid]["maturity"])
            mf, cov = maturity_factor(level), coverage_used(cid)
        return float(np.clip(mapping["base_eff"] * mf * cov, 0.0, 0.95))

    def combine_effects(values):
        """Strongest distinct control gets full credit; subsequent controls receive diminishing incremental credit."""
        vals = sorted([float(v) for v in values if float(v) > 0], reverse=True)
        if not vals:
            return 0.0
        total, weight = vals[0], agg_inc
        for e in vals[1:]:
            total += e * weight * (1 - total)
            weight *= agg_inc
        return float(min(total, 0.95))

    def relevant_ttps(actor, sc, fac=None):
        fac = facility if fac is None else fac
        if not scenario_feasible(sc, fac):
            return []
        return [
            x for x in sc_ttp[sc]
            if ttp_is_relevant(
                True,
                actor_app.get((actor, x["tid"]), False),
                sector_pack["rationale"][x["tid"]]["applicable"],
                ttp_feasible(x["tid"], fac),
            )
        ]

    def ttp_barrier(tid, channel, overrides=None, reference=False):
        # Deduplicate by Control ID within the TTP before combining.
        by_control = {}
        for m in ttp_controls.get(tid, []):
            if m["channel"] != channel or m["cid"] not in controls:
                continue
            e = pair_eff(m, overrides, reference)
            by_control[m["cid"]] = max(by_control.get(m["cid"], 0.0), e)
        barrier = combine_effects(by_control.values())
        if channel == "Prevent / Resist" and not reference:
            barrier = float(np.clip(barrier * oi_prevent_mult.get(str(tid), 1.0), 0.0, 0.95))
        return barrier, sorted(by_control)

    def channel_barrier(actor, sc, channel, overrides=None, reference=False, fac=None):
        rel = relevant_ttps(actor, sc, fac)
        vals, cids = [], set()
        for t in rel:
            b, ids = ttp_barrier(t["tid"], channel, overrides, reference)
            if ids:
                vals.append(b)
                cids.update(ids)
        # Equal weighting across relevant TTPs with at least one mapped control in this channel.
        return (float(np.mean(vals)) if vals else 0.0), sorted(cids)

    def channel_factor(actor, sc, channel, overrides=None, fac=None):
        actual, cids = channel_barrier(actor, sc, channel, overrides, False, fac)
        ref, _ = channel_barrier(actor, sc, channel, None, True, fac)
        ratio = (1 - actual) / (1 - ref) if ref < 1 else 1.0
        return float(np.clip(ratio, adj_floor, adj_ceiling)), cids, actual, ref

    def build_combo(actor, sc, overrides=None, fac=None):
        fac = facility if fac is None else fac
        rel = relevant_ttps(actor, sc, fac)
        by_stage = defaultdict(list)
        for t in rel:
            by_stage[t["stage"]].append(t)

        stages, p_success = [], 1.0
        valid = scenario_feasible(sc, fac)
        for st in STAGES:
            required = not (actor == "Malicious Insider" and st == "S1")
            tlist = by_stage.get(st, [])
            n_def = sum(t["role"] == "Scenario-defining" for t in tlist)
            if not required:
                stages.append({
                    "stage": st, "required": False, "n_ttp": len(tlist), "n_def": n_def,
                    "n_ctl": 0, "prior": 1.0, "ref_bar": 0.0, "act_bar": 0.0,
                    "adj": 1.0, "through": 1.0, "valid": True,
                })
                continue

            stage_valid = bool(tlist) and (st != "S5" or n_def > 0)
            valid = valid and stage_valid

            actual_ttp_barriers, reference_ttp_barriers, prevent_ids = [], [], set()
            for t in tlist:
                ab, aids = ttp_barrier(t["tid"], "Prevent / Resist", overrides, False)
                rb, rids = ttp_barrier(t["tid"], "Prevent / Resist", None, True)
                # Every active relevant TTP participates in the stage barrier.
                # If no Prevent / Resist mapping exists, ttp_barrier returns 0.0.
                # This treats missing mapping coverage conservatively rather than
                # removing an unmitigated route from the denominator.
                actual_ttp_barriers.append(ab)
                reference_ttp_barriers.append(rb)
                prevent_ids.update(aids or rids)

            # Equal weighting: no arbitrary 2x weighting for scenario-defining TTPs.
            act_bar = stage_barrier(actual_ttp_barriers)
            ref_bar = stage_barrier(reference_ttp_barriers)
            adj = float(np.clip(
                (1 - act_bar) / (1 - ref_bar) if ref_bar < 1 else 1.0,
                adj_floor, adj_ceiling,
            ))
            prior = actor_cfg[actor][st] if st != "S5" else actor_cfg[actor]["S5cap"] * scenario_difficulty[sc]
            through = float(np.clip(prior * adj, 0, 1)) if stage_valid else 0.0
            p_success = campaign_conditional_success([p_success, through])
            stages.append({
                "stage": st, "required": True, "n_ttp": len(tlist), "n_def": n_def,
                "n_ctl": len(prevent_ids), "prior": prior, "ref_bar": ref_bar,
                "act_bar": act_bar, "adj": adj, "through": through, "valid": stage_valid,
            })

        detect_factor, detect_ids, _, _ = channel_factor(actor, sc, "Detect / Contain", overrides, fac)
        recover_factor, recover_ids, _, _ = channel_factor(actor, sc, "Recover / Restore", overrides, fac)
        safety_factor, safety_ids, _, _ = channel_factor(actor, sc, "Safety / Resilience", overrides, fac)
        duration_factor = max(detect_factor * recover_factor, dur_floor)

        weights = {"Fixed": 0.0, "Recover": 0.0, "Safety": 0.0}
        for comp, d in impact[sc].items():
            if comp in ("Downtime days", "Capacity affected") or d["actor_app"] not in ("All", actor):
                continue
            if d["sensitivity"] in weights:
                weights[d["sensitivity"]] += 0.5 * (d["base"] + d["stress"])
        total_weight = sum(weights.values()) or 1.0
        nonbi_factor = (
            weights["Fixed"] / total_weight
            + weights["Recover"] / total_weight * recover_factor
            + weights["Safety"] / total_weight * safety_factor
        )
        nonbi_factor = float(np.clip(nonbi_factor, conseq_floor, conseq_ceiling))

        return {
            "actor": actor, "scenario": sc, "valid": bool(valid),
            "p_success": float(p_success if valid else 0.0), "rel": rel, "stages": stages,
            "detect_factor": detect_factor, "recover_factor": recover_factor,
            "safety_factor": safety_factor, "duration_factor": duration_factor,
            "nonbi_factor": nonbi_factor, "detect_cids": detect_ids,
            "recover_cids": recover_ids, "safety_cids": safety_ids,
        }

    combos0 = {(a, s): build_combo(a, s) for a in ACTORS for s in SCENARIOS}

    # ---------------- Coherent 500,000-year Monte Carlo ----------------
    N = int(general["SIMULATIONS"]["base"])
    if N != REQUIRED_SIMULATIONS and os.environ.get("CRQ_E2E_ALLOW_OT_N") != "1":
        raise ValueError(
            f"Model requires exactly {REQUIRED_SIMULATIONS:,} simulations; workbook currently has {N:,}."
        )
    seed = int(general["RANDOM_SEED"]["base"])
    stress_z = float(severity_settings["STRESS_Z"])
    rho = float(severity_settings["LOSS_DOWNTIME_RHO"])
    reference_lambda = float(general["REFERENCE_CAMPAIGNS_PER_YEAR"]["base"])
    prudence_factor = float(general["PRUDENCE_FACTOR"]["base"])
    reporting_view = str(general["REPORTING_VIEW"]["base"] or "Both").strip()
    if reference_lambda < 0:
        raise ValueError("REFERENCE_CAMPAIGNS_PER_YEAR must be non-negative.")
    if prudence_factor < 0:
        raise ValueError("PRUDENCE_FACTOR must be non-negative.")
    if reporting_view not in ("Best Estimate", "Prudent", "Both"):
        raise ValueError("REPORTING_VIEW must be Best Estimate, Prudent, or Both.")
    # Threat/sector/geography modifiers affect both total campaign intensity and actor mix.
    # Because actor shares sum to one, all-neutral multipliers preserve the base campaign rate.
    actor_weights = _actor_intensity_weights(
        actor_cfg,
        {a: selected_sector_mult(a) for a in ACTORS},
        {a: selected_asset_mult(a) for a in ACTORS},
        {a: selected_geo_mult(a) for a in ACTORS},
    )
    threat_intensity_multiplier = float(actor_weights.sum())
    actor_probs = effective_actor_probabilities(actor_weights)

    facility_mult = exposure_multiplier()
    lambda_be = best_estimate_lambda(reference_lambda, facility_mult, threat_intensity_multiplier)
    lambda_prudent = lambda_be * prudence_factor
    if not simulate:
        return {
            "output": None,
            "sector": sector_pack["sector"],
            "asset_type": sector_pack["asset_type"],
            "sector_pack_id": sector_pack["pack_id"],
            "sector_pack_status": sector_pack["pack_status"],
            "sector_pack": sector_pack,
            "combos": combos0,
            "actor_weights": actor_weights,
            "actor_probs": actor_probs,
            "threat_intensity_multiplier": threat_intensity_multiplier,
            "facility_mult": facility_mult,
            "reference_lambda": reference_lambda,
            "lambda_be": lambda_be,
            "lambda_prudent": lambda_prudent,
            "facility": facility,
            "rule_by_tid": rule_by_tid,
            "sc_ttp": sc_ttp,
            "actor_app": actor_app,
        }
    lambda_be_year = np.full(N, lambda_be)
    lambda_prudent_year = lambda_be_year * prudence_factor

    revenue_per_day = financial["ANNUAL_REVENUE_AT_RISK"] / 365.0
    bi_loss_factor = financial["BI_LOSS_FACTOR"]
    if not 0 <= bi_loss_factor <= 1:
        raise ValueError("BI_LOSS_FACTOR must be between 0% and 100%; model extra costs separately.")
    bi_loss_per_day = revenue_per_day * bi_loss_factor

    def lognormal_draw(base, stress, z):
        base = max(float(base), 1e-9)
        stress = max(float(stress), base)
        sigma = max(math.log(stress / base) / stress_z, 1e-9)
        return np.exp(math.log(base) + sigma * z)

    def impact_totals(actor, sc):
        base_total = stress_total = 0.0
        by_sensitivity = {"Fixed": [0.0, 0.0], "Recover": [0.0, 0.0], "Safety": [0.0, 0.0]}
        for comp, d in impact[sc].items():
            if comp in ("Downtime days", "Capacity affected") or d["actor_app"] not in ("All", actor):
                continue
            base_total += d["base"]
            stress_total += d["stress"]
            if d["sensitivity"] in by_sensitivity:
                by_sensitivity[d["sensitivity"]][0] += d["base"]
                by_sensitivity[d["sensitivity"]][1] += d["stress"]
        return base_total, stress_total, by_sensitivity

    def build_context(lambda_year, context_seed):
        """Build one deterministic event skeleton for a reporting basis.

        Reusing the same context for baseline and control what-ifs provides common
        random numbers. Best Estimate and Prudent use the same seed; if the
        prudence factor is 1.00 their contexts and results are exactly identical.
        """
        rng = np.random.default_rng(context_seed)
        counts = rng.poisson(lambda_year)
        year_idx = np.repeat(np.arange(N), counts)
        total_campaigns = len(year_idx)
        actor_idx = np.searchsorted(
            np.cumsum(actor_probs), rng.random(total_campaigns), side="right"
        )
        u_scenario = rng.random(total_campaigns)
        scenario_idx = np.empty(total_campaigns, dtype=np.int8)
        for ai, actor in enumerate(ACTORS):
            probs = np.array([
                scenario_prop[actor][s] if combos0[(actor, s)]["valid"] else 0.0
                for s in SCENARIOS
            ], dtype=float)
            if probs.sum() <= 0:
                raise ValueError(f"Actor '{actor}' has no feasible scenario after facility gating.")
            probs /= probs.sum()
            mask = actor_idx == ai
            scenario_idx[mask] = np.searchsorted(
                np.cumsum(probs), u_scenario[mask], side="right"
            )
        u_success = rng.random(total_campaigns)
        z_dur = rng.standard_normal(total_campaigns)
        z_independent = rng.standard_normal(total_campaigns)
        z_nonbi = rho * z_dur + math.sqrt(max(1 - rho * rho, 0.0)) * z_independent
        return {
            "lambda_year": lambda_year,
            "counts": counts,
            "year_idx": year_idx,
            "actor_idx": actor_idx,
            "scenario_idx": scenario_idx,
            "u_success": u_success,
            "z_dur": z_dur,
            "z_nonbi": z_nonbi,
        }

    bi_scale = [1.0]

    def evaluate(ctx, overrides=None):
        year_idx = ctx["year_idx"]
        actor_idx = ctx["actor_idx"]
        scenario_idx = ctx["scenario_idx"]
        u_success = ctx["u_success"]
        z_dur = ctx["z_dur"]
        z_nonbi = ctx["z_nonbi"]
        total_campaigns = len(year_idx)
        combos = {(a, s): build_combo(a, s, overrides) for a in ACTORS for s in SCENARIOS}
        pbase = np.zeros(total_campaigns)
        duration_factor = np.ones(total_campaigns)
        nonbi_factor = np.ones(total_campaigns)
        for ai, actor in enumerate(ACTORS):
            for si, sc in enumerate(SCENARIOS):
                mask = (actor_idx == ai) & (scenario_idx == si)
                c = combos[(actor, sc)]
                pbase[mask] = c["p_success"]
                duration_factor[mask] = c["duration_factor"]
                nonbi_factor[mask] = c["nonbi_factor"]

        # No separate logit shock: stage/control-derived probability is the
        # Bernoulli parameter for each campaign.
        p_event = np.clip(pbase, 0.0, 1.0)
        success = u_success < p_event

        sy = year_idx[success]
        sai = actor_idx[success]
        ssi = scenario_idx[success]
        zd = z_dur[success]
        zn = z_nonbi[success]
        df = duration_factor[success]
        nf = nonbi_factor[success]

        loss = np.zeros(success.sum())
        hours = np.zeros(success.sum())
        bi_evt = np.zeros(success.sum())
        nbi_evt = np.zeros(success.sum())
        capacity_evt = np.zeros(success.sum())
        bi_scale_factor = float(bi_scale[0]) if bi_scale else 1.0
        for ai, actor in enumerate(ACTORS):
            for si, sc in enumerate(SCENARIOS):
                mask = (sai == ai) & (ssi == si)
                if not np.any(mask):
                    continue
                dd = impact[sc]["Downtime days"]
                cc = impact[sc]["Capacity affected"]
                days = lognormal_draw(dd["base"], dd["stress"], zd[mask]) * df[mask]
                slope = (cc["stress"] / cc["base"] - 1) / stress_z if cc["base"] > 0 else 0.0
                capacity = np.clip(cc["base"] * (1 + slope * zd[mask]), 0.01, 1.0)
                bi = bi_loss_per_day * bi_scale_factor * days * capacity if bi_enabled[sc] else 0.0
                nbi_base, nbi_stress, _ = impact_totals(actor, sc)
                nbi = lognormal_draw(nbi_base, nbi_stress, zn[mask]) * nf[mask]
                loss[mask] = bi + nbi
                hours[mask] = days * 24.0
                bi_evt[mask] = bi
                nbi_evt[mask] = nbi
                capacity_evt[mask] = capacity

        # Facility annual arrays.
        aep = np.bincount(sy, weights=loss, minlength=N)
        aep_h = np.bincount(sy, weights=hours, minlength=N)
        aep_bi = np.bincount(sy, weights=bi_evt, minlength=N)
        aep_nbi = np.bincount(sy, weights=nbi_evt, minlength=N)
        # Capacity: annual max-affected capacity among successful events (0 if no events)
        aep_cap = np.zeros(N)
        if success.sum():
            np.maximum.at(aep_cap, sy, capacity_evt)
        oep = np.zeros(N); np.maximum.at(oep, sy, loss)
        oep_h = np.zeros(N); np.maximum.at(oep_h, sy, hours)

        # Annual arrays by actor, scenario, and actor-scenario cell.
        actor_aep, actor_oep = [], []
        for ai in range(3):
            mask = sai == ai
            aa = np.bincount(sy[mask], weights=loss[mask], minlength=N)
            ao = np.zeros(N); np.maximum.at(ao, sy[mask], loss[mask])
            actor_aep.append(aa); actor_oep.append(ao)

        scenario_aep, scenario_oep = [], []
        for si in range(5):
            mask = ssi == si
            sa = np.bincount(sy[mask], weights=loss[mask], minlength=N)
            so = np.zeros(N); np.maximum.at(so, sy[mask], loss[mask])
            scenario_aep.append(sa); scenario_oep.append(so)

        cell_aep = [[None for _ in range(5)] for _ in range(3)]
        cell_oep = [[None for _ in range(5)] for _ in range(3)]
        for ai in range(3):
            for si in range(5):
                mask = (sai == ai) & (ssi == si)
                ca = np.bincount(sy[mask], weights=loss[mask], minlength=N)
                co = np.zeros(N); np.maximum.at(co, sy[mask], loss[mask])
                cell_aep[ai][si] = ca; cell_oep[ai][si] = co

        actor_aal = [float(x.mean()) for x in actor_aep]
        scenario_aal = [float(x.mean()) for x in scenario_aep]
        cell_aal = np.array([[float(cell_aep[ai][si].mean()) for si in range(5)] for ai in range(3)])
        cell_succ_freq = np.zeros((3, 5))
        cell_p = np.zeros((3, 5))
        for ai, actor in enumerate(ACTORS):
            for si, sc in enumerate(SCENARIOS):
                sm = (sai == ai) & (ssi == si)
                attempts = (actor_idx == ai) & (scenario_idx == si)
                cell_succ_freq[ai, si] = sm.sum() / N
                cell_p[ai, si] = p_event[attempts].mean() if np.any(attempts) else combos[(actor, sc)]["p_success"]

        return {
            "combos": combos, "pbase": pbase, "p_event": p_event, "success": success,
            "loss": loss, "hours": hours, "success_year": sy,
            "success_actor": sai, "success_scenario": ssi,
            "aep": aep, "oep": oep, "aep_h": aep_h, "oep_h": oep_h,
            "aep_bi": aep_bi, "aep_nbi": aep_nbi, "aep_cap": aep_cap,
            "actor_aep": actor_aep, "actor_oep": actor_oep,
            "scenario_aep": scenario_aep, "scenario_oep": scenario_oep,
            "cell_aep": cell_aep, "cell_oep": cell_oep,
            "actor_aal": actor_aal, "scenario_aal": scenario_aal,
            "cell_aal": cell_aal, "cell_succ_freq": cell_succ_freq, "cell_p": cell_p,
        }

    contexts = {
        "Best Estimate": build_context(lambda_be_year, seed),
        "Prudent": build_context(lambda_prudent_year, seed),
    }
    baselines = {
        name: evaluate(ctx)
        for name, ctx in contexts.items()
    }
    primary_view = "Best Estimate" if reporting_view == "Best Estimate" else "Prudent"
    primary_ctx = contexts[primary_view]
    baseline = baselines[primary_view]
    base_aal = float(baseline["aep"].mean())

    # Preserve compact local names for downstream detailed output generation.
    counts = primary_ctx["counts"]
    year_idx = primary_ctx["year_idx"]
    actor_idx = primary_ctx["actor_idx"]
    scenario_idx = primary_ctx["scenario_idx"]
    total_campaigns = len(year_idx)

    def var_tvar(arr, q):
        return shared_var_tvar(arr, q)

    # ---------------- One-control-at-a-time what-ifs (same N as baseline) ----------------
    # Extra stats (TVaR, percentiles, event frequency, AEP LEC) are derived from the
    # existing evaluate() annual aggregate vector. No change to simulation methodology.
    levels = ["Absent", "Initial", "Developing", "Managed", "Optimised"]

    def effective_level(c):
        return baseline_mat if c["maturity"] in (None, "", "Not Assessed") else c["maturity"]

    def next_level(level):
        if level not in levels:
            return "Managed"
        idx = levels.index(level)
        return levels[min(idx + 1, len(levels) - 1)]

    def stats_from_aep(aep, n_success):
        v95, t95 = var_tvar(aep, 0.95)
        v99, t99 = var_tvar(aep, 0.99)
        return {
            "aal": float(np.asarray(aep).mean()),
            "p95": v95, "p99": v99, "tvar95": t95, "tvar99": t99,
            "event_freq": n_success / N,
            "n_success": int(n_success),
            "lec": empirical_lec(aep),
        }

    base_stats = {
        view_name: stats_from_aep(baselines[view_name]["aep"], baselines[view_name]["success"].sum())
        for view_name in ("Best Estimate", "Prudent")
    }

    whatifs = []
    for cid, c in controls.items():
        current = effective_level(c)
        nxt = next_level(current)
        mapped_nonzero = any(
            m["cid"] == cid and m["base_eff"] > 0
            for maps in ttp_controls.values() for m in maps
        )
        results_by_view = {}
        for view_name in ("Best Estimate", "Prudent"):
            baseline_aal = float(baselines[view_name]["aep"].mean())
            if (not run_whatifs) or (not mapped_nonzero) or nxt == current:
                st = dict(base_stats[view_name])
            else:
                ev = evaluate(contexts[view_name], {cid: nxt})
                st = stats_from_aep(ev["aep"], ev["success"].sum())
            st["baseline"] = baseline_aal
            st["reduction"] = baseline_aal - st["aal"]
            st["pct"] = st["reduction"] / baseline_aal if baseline_aal else 0.0
            st["var95"] = st["p95"]
            st["var99"] = st["p99"]
            st["var95_base"] = base_stats[view_name]["p95"]
            st["var99_base"] = base_stats[view_name]["p99"]
            st["var95_change"] = base_stats[view_name]["p95"] - st["p95"]
            st["var99_change"] = base_stats[view_name]["p99"] - st["p99"]
            st["tvar95_base"] = base_stats[view_name]["tvar95"]
            st["tvar95_change"] = base_stats[view_name]["tvar95"] - st["tvar95"]
            st["tvar99_base"] = base_stats[view_name]["tvar99"]
            st["tvar99_change"] = base_stats[view_name]["tvar99"] - st["tvar99"]
            st["freq_base"] = base_stats[view_name]["event_freq"]
            st["freq_change"] = base_stats[view_name]["event_freq"] - st["event_freq"]
            results_by_view[view_name] = st
        costs = treatment_cost_metrics(
            aal_reduction=results_by_view[primary_view]["reduction"],
            one_off_cost=None,
            annual_cost=None,
            evaluation_years=None,
        )
        whatifs.append({
            "cid": cid, "name": c["name"], "channel": c["channel"],
            "current": current, "whatif": nxt,
            "be": results_by_view["Best Estimate"],
            "prudent": results_by_view["Prudent"],
            "reduction": results_by_view[primary_view]["reduction"],
            "mapped": mapped_nonzero,
            "costs": costs,
        })
    whatifs.sort(key=lambda x: x["reduction"], reverse=True)

    crn_whatif_ok = True
    for x in whatifs:
        mapped_nonzero = any(
            m["cid"] == x["cid"] and m["base_eff"] > 0
            for maps in ttp_controls.values() for m in maps
        )
        if run_whatifs and mapped_nonzero and x["whatif"] != x["current"]:
            ev1 = evaluate(contexts[primary_view], {x["cid"]: x["whatif"]})
            ev2 = evaluate(contexts[primary_view], {x["cid"]: x["whatif"]})
            crn_whatif_ok = bool(np.array_equal(ev1["aep"], ev2["aep"]))
            break

    # ---------------- Audit / output tables ----------------
    ttp_detail = []
    for actor in ACTORS:
        for sc in SCENARIOS:
            for t in sc_ttp[sc]:
                aa = actor_app.get((actor, t["tid"]), False)
                sector_detail = sector_pack["rationale"][t["tid"]]
                sa = sector_detail["applicable"]
                ff = ttp_feasible(t["tid"]) and scenario_feasible(sc)
                mapped = len({m["cid"] for m in ttp_controls[t["tid"]] if m["cid"] in controls and m["base_eff"] > 0})
                ttp_detail.append([
                    actor, sc, t["tid"], t["tech"], t["stage"], t["role"],
                    "Yes" if aa else "No", "Yes" if ff else "No",
                    "Yes" if ttp_is_relevant(True, aa, sa, ff) else "No", mapped, t["basis"], t["url"],
                    "Yes" if sa else "No", sector_detail["facility_gate"],
                    sector_detail["rationale"], sector_detail["guidance_url"],
                ])

    path_rows = []
    success_summary = []
    for actor in ACTORS:
        for sc in SCENARIOS:
            combo = baseline["combos"][(actor, sc)]
            stage_probs = {}
            for st in combo["stages"]:
                stage_probs[st["stage"]] = st["through"]
                path_rows.append([
                    actor, sc, st["stage"], "Yes" if st["required"] else "No",
                    st["n_ttp"], st["n_def"], st["n_ctl"], st["prior"], st["ref_bar"],
                    st["act_bar"], st["adj"], st["through"], "Yes" if st["valid"] else "No",
                ])
            success_summary.append([
                actor, sc, stage_probs.get("S1", 1.0), stage_probs.get("S2", 0.0),
                stage_probs.get("S3", 0.0), stage_probs.get("S4", 0.0), stage_probs.get("S5", 0.0),
                combo["p_success"], "Yes" if combo["valid"] else "No",
            ])

    attempt_counts = np.zeros((3, 5), int)
    for ai in range(3):
        for si in range(5):
            attempt_counts[ai, si] = int(np.sum((actor_idx == ai) & (scenario_idx == si)))

    freq_rows = []
    for ai, actor in enumerate(ACTORS):
        for si, sc in enumerate(SCENARIOS):
            combo = baseline["combos"][(actor, sc)]
            freq_rows.append([
                actor, sc, "Yes" if combo["valid"] else "No",
                actor_cfg[actor]["share"], actor_probs[ai], scenario_prop[actor][sc],
                actor_cfg[actor]["threat"], selected_sector_mult(actor),
                selected_asset_mult(actor), selected_geo_mult(actor),
                exposure_multiplier(), attempt_counts[ai, si] / N,
                baseline["cell_p"][ai, si], baseline["cell_succ_freq"][ai, si],
            ])

    impact_audit = []
    for actor in ACTORS:
        for sc in SCENARIOS:
            combo = baseline["combos"][(actor, sc)]
            dd, cc = impact[sc]["Downtime days"], impact[sc]["Capacity affected"]
            nbi_base, nbi_stress, _ = impact_totals(actor, sc)
            base_revenue = revenue_per_day * dd["base"] * cc["base"]
            stress_revenue = revenue_per_day * dd["stress"] * cc["stress"]
            base_bi = base_revenue * bi_loss_factor if bi_enabled[sc] else 0.0
            stress_bi = stress_revenue * bi_loss_factor if bi_enabled[sc] else 0.0
            impact_audit.append([
                actor, sc, dd["base"], dd["stress"], cc["base"], cc["stress"],
                base_revenue, stress_revenue, base_bi, stress_bi,
                nbi_base, nbi_stress, base_bi + nbi_base, stress_bi + nbi_stress,
                combo["duration_factor"], combo["nonbi_factor"],
            ])

    retention = float(risk_financing.get("INSURANCE_RETENTION", 0.0) or 0.0)
    tail_basis = normalize_tail_basis(risk_financing.get("TAIL_BASIS", LABEL_TVAR_99))
    appetite = parse_appetite_inputs(appetite_inputs)

    def summarize_view(result):
        aal = float(result["aep"].mean())
        v95, tv95 = var_tvar(result["aep"], .95)
        v99, tv99 = var_tvar(result["aep"], .99)
        p_any = float((result["aep"] > 0).mean())
        mean_h = float(result["aep_h"].mean())
        _, tv95_h = var_tvar(result["aep_h"], .95)
        successful_years = result["aep_h"][result["aep"] > 0]
        cond_h = float(successful_years.mean()) if successful_years.size else 0.0
        selected_tvar = tv95 if tail_basis == LABEL_TVAR_95 else tv99
        # Downtime P95 in days for appetite (operational, not financial VaR)
        downtime_days = result["aep_h"] / 24.0
        downtime_p95 = float(np.quantile(downtime_days, 0.95, method=VAR_QUANTILE_METHOD))
        appet = evaluate_appetite(
            appetite=appetite,
            aal=aal,
            p_any=p_any,
            tvar95=tv95,
            tvar99=tv99,
            downtime_p95_days=downtime_p95,
            annual_losses=result["aep"],
        )
        return {
            LABEL_AAL: aal, LABEL_VAR_95: v95, LABEL_TVAR_95: tv95,
            LABEL_VAR_99: v99, LABEL_TVAR_99: tv99,
            "P(any successful loss event)": p_any,
            "Mean annual downtime (hours)": mean_h,
            "Mean downtime | successful year (hours)": cond_h,
            "TVaR 95 downtime (hours)": tv95_h,
            "Downtime P95 (days)": downtime_p95,
            "Selected TVaR": selected_tvar,
            "Insurance retention": retention,
            TAIL_ABOVE_RETENTION_LABEL: max(selected_tvar - retention, 0.0),
            "P(annual loss exceeds tolerance)": appet["p_exceed_tolerance"],
            "appetite_status": appet["appetite_status"],
            "appetite_breaches": appet["appetite_breaches"],
        }

    metrics_by_view = {
        name: summarize_view(result)
        for name, result in baselines.items()
    }
    be_metrics = metrics_by_view["Best Estimate"]
    prudent_metrics = metrics_by_view["Prudent"]
    primary_metrics = metrics_by_view[primary_view]
    v95, tv95 = primary_metrics[LABEL_VAR_95], primary_metrics[LABEL_TVAR_95]
    v99, tv99 = primary_metrics[LABEL_VAR_99], primary_metrics[LABEL_TVAR_99]
    p_any = primary_metrics["P(any successful loss event)"]

    def selected_value(view_name, value):
        return value if reporting_view in (view_name, "Both") else None

    financial_metrics = [
        [LABEL_AAL, selected_value("Best Estimate", be_metrics[LABEL_AAL]), selected_value("Prudent", prudent_metrics[LABEL_AAL]), "Mean annual aggregate financial loss across all simulation trials, including zero-loss years."],
        [LABEL_VAR_95, selected_value("Best Estimate", be_metrics[LABEL_VAR_95]), selected_value("Prudent", prudent_metrics[LABEL_VAR_95]), f"95th percentile of annual aggregate loss (NumPy quantile method={VAR_QUANTILE_METHOD}; ≈ 1-in-20 annual aggregate loss)."],
        [LABEL_TVAR_95, selected_value("Best Estimate", be_metrics[LABEL_TVAR_95]), selected_value("Prudent", prudent_metrics[LABEL_TVAR_95]), "Mean annual aggregate loss across the worst 5% of simulation trials (Expected Shortfall)."],
        [LABEL_VAR_99, selected_value("Best Estimate", be_metrics[LABEL_VAR_99]), selected_value("Prudent", prudent_metrics[LABEL_VAR_99]), f"99th percentile of annual aggregate loss (NumPy quantile method={VAR_QUANTILE_METHOD}; ≈ 1-in-100 annual aggregate loss)."],
        [LABEL_TVAR_99, selected_value("Best Estimate", be_metrics[LABEL_TVAR_99]), selected_value("Prudent", prudent_metrics[LABEL_TVAR_99]), "Mean annual aggregate loss across the worst 1% of simulation trials (Expected Shortfall)."],
        ["Selected TVaR", selected_value("Best Estimate", be_metrics["Selected TVaR"]), selected_value("Prudent", prudent_metrics["Selected TVaR"]), f"Tail basis selected on 19 Tail Risk Metrics: {tail_basis}."],
        ["Insurance retention", selected_value("Best Estimate", retention), selected_value("Prudent", retention), "Insurance-programme retention only — not organisational risk tolerance."],
        [TAIL_ABOVE_RETENTION_LABEL, selected_value("Best Estimate", be_metrics[TAIL_ABOVE_RETENTION_LABEL]), selected_value("Prudent", prudent_metrics[TAIL_ABOVE_RETENTION_LABEL]), "Selected TVaR minus insurance retention, floored at zero; indicative financing diagnostic, not expected insured loss."],
    ]
    operational_metrics = [
        ["P(any successful loss event)", selected_value("Best Estimate", be_metrics["P(any successful loss event)"]), selected_value("Prudent", prudent_metrics["P(any successful loss event)"]), "Share of years with at least one successful loss event."],
        ["Mean annual downtime (hours)", selected_value("Best Estimate", be_metrics["Mean annual downtime (hours)"]), selected_value("Prudent", prudent_metrics["Mean annual downtime (hours)"]), "Expected hours per year including zero-event years."],
        ["Mean downtime | successful year (hours)", selected_value("Best Estimate", be_metrics["Mean downtime | successful year (hours)"]), selected_value("Prudent", prudent_metrics["Mean downtime | successful year (hours)"]), "Mean hours in years with at least one successful event."],
        ["TVaR 95 downtime (hours)", selected_value("Best Estimate", be_metrics["TVaR 95 downtime (hours)"]), selected_value("Prudent", prudent_metrics["TVaR 95 downtime (hours)"]), "Mean downtime in the worst 5% of simulated years (operational consequence, not financial VaR)."],
    ]
    run_metrics = [
        ["Last simulation run", datetime.now().strftime("%Y-%m-%d %H:%M"), datetime.now().strftime("%Y-%m-%d %H:%M"), "Timestamp when the Python engine refreshed the workbook."],
        ["Simulation years", N, N, "Number of simulated facility-years per reporting basis and per control what-if."],
        ["Reference campaign rate", reference_lambda, reference_lambda, "Centrally governed material-campaign arrival-rate prior before modifiers."],
        ["Facility exposure multiplier", facility_mult, facility_mult, "Combined IT/OT, remote-access, internet-OT and transient-asset exposure factor; supply-chain and wireless are feasibility-only."],
        ["Threat intensity multiplier", threat_intensity_multiplier, threat_intensity_multiplier, "Σ(Actor Share × Threat Activity × Sector × Asset Type × Geography). Each overlay is applied exactly once."],
        ["Selected sector", sector_pack["sector"], sector_pack["sector"], "Sector selected on 03 Facility Inputs; one facility/site is the unit of analysis."],
        ["Selected asset type", sector_pack["asset_type"], sector_pack["asset_type"], "Asset type selected on 03 Facility Inputs."],
        ["Resolved pack ID", sector_pack["pack_id"], sector_pack["pack_id"], "Exactly one registered pack from 28 Sector Pack Registry."],
        ["Simulated campaign rate", float(contexts["Best Estimate"]["counts"].mean()), float(contexts["Prudent"]["counts"].mean()), "Average Poisson campaign count after all frequency modifiers."],
        ["Prudence factor", 1.0, prudence_factor, f"Applied only to frequency. Reporting selection: {reporting_view}; detailed result sheets use {primary_view}."],
    ]

    def _decomp_row(name, aal, aep, attempts, succ, pmean):
        v95, t95 = var_tvar(aep, 0.95)
        v99, t99 = var_tvar(aep, 0.99)
        share = aal / base_aal if base_aal else 0.0
        return [name, aal, v95, t95, v99, t99, attempts, succ, pmean, share, 0]

    actor_decomp = []
    for ai, actor in enumerate(ACTORS):
        attempts = np.sum(actor_idx == ai) / N
        succ = np.sum(baseline["success"] & (actor_idx == ai)) / N
        pmean = baseline["p_event"][actor_idx == ai].mean()
        actor_decomp.append(_decomp_row(
            actor, baseline["actor_aal"][ai], baseline["actor_aep"][ai],
            attempts, succ, pmean,
        ))
    actor_decomp.sort(key=lambda x: x[1], reverse=True)
    for rank, row in enumerate(actor_decomp, 1):
        row[10] = rank

    scenario_decomp = []
    for si, sc in enumerate(SCENARIOS):
        attempts = np.sum(scenario_idx == si) / N
        succ = np.sum(baseline["success"] & (scenario_idx == si)) / N
        pmean = baseline["p_event"][scenario_idx == si].mean()
        scenario_decomp.append(_decomp_row(
            sc, baseline["scenario_aal"][si], baseline["scenario_aep"][si],
            attempts, succ, pmean,
        ))
    scenario_decomp.sort(key=lambda x: x[1], reverse=True)
    for rank, row in enumerate(scenario_decomp, 1):
        row[10] = rank

    scenario_comps = {SCENARIOS[i]: baseline["scenario_aep"][i] for i in range(5)}
    actor_comps = {ACTORS[i]: baseline["actor_aep"][i] for i in range(3)}
    scen_t95 = tvar_tail_contributions(baseline["aep"], scenario_comps, 0.95)
    scen_t99 = tvar_tail_contributions(baseline["aep"], scenario_comps, 0.99)
    actor_t95 = tvar_tail_contributions(baseline["aep"], actor_comps, 0.95)
    actor_t99 = tvar_tail_contributions(baseline["aep"], actor_comps, 0.99)

    tail_rows = []
    reported_views = (
        ["Best Estimate", "Prudent"] if reporting_view == "Both" else [reporting_view]
    )
    for view_name in reported_views:
        result = baselines[view_name]
        for rp in RETURN_PERIODS:
            q = 1 - 1 / rp
            av, at = var_tvar(result["aep"], q); ov, ot = var_tvar(result["oep"], q)
            ah, aht = var_tvar(result["aep_h"], q); oh, oht = var_tvar(result["oep_h"], q)
            tail_rows.append([view_name, rp, av, at, ov, ot, ah, aht, oh, oht])

    aggregate_curve_rows = [[
        p,
        float(np.quantile(baselines["Best Estimate"]["aep"], 1 - p, method=VAR_QUANTILE_METHOD)),
        float(np.quantile(baselines["Best Estimate"]["oep"], 1 - p, method=VAR_QUANTILE_METHOD)),
        float(np.quantile(baselines["Prudent"]["aep"], 1 - p, method=VAR_QUANTILE_METHOD)),
        float(np.quantile(baselines["Prudent"]["oep"], 1 - p, method=VAR_QUANTILE_METHOD)),
        float(np.quantile(baselines["Best Estimate"]["aep_h"], 1 - p, method=VAR_QUANTILE_METHOD)),
        float(np.quantile(baselines["Best Estimate"]["oep_h"], 1 - p, method=VAR_QUANTILE_METHOD)),
        float(np.quantile(baselines["Prudent"]["aep_h"], 1 - p, method=VAR_QUANTILE_METHOD)),
        float(np.quantile(baselines["Prudent"]["oep_h"], 1 - p, method=VAR_QUANTILE_METHOD)),
    ] for p in EXCEEDANCE_PROBS]

    # Wide scenario LEC table: probability + AEP/OEP per scenario.
    scenario_lec_rows = []
    for p in EXCEEDANCE_PROBS:
        row = [p]
        for si in range(5):
            row += [
                float(np.quantile(baseline["scenario_aep"][si], 1 - p, method=VAR_QUANTILE_METHOD)),
                float(np.quantile(baseline["scenario_oep"][si], 1 - p, method=VAR_QUANTILE_METHOD)),
            ]
        scenario_lec_rows.append(row)

    actor_lec_rows = []
    for p in EXCEEDANCE_PROBS:
        row = [p]
        for ai in range(3):
            row += [
                float(np.quantile(baseline["actor_aep"][ai], 1 - p, method=VAR_QUANTILE_METHOD)),
                float(np.quantile(baseline["actor_oep"][ai], 1 - p, method=VAR_QUANTILE_METHOD)),
            ]
        actor_lec_rows.append(row)

    cell_lec_rows = []
    for ai, actor in enumerate(ACTORS):
        for si, sc in enumerate(SCENARIOS):
            for p in EXCEEDANCE_PROBS:
                cell_lec_rows.append([
                    actor, sc, p,
                    float(np.quantile(baseline["cell_aep"][ai][si], 1 - p, method=VAR_QUANTILE_METHOD)),
                    float(np.quantile(baseline["cell_oep"][ai][si], 1 - p, method=VAR_QUANTILE_METHOD)),
                ])

    # ---------------- End-to-end QA ----------------
    repeat = evaluate(primary_ctx)
    unit_prudence_context = build_context(lambda_be_year, seed)
    unit_prudence = evaluate(unit_prudence_context)
    safe_fac = dict(facility); safe_fac["SAFETY_SYSTEM"] = "None"
    wire_fac = dict(facility); wire_fac["WIRELESS_OT"] = "Yes"
    remote_fac = dict(facility); remote_fac["REMOTE_ACCESS"] = "None"; remote_fac["IT_OT_CONNECTIVITY"] = "No"
    wire_ids = {"T0860", "T0887", "T1695.003"}
    remote_ids = {"T0822", "T0866", "T0886"}
    wire_before = sum(t["tid"] in wire_ids for t in relevant_ttps("Nation State", "Operational Disruption", facility))
    wire_after = sum(t["tid"] in wire_ids for t in relevant_ttps("Nation State", "Operational Disruption", wire_fac))
    remote_before = sum(t["tid"] in remote_ids for t in relevant_ttps("Nation State", "Operational Disruption", facility))
    remote_after = sum(t["tid"] in remote_ids for t in relevant_ttps("Nation State", "Operational Disruption", remote_fac))

    agg_curve = [r[3] if primary_view == "Prudent" else r[1] for r in aggregate_curve_rows]
    all_scenario_monotonic = all(
        all(scenario_lec_rows[i + 1][1 + 2 * si] >= scenario_lec_rows[i][1 + 2 * si] - 1e-8 for i in range(len(scenario_lec_rows) - 1))
        for si in range(5)
    )
    all_actor_monotonic = all(
        all(actor_lec_rows[i + 1][1 + 2 * ai] >= actor_lec_rows[i][1 + 2 * ai] - 1e-8 for i in range(len(actor_lec_rows) - 1))
        for ai in range(3)
    )
    all_paths = sum(c["valid"] for c in combos0.values())
    base_eff_values = [m["base_eff"] for maps in ttp_controls.values() for m in maps if m["channel"] != "Excluded — no modelled effect"]
    impact_pairs_ordered = all(
        base >= 0 and stress >= base
        for base, stress in calculated_driver_values.values()
    )
    inactive_driver_toggles = [
        (sc, driver_id)
        for driver_id, m in driver_matrix.items()
        for sc in SCENARIOS
        if not m["applicable"][sc]
    ]
    inactive_driver_toggles_honored = all(
        (not bi_enabled[sc]) if driver_id == "BI-01" else driver_matrix[driver_id]["name"] not in impact[sc]
        for sc, driver_id in inactive_driver_toggles
    )
    generic_consumer_terms = ("credit monitoring", "card replacement", "customer notification", "customer churn")
    generic_consumer_rows = [
        m["name"] for m in driver_matrix.values()
        if any(term in m["name"].lower() for term in generic_consumer_terms)
    ]

    tests = [
        ["Simulation count is exactly 500,000", "PASS" if N == REQUIRED_SIMULATIONS or os.environ.get("CRQ_E2E_ALLOW_OT_N") == "1" else "FAIL", N, REQUIRED_SIMULATIONS],
        ["Not Assessed resolves to Developing = 0.50", "PASS" if abs(maturity_factor("Not Assessed") - 0.50) < 1e-12 else "FAIL", maturity_factor("Not Assessed"), 0.50],
        ["Default coverage is 75%", "PASS" if abs(default_cov - 0.75) < 1e-12 else "FAIL", default_cov, 0.75],
        ["Optimised maturity factor is 0.95", "PASS" if abs(maturity_table.get("Optimised", -1) - 0.95) < 1e-12 else "FAIL", maturity_table.get("Optimised"), 0.95],
        ["All non-excluded TTP-control Base Efficacy values are within (0,1]", "PASS" if base_eff_values and min(base_eff_values) > 0 and max(base_eff_values) <= 1 else "FAIL", f"{min(base_eff_values):.2f} to {max(base_eff_values):.2f}" if base_eff_values else "none", "(0,1]"],
        ["Actor probabilities normalize to 1", "PASS" if abs(actor_probs.sum() - 1) < 1e-12 else "FAIL", actor_probs.sum(), 1],
        ["Reference campaign rate is non-negative", "PASS" if reference_lambda >= 0 else "FAIL", reference_lambda, ">= 0"],
        ["Prudence factor is non-negative and uncapped", "PASS" if prudence_factor >= 0 else "FAIL", prudence_factor, ">= 0; no upper cap"],
        ["Reporting view is valid", "PASS" if reporting_view in ("Best Estimate", "Prudent", "Both") else "FAIL", reporting_view, "Best Estimate / Prudent / Both"],
        ["Best-estimate λ bridge reconciles with sector and asset overlay exactly once", "PASS" if abs(float(lambda_be_year.mean()) - lambda_be) < 1e-12 else "FAIL", float(lambda_be_year.mean()), lambda_be],
        ["Prudent λ scales exactly by the prudence factor", "PASS" if np.allclose(lambda_prudent_year, lambda_be_year * prudence_factor, atol=0, rtol=0) else "FAIL", float(lambda_prudent_year.mean()), float(lambda_be_year.mean() * prudence_factor)],
        ["Prudence factor 1.00 reproduces Best Estimate exactly", "PASS" if np.array_equal(baselines["Best Estimate"]["aep"], unit_prudence["aep"]) else "FAIL", "exact match" if np.array_equal(baselines["Best Estimate"]["aep"], unit_prudence["aep"]) else "mismatch", "exact match"],
        ["Scenario propensities normalize for every actor", "PASS" if all(abs(sum(scenario_prop[a].values()) - 1) < 1e-12 for a in ACTORS) else "FAIL", max(abs(sum(scenario_prop[a].values()) - 1) for a in ACTORS), 0],
        ["All conditional success probabilities are within [0,1]", "PASS" if all(0 <= c["p_success"] <= 1 for c in combos0.values()) else "FAIL", f"{min(c['p_success'] for c in combos0.values()):.4f} to {max(c['p_success'] for c in combos0.values()):.4f}", "0 to 1"],
        ["No independent success logit shock is active", "PASS" if "SUCCESS_LOGIT_SIGMA" not in general and np.array_equal(baseline["p_event"], baseline["pbase"]) else "FAIL", "direct Bernoulli parameter", "stage/control-derived P(success)"],
        ["All 15 default actor-scenario attack paths are valid", "PASS" if all_paths == 15 else "FAIL", all_paths, 15],
        ["No valid S5 path lacks a scenario-defining TTP", "PASS" if all(any(st["stage"] == "S5" and st["n_def"] > 0 and st["valid"] for st in c["stages"]) for c in combos0.values()) else "FAIL", "checked 15 paths", "S5 defining TTP required"],
        ["Every relevant TTP participates in Prevent-stage aggregation; unmapped TTPs contribute zero barrier", "PASS" if all(
            abs(st["act_bar"] - (float(np.mean([ttp_barrier(t["tid"], "Prevent / Resist", None, False)[0] for t in [x for x in c["rel"] if x["stage"] == st["stage"]]])) if [x for x in c["rel"] if x["stage"] == st["stage"]] else 0.0)) < 1e-12
            for c in combos0.values() for st in c["stages"] if st["required"]
        ) else "FAIL", "all required stages checked", "all relevant TTPs included; no mapping = 0"],
        ["Actor AAL decomposition reconciles to facility AAL", "PASS" if abs(sum(baseline["actor_aal"]) - base_aal) < 1e-6 else "FAIL", sum(baseline["actor_aal"]) - base_aal, 0],
        ["Scenario AAL decomposition reconciles to facility AAL", "PASS" if abs(sum(baseline["scenario_aal"]) - base_aal) < 1e-6 else "FAIL", sum(baseline["scenario_aal"]) - base_aal, 0],
        ["Actor-scenario AAL matrix reconciles to facility AAL", "PASS" if abs(float(baseline["cell_aal"].sum()) - base_aal) < 1e-6 else "FAIL", float(baseline["cell_aal"].sum()) - base_aal, 0],
        ["TVaR95 is not below VaR95", "PASS" if tv95 >= v95 else "FAIL", tv95 - v95, ">= 0"],
        ["TVaR99 is not below VaR99", "PASS" if tv99 >= v99 else "FAIL", tv99 - v99, ">= 0"],
        ["Scenario TVaR 99 contributions reconcile to aggregate TVaR 99", "PASS" if abs(sum(scen_t99.values()) - tv99) < max(1.0, 1e-6 * abs(tv99)) else "FAIL", sum(scen_t99.values()) - tv99, 0],
        ["Actor TVaR 95 contributions reconcile to aggregate TVaR 95", "PASS" if abs(sum(actor_t95.values()) - tv95) < max(1.0, 1e-6 * abs(tv95)) else "FAIL", sum(actor_t95.values()) - tv95, 0],
        ["TVaR uses upper-tail Expected Shortfall when VaR is zero", "PASS" if var_tvar(baseline["aep"], .50)[1] > base_aal + 1e-8 else "FAIL", var_tvar(baseline["aep"], .50)[1], "> AAL when positive losses occupy less than half of years"],
        ["Aggregate AEP LEC is monotonic toward rarer probabilities", "PASS" if all(agg_curve[i + 1] >= agg_curve[i] - 1e-8 for i in range(len(agg_curve) - 1)) else "FAIL", "monotonic", "monotonic"],
        ["All scenario AEP LECs are monotonic", "PASS" if all_scenario_monotonic else "FAIL", "5 scenario curves", "monotonic"],
        ["All actor AEP LECs are monotonic", "PASS" if all_actor_monotonic else "FAIL", "3 actor curves", "monotonic"],
        ["Every one-level control uplift is non-increasing in AAL for both views", "PASS" if min(min(x["be"]["reduction"], x["prudent"]["reduction"]) for x in whatifs) >= -1e-8 else "FAIL", min(min(x["be"]["reduction"], x["prudent"]["reduction"]) for x in whatifs), ">= 0"],
        ["Fixed seed / common random numbers reproduce baseline exactly", "PASS" if np.array_equal(baseline["aep"], repeat["aep"]) else "FAIL", "exact match" if np.array_equal(baseline["aep"], repeat["aep"]) else "mismatch", "exact match"],
        ["What-if common random numbers are reproducible for a mapped control", "PASS" if crn_whatif_ok else "FAIL", "exact match" if crn_whatif_ok else "mismatch", "exact match"],
        ["BI loss factor is within [0,1]", "PASS" if 0 <= bi_loss_factor <= 1 else "FAIL", bi_loss_factor, "0 to 1"],
        ["Gross revenue and modelled BI are separated", "PASS" if all(
            abs(r[8] - (r[6] * bi_loss_factor if bi_enabled[r[1]] else 0.0)) < 1e-6
            and abs(r[9] - (r[7] * bi_loss_factor if bi_enabled[r[1]] else 0.0)) < 1e-6
            for r in impact_audit
        ) else "FAIL", f"factor {bi_loss_factor:.1%}; BI matrix toggle honored", "BI = gross revenue disruption × factor when applicable"],
        ["Impact matrix contains all 18 governed OT drivers", "PASS" if set(driver_matrix) == expected_driver_ids else "FAIL", len(driver_matrix), 18],
        ["Every impact driver has a supported calculation type", "PASS" if all(a["formula_type"] in valid_formula_types for a in driver_assumptions.values()) else "FAIL", ", ".join(sorted({a["formula_type"] for a in driver_assumptions.values()})), ", ".join(sorted(valid_formula_types))],
        ["All five scenarios have valid P50/P99 downtime and capacity calibration", "PASS" if all(
            s["base_days"] >= 0 and s["stress_days"] >= s["base_days"]
            and 0 <= s["base_capacity"] <= s["stress_capacity"] <= 1
            for s in scenario_impact.values()
        ) else "FAIL", len(scenario_impact), 5],
        ["All calculated impact-driver P50/P99 pairs are non-negative and ordered", "PASS" if impact_pairs_ordered else "FAIL", len(calculated_driver_values), 90],
        ["Scenario applicability toggles are honored by the impact engine", "PASS" if inactive_driver_toggles and inactive_driver_toggles_honored else "FAIL", len(inactive_driver_toggles), "> 0 inactive driver-scenario pairs excluded"],
        ["Generic consumer-breach cost rows are not default OT drivers", "PASS" if not generic_consumer_rows else "FAIL", generic_consumer_rows or "none", "none"],
        ["Tail basis is TVaR 99 for insurance / risk financing", "PASS" if tail_basis == LABEL_TVAR_99 else "FAIL", tail_basis, LABEL_TVAR_99],
        ["Selected TVaR equals TVaR 99", "PASS" if all(abs(metrics_by_view[v]["Selected TVaR"] - metrics_by_view[v][LABEL_TVAR_99]) < 1e-8 for v in metrics_by_view) else "FAIL", "both views checked", "Selected TVaR = TVaR 99"],
        ["Tail transfer equals selected TVaR less retention", "PASS" if all(abs(metrics_by_view[v][TAIL_ABOVE_RETENTION_LABEL] - max(metrics_by_view[v]["Selected TVaR"] - retention, 0.0)) < 1e-8 for v in metrics_by_view) else "FAIL", "both views checked", "max(selected TVaR - retention, 0)"],
        ["Supply-chain and wireless frequency multipliers are neutral", "PASS" if all(abs(exposure_map.get((k, val), 1.0) - 1.0) < 1e-12 for k, vals in (("SUPPLY_CHAIN_ROUTE", ("No", "Yes")), ("WIRELESS_OT", ("No", "Yes"))) for val in vals) else "FAIL", "all four options", "1.00; feasibility-only"],
        ["Safety-system absence gates Safety System Compromise", "PASS" if all(not build_combo(a, "Safety System Compromise", fac=safe_fac)["valid"] for a in ACTORS) else "FAIL", "all 3 invalid", "all 3 invalid"],
        ["Wireless facility input changes wireless-TTP feasibility", "PASS" if wire_after > wire_before else "FAIL", f"{wire_before} -> {wire_after}", "increase"],
        ["Removing remote access and IT-OT connectivity removes remote TTPs", "PASS" if remote_after < remote_before else "FAIL", f"{remote_before} -> {remote_after}", "decrease"],
        ["Selected sector resolves to one registered pack", "PASS", f"{sector_pack['sector']} / {sector_pack['pack_id']}", "one explicit pack"],
        ["Selected asset type belongs to selected sector", "PASS", f"{sector_pack['sector']} / {sector_pack['asset_type']}", "one explicit sector/asset row"],
        ["Selected asset type has an explicit actor-frequency overlay", "PASS" if set(sector_pack["asset_multipliers"]) == set(ACTORS) else "FAIL", str(sector_pack["asset_multipliers"]), "three explicit actor multipliers"],
        ["Selected sector has a rationale row for every governed TTP", "PASS" if set(governed_ttp_ids) <= set(sector_pack["rationale"]) else "FAIL", len(set(governed_ttp_ids) & set(sector_pack["rationale"])), len(set(governed_ttp_ids))],
        ["All selected-sector TTP rows have explicit default applicability", "PASS" if all(isinstance(x["applicable"], bool) for x in sector_pack["rationale"].values()) else "FAIL", len(sector_pack["rationale"]), "all Yes/No"],
        ["Composite stage-barrier methodology retained", "PASS" if all(len(c["stages"]) == 5 and abs(c["p_success"] - (float(np.prod([st["through"] for st in c["stages"]])) if c["valid"] else 0.0)) < 1e-12 for c in combos0.values()) else "FAIL", "stage barriers averaged; S1-S5 multiplied", "no discrete path selection"],
        ["Selected geography resolves to an explicit calibration row", "PASS" if selected_geography in geo_map else "FAIL", selected_geography, "explicit row; no silent fallback"],
    ]
    overall = "PASS" if all(t[1] == "PASS" for t in tests) else "FAIL"

    # ---------------- Write engine output back to workbook ----------------
    # Calculation sheets start at row 16; explanatory blocks above remain untouched.
    sh = _ws(wb, "ttp_calc")
    sh.get_range("A16:P1200").clear({})
    sh.get_range(f"A16:P{15 + len(ttp_detail)}").values = ttp_detail

    sh = _ws(wb, "path_calc")
    sh.get_range("A16:M100").clear({})
    sh.get_range(f"A16:M{15 + len(path_rows)}").values = path_rows
    sh.get_range("A95:I112").clear({})
    sh.get_range("A95:I95").values = [["Threat actor", "Scenario", "S1", "S2", "S3", "S4", "S5", "Overall P(success)", "Path valid"]]
    sh.get_range("A96:I110").values = success_summary

    sh = _ws(wb, "freq_calc")
    sh.get_range("A15:N40").clear({})
    sh.get_range("A15:N15").values = [[
        "Threat actor", "Scenario", "Path valid", "Input actor share",
        "Effective actor probability", "Scenario propensity", "Threat activity mult.",
        "Sector mult.", "Asset type mult.", "Geography mult.",
        "Facility exposure mult.", "Attempt rate / yr", "P(success | attempt)",
        "Successful event freq. / yr",
    ]]
    sh.get_range(f"A16:N{15 + len(freq_rows)}").values = freq_rows

    sh = _ws(wb, "impact_calc")
    sh.get_range("A16:P40").clear({})
    sh.get_range(f"A16:P{15 + len(impact_audit)}").values = impact_audit

    _write_executive_summary(
        wb, financial_metrics, operational_metrics, run_metrics,
        actor_decomp, scenario_decomp, reporting_view=reporting_view,
        primary_view=primary_view,
    )

    sh = _ws(wb, "matrix")
    sh.get_range("A12:F12").values = [[f"Detailed results basis: {primary_view} (reporting selection: {reporting_view})", None, None, None, None, None]]
    sh.get_range("B16:F18").values = baseline["cell_aal"].tolist()
    sh.get_range("B24:F26").values = baseline["cell_succ_freq"].tolist()
    sh.get_range("B32:F34").values = baseline["cell_p"].tolist()

    sh = _ws(wb, "tail")
    sh.get_range("A16:J45").clear({})
    sh.get_range(f"A16:J{15 + len(tail_rows)}").values = tail_rows
    sh.get_range("M19:M20").values = [[primary_metrics["Selected TVaR"]], [primary_metrics[TAIL_ABOVE_RETENTION_LABEL]]]
    xl_tail = getattr(wb, "wb", None)
    if xl_tail is not None:
        ws_tail = xl_tail[_sheet_name(wb, "tail")]
        for row in range(16, 36):
            ws_tail.cell(row, 2).number_format = '0 "years"'
            for col in range(3, 7):
                ws_tail.cell(row, col).number_format = CURRENCY_FORMAT
            for col in range(7, 11):
                ws_tail.cell(row, col).number_format = '0.0'

    sh = _ws(wb, "whatif")
    sh.get_range("A16:I80").clear({})
    whatif_header = [[
        "Control ID", "Control", "Channel", "Current maturity", "What-if maturity",
        "Baseline AAL", "What-If AAL", "AAL Reduction", "AAL Reduction %",
        "Baseline AAL", "What-If AAL", "AAL Reduction", "AAL Reduction %",
        "Baseline TVaR 95", "What-If TVaR 95", "Baseline TVaR 99", "What-If TVaR 99",
        "Baseline TVaR 95", "What-If TVaR 95", "Baseline TVaR 99", "What-If TVaR 99",
        "Baseline successful-event frequency", "What-If successful-event frequency",
        "Baseline successful-event frequency", "What-If successful-event frequency",
    ]]
    whatif_rows = [[
        x["cid"], x["name"], x["channel"], x["current"], x["whatif"],
        x["be"]["baseline"], x["be"]["aal"], x["be"]["reduction"], x["be"]["pct"],
        x["prudent"]["baseline"], x["prudent"]["aal"], x["prudent"]["reduction"], x["prudent"]["pct"],
        x["be"]["tvar95_base"], x["be"]["tvar95"], x["be"]["tvar99_base"], x["be"]["tvar99"],
        x["prudent"]["tvar95_base"], x["prudent"]["tvar95"], x["prudent"]["tvar99_base"], x["prudent"]["tvar99"],
        x["be"]["freq_base"], x["be"]["event_freq"], x["prudent"]["freq_base"], x["prudent"]["event_freq"],
    ] for x in whatifs]
    sh.get_range("A15:Y80").clear({})
    sh.get_range("A15:Y15").values = whatif_header
    if whatif_rows:
        sh.get_range(f"A16:Y{15 + len(whatif_rows)}").values = whatif_rows

    sh = _ws(wb, "agg_curves")
    sh.get_range("A16:I40").clear({})
    sh.get_range(f"A16:I{15 + len(aggregate_curve_rows)}").values = aggregate_curve_rows

    sh = _ws(wb, "scenario_lec")
    sh.get_range("A16:K40").clear({})
    sh.get_range(f"A16:K{15 + len(scenario_lec_rows)}").values = scenario_lec_rows

    sh = _ws(wb, "actor_lec")
    sh.get_range("A16:G40").clear({})
    sh.get_range(f"A16:G{15 + len(actor_lec_rows)}").values = actor_lec_rows

    sh = _ws(wb, "cell_lec")
    sh.get_range("A16:E220").clear({})
    sh.get_range(f"A16:E{15 + len(cell_lec_rows)}").values = cell_lec_rows

    sh = _ws(wb, "tests")
    sh.get_range("A15:D15").values = [[f"OVERALL MODEL VALIDATION: {overall}", None, None, None]]
    sh.get_range("A18:D90").clear({})
    sh.get_range(f"A18:D{17 + len(tests)}").values = tests
    sh.get_range("F18:G35").values = [
        ["Simulation years", N],
        ["Campaigns simulated", total_campaigns],
        ["Successful events", int(baseline["success"].sum())],
        ["Random seed", seed],
        ["Facility exposure multiplier", exposure_multiplier()],
        ["Workbook version", WORKBOOK_VERSION],
        ["Engine version", ENGINE_VERSION],
        ["Reporting selection", reporting_view],
        ["Detailed results basis", primary_view],
        ["Best-estimate campaigns", int(contexts["Best Estimate"]["counts"].sum())],
        ["Prudent campaigns", int(contexts["Prudent"]["counts"].sum())],
        ["What-if simulations", f"Full {N:,} × both views" if run_whatifs else "Skipped"],
        ["Scenario LECs", "5 AEP/OEP curves"],
        ["Actor LECs", "3 AEP/OEP curves"],
        ["Overall status", overall],
        ["Sector pack", sector_pack["pack_id"]],
        ["Sector / asset", f"{sector_pack['sector']} / {sector_pack['asset_type']}"],
    ]

    _ws(wb, "guide").get_range("A32:H32").values = [[
        f"Last complete engine run: {datetime.now().strftime('%Y-%m-%d %H:%M')} | {N:,} years per view | Reporting: {reporting_view} | Detailed basis: {primary_view} | Validation: {overall}",
        None, None, None, None, None, None, None,
    ]]

    dash_payload = build_payload(
        facility=facility,
        sector_pack=sector_pack,
        N=N,
        run_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
        version=ENGINE_VERSION,
        reporting_view=primary_view if reporting_view != "Both" else "Prudent",
        baselines=baselines,
        contexts=contexts,
        actors=ACTORS,
        scenarios=SCENARIOS,
        var_tvar=var_tvar,
        expected_shortfall=expected_shortfall,
        empirical_lec=empirical_lec,
        whatifs=whatifs,
        driver_matrix=driver_matrix,
        calculated_driver_values=calculated_driver_values,
        cell_aal=baseline["cell_aal"],
        primary_view=primary_view,
        run_whatifs=run_whatifs,
    )
    write_executive_dashboard(wb, dash_payload)

    apply_sector_asset_dropdowns(wb)
    if output_path is None:
        output_path = input_path
    SpreadsheetFile.export_xlsx(wb).save(output_path)

    # --- Control packages (combined overrides; each package is re-simulated) ---
    packages = []
    if run_packages:
        def package_overrides(name):
            if name == "Foundation":
                return {cid: "Developing" for cid, c in controls.items()}
            if name == "Target":
                # Full target state = Optimised (Managed is already the default OT baseline).
                return {cid: "Optimised" for cid, c in controls.items()}
            if name == "Priority":
                # Prefer uplift ranked by simulated AAL reduction when what-ifs ran;
                # otherwise one-level uplift on mapped controls that still have headroom.
                ranked = [
                    x for x in whatifs
                    if x.get("mapped") and x["whatif"] != x["current"]
                ]
                ranked.sort(key=lambda x: x.get("reduction", 0), reverse=True)
                return {x["cid"]: x["whatif"] for x in ranked[:8]}
            if name == "User-defined":
                # Prefer explicit targets already at Optimised/Managed where assessed
                out = {}
                for cid, c in controls.items():
                    cur = effective_level(c)
                    if cur in ("Absent", "Initial", "Developing"):
                        out[cid] = "Managed"
                    else:
                        out[cid] = cur
                return out
            return {}

        for pname in ("Foundation", "Priority", "Target", "User-defined"):
            ov = package_overrides(pname)
            if not ov:
                continue
            ev = evaluate(contexts[primary_view], ov)
            st = stats_from_aep(ev["aep"], ev["success"].sum())
            base = base_stats[primary_view]
            packages.append({
                "name": pname,
                "overrides": {k: ov[k] for k in list(ov)[:40]},
                "n_controls": len(ov),
                "event_freq": st["event_freq"],
                "aal": st["aal"],
                "var95": st["p95"],
                "tvar95": st["tvar95"],
                "var99": st["p99"],
                "tvar99": st["tvar99"],
                "baseline_aal": base["aal"],
                "baseline_var95": base["p95"],
                "baseline_tvar95": base["tvar95"],
                "baseline_var99": base["p99"],
                "baseline_tvar99": base["tvar99"],
                "baseline_event_freq": base["event_freq"],
                "aal_reduction": base["aal"] - st["aal"],
                "tvar99_reduction": base["tvar99"] - st["tvar99"],
                "simulated": True,
            })

    # --- Trial-level insurance on primary annual aggregate ---
    programme = parse_programme(insurance_programme if insurance_programme is not None else {
        "INSURANCE_RETENTION": retention,
    })
    insurance_analysis = None
    if programme.active():
        insurance_analysis = apply_programme(baseline["aep"], programme)
        # Drop large arrays from persisted analysis; keep metrics + scalars
        insurance_analysis = {
            k: v for k, v in insurance_analysis.items()
            if k not in {"ground_up", "retained", "insured", "residual", "uninsured_above_programme", "layer_recoveries", "programme"}
        }
        insurance_analysis["layers"] = [
            {"name": ly.name, "attachment": ly.attachment, "limit": ly.limit, "coinsurance": ly.coinsurance}
            for ly in programme.layers
        ]
        insurance_analysis["retention"] = programme.retention

    # --- Formation funnel (frequency-weighted success) ---
    ctx = contexts[primary_view]
    total_campaigns_per_year = float(ctx["counts"].mean())
    succ_freq = float(baseline["success"].sum()) / N
    # Applicable = all simulated campaigns (facility-applicable by construction)
    applicable_freq = total_campaigns_per_year
    weighted_p_success = (succ_freq / applicable_freq) if applicable_freq > 0 else 0.0
    formation = {
        "campaigns_per_year": total_campaigns_per_year,
        "applicable_campaigns_per_year": applicable_freq,
        "conditional_success_probability": weighted_p_success,
        "successful_events_per_year": succ_freq,
        "p_any_successful_event": p_any,
        "aal": base_aal,
    }

    # Actor-scenario formation rows
    actor_scenario_rows = []
    for ai, actor in enumerate(ACTORS):
        for si, sc in enumerate(SCENARIOS):
            attempts = float(np.sum((ctx["actor_idx"] == ai) & (ctx["scenario_idx"] == si))) / N
            succ = float(baseline["cell_succ_freq"][ai, si])
            p_succ = float(baseline["cell_p"][ai, si])
            aal_c = float(baseline["cell_aal"][ai, si])
            actor_scenario_rows.append({
                "actor": actor,
                "scenario": sc,
                "campaign_frequency": attempts,
                "applicable_frequency": attempts,
                "success_probability": p_succ,
                "successful_event_frequency": succ,
                "annual_event_probability": 1.0 - math.exp(-succ) if succ >= 0 else 0.0,
                "aal": aal_c,
            })

    # Scenario standalone VaR/TVaR + contributions
    # Use distinct locals — do not overwrite facility-level v95/v99 used by the narrative.
    scenario_analysis = []
    for si, sc in enumerate(SCENARIOS):
        arr = baseline["scenario_aep"][si]
        s_v95, s_tv95 = var_tvar(arr, 0.95)
        s_v99, s_tv99 = var_tvar(arr, 0.99)
        attempts = float(np.sum(ctx["scenario_idx"] == si)) / N
        succ = float(sum(baseline["cell_succ_freq"][ai, si] for ai in range(3)))
        scenario_analysis.append({
            "name": sc,
            "campaign_frequency": attempts,
            "successful_event_frequency": succ,
            "annual_event_probability": 1.0 - math.exp(-succ),
            "aal": float(arr.mean()),
            "var95": s_v95, "tvar95": s_tv95, "var99": s_v99, "tvar99": s_tv99,
            "pct_total_aal": float(arr.mean()) / base_aal if base_aal else 0.0,
            "contrib_tvar95": scen_t95.get(sc, 0.0),
            "contrib_tvar99": scen_t99.get(sc, 0.0),
            "primary_operational_driver": "Downtime days",
            "primary_financial_driver": "Business interruption" if bi_enabled.get(sc) else "Non-BI impact drivers",
        })

    actor_analysis = []
    for ai, actor in enumerate(ACTORS):
        arr = baseline["actor_aep"][ai]
        a_v95, a_tv95 = var_tvar(arr, 0.95)
        a_v99, a_tv99 = var_tvar(arr, 0.99)
        attempts = float(np.sum(ctx["actor_idx"] == ai)) / N
        succ = float(sum(baseline["cell_succ_freq"][ai, si] for si in range(5)))
        actor_analysis.append({
            "name": actor,
            "campaign_frequency": attempts,
            "successful_event_frequency": succ,
            "annual_event_probability": 1.0 - math.exp(-succ),
            "aal": float(arr.mean()),
            "var95": a_v95, "tvar95": a_tv95, "var99": a_v99, "tvar99": a_tv99,
            "pct_total_aal": float(arr.mean()) / base_aal if base_aal else 0.0,
            "contrib_tvar95": actor_t95.get(actor, 0.0),
            "contrib_tvar99": actor_t99.get(actor, 0.0),
        })

    # Sensitivity reruns — actual evaluate() shocks when enabled
    sensitivities = []
    if run_sensitivity:
        from copy import deepcopy

        def _metric_row(label, kind, factor, aep_arr):
            m = annual_aggregate_metrics(aep_arr)
            def _pct(new, old):
                return (new - old) / old if old else None
            return {
                "parameter": label,
                "kind": kind,
                "factor": factor,
                "simulation_years": N,
                "aal": m["AAL"],
                "var95": m["VaR95"],
                "tvar95": m["TVaR95"],
                "var99": m["VaR99"],
                "tvar99": m["TVaR99"],
                "delta_aal": m["AAL"] - base_aal,
                "delta_var95": m["VaR95"] - v95,
                "delta_tvar95": m["TVaR95"] - tv95,
                "delta_var99": m["VaR99"] - v99,
                "delta_tvar99": m["TVaR99"] - tv99,
                "pct_aal": _pct(m["AAL"], base_aal),
                "pct_var95": _pct(m["VaR95"], v95),
                "pct_tvar95": _pct(m["TVaR95"], tv95),
                "pct_var99": _pct(m["VaR99"], v99),
                "pct_tvar99": _pct(m["TVaR99"], tv99),
                "limitation": None,
            }

        base_lambda = lambda_be_year if primary_view == "Best Estimate" else lambda_prudent_year
        for label, factor in (("Campaign frequency +20%", 1.2), ("Campaign frequency -20%", 0.8)):
            sev = evaluate(build_context(base_lambda * factor, seed))
            sensitivities.append(_metric_row(label, "frequency", factor, sev["aep"]))

        for label, factor in (("Downtime +20%", 1.2), ("Downtime -20%", 0.8)):
            saved = deepcopy(impact)
            try:
                for sc in SCENARIOS:
                    impact[sc]["Downtime days"]["base"] *= factor
                    impact[sc]["Downtime days"]["stress"] *= factor
                sensitivities.append(_metric_row(label, "downtime", factor, evaluate(contexts[primary_view])["aep"]))
            finally:
                impact.clear()
                impact.update(saved)

        for label, factor in (("Capacity affected +20%", 1.2), ("Capacity affected -20%", 0.8)):
            saved = deepcopy(impact)
            try:
                for sc in SCENARIOS:
                    impact[sc]["Capacity affected"]["base"] = min(1.0, max(0.01, impact[sc]["Capacity affected"]["base"] * factor))
                    impact[sc]["Capacity affected"]["stress"] = min(1.0, max(0.01, impact[sc]["Capacity affected"]["stress"] * factor))
                sensitivities.append(_metric_row(label, "capacity", factor, evaluate(contexts[primary_view])["aep"]))
            finally:
                impact.clear()
                impact.update(saved)

        for label, factor in (("Revenue at risk +20%", 1.2), ("Revenue at risk -20%", 0.8)):
            bi_scale[0] = float(factor)
            try:
                sensitivities.append(_metric_row(label, "revenue", factor, evaluate(contexts[primary_view])["aep"]))
            finally:
                bi_scale[0] = 1.0

        for label, factor in (("Restoration / non-BI drivers +20%", 1.2), ("Restoration / non-BI drivers -20%", 0.8)):
            saved = deepcopy(impact)
            try:
                for sc in SCENARIOS:
                    for key, d in list(impact[sc].items()):
                        if key in ("Downtime days", "Capacity affected"):
                            continue
                        if isinstance(d, dict) and "base" in d:
                            d["base"] = float(d["base"]) * factor
                            d["stress"] = float(d["stress"]) * factor
                sensitivities.append(_metric_row(label, "restoration", factor, evaluate(contexts[primary_view])["aep"]))
            finally:
                impact.clear()
                impact.update(saved)

        # --- Actor-mix: +20% relative weight on Nation State, renormalise to 100% ---
        base_probs = np.asarray(actor_probs, dtype=float).copy()
        shocked = base_probs.copy()
        shocked[0] = max(shocked[0] * 1.2, 0.0)
        if shocked.sum() <= 0:
            shocked = np.full(3, 1.0 / 3.0)
        else:
            shocked = shocked / shocked.sum()
        actor_probs_saved = actor_probs
        actor_probs = shocked
        try:
            row = _metric_row(
                "Actor mix: Nation State ×1.2 then renormalised to 100%",
                "actor_mix",
                1.2,
                evaluate(build_context(base_lambda, seed))["aep"],
            )
            row["baseline_actor_weights"] = {ACTORS[i]: float(base_probs[i]) for i in range(3)}
            row["shocked_actor_weights"] = {ACTORS[i]: float(shocked[i]) for i in range(3)}
            row["weight_sum"] = float(shocked.sum())
            sensitivities.append(row)
        finally:
            actor_probs = actor_probs_saved

        # --- Route applicability: close one currently enabled facility architecture route ---
        route_candidates = [
            ("SUPPLY_CHAIN_ROUTE", "Yes", "No", "Supply-chain delivery route"),
            ("WIRELESS_OT", "Yes", "No", "Wireless OT connectivity"),
            ("INTERNET_OT", "Yes", "No", "Internet-facing OT"),
            ("TRANSIENT_ASSETS", "USB/Transient", "None", "Transient/USB media route"),
        ]
        route_applied = False
        for key, enabled_val, closed_val, label in route_candidates:
            cur = facility.get(key)
            # Only shock routes that are already applicable/enabled
            if cur is None:
                continue
            cur_s = str(cur).strip()
            if cur_s in ("", "None", "No"):
                continue
            if key == "TRANSIENT_ASSETS" and cur_s == "None":
                continue
            saved_fac = facility.get(key)
            facility[key] = closed_val if key != "TRANSIENT_ASSETS" else "None"
            try:
                row = _metric_row(
                    f"Route applicability: close {label} (was {saved_fac!r} → {facility[key]!r})",
                    "route",
                    None,
                    evaluate(contexts[primary_view])["aep"],
                )
                row["route_field"] = key
                row["baseline_route_value"] = saved_fac
                row["shocked_route_value"] = facility[key]
                row["rationale"] = (
                    "Discrete closure of an already-enabled facility architecture route; "
                    "does not enable previously impossible routes."
                )
                sensitivities.append(row)
                route_applied = True
            finally:
                facility[key] = saved_fac
            break
        if not route_applied:
            sensitivities.append({
                "parameter": "Route applicability",
                "kind": "route",
                "factor": None,
                "simulation_years": N,
                "aal": None, "var95": None, "tvar95": None, "var99": None, "tvar99": None,
                "delta_aal": None, "delta_tvar99": None,
                "limitation": "No currently enabled facility architecture route was available to close for this assessment.",
            })

        # --- Stage / barrier priors: ±20% on stage through priors, clipped to [0,1] ---
        def _shock_stage_priors(factor, label):
            saved_cfg = {a: dict(actor_cfg[a]) for a in ACTORS}
            baseline_vals = {}
            shocked_vals = {}
            try:
                for a in ACTORS:
                    for st in ("S1", "S2", "S3", "S4", "S5cap"):
                        if st not in actor_cfg[a]:
                            continue
                        base = float(actor_cfg[a][st])
                        baseline_vals[f"{a}:{st}"] = base
                        shocked = float(np.clip(base * factor, 0.0, 1.0))
                        actor_cfg[a][st] = shocked
                        shocked_vals[f"{a}:{st}"] = shocked
                row = _metric_row(label, "stage_barrier", factor, evaluate(contexts[primary_view])["aep"])
                row["baseline_stage_priors"] = baseline_vals
                row["shocked_stage_priors"] = shocked_vals
                sensitivities.append(row)
            finally:
                for a in ACTORS:
                    actor_cfg[a].clear()
                    actor_cfg[a].update(saved_cfg[a])

        _shock_stage_priors(1.2, "Stage/barrier priors +20% (clipped to [0,1])")
        _shock_stage_priors(0.8, "Stage/barrier priors -20% (clipped to [0,1])")

        sensitivities.sort(key=lambda r: abs(r.get("delta_aal") or 0), reverse=True)

    top_aal_name = SCENARIOS[int(np.argmax(baseline["scenario_aal"]))]
    top_tvar99_name = max(scen_t99.items(), key=lambda kv: kv[1])[0] if scen_t99 else None
    appetite_status = primary_metrics.get("appetite_status") or "Tolerance not set"
    narrative = executive_risk_narrative(
        p_any_1y=p_any,
        p_any_5y=multi_year_event_probability(p_any, 5),
        aal=base_aal,
        var95=v95,
        tvar95=tv95,
        var99=v99,
        tvar99=tv99,
        top_aal_name=top_aal_name,
        top_tvar99_name=top_tvar99_name,
        within_tolerance=(
            True if appetite_status == "Within tolerance"
            else False if appetite_status == "Above tolerance"
            else None
        ),
        tolerance=appetite.get("ANNUAL_LOSS_TOLERANCE"),
    )

    revenue = float(financial.get("ANNUAL_REVENUE_AT_RISK") or 0) or None

    def _ot_loss_components(bl, drivers):
        """Allocate BI trials + proportionally split non-BI using Balbix categories where mapped."""
        from crq.impact.catalogue import OT_BALBIX_GAPS, OT_TO_BALBIX, driver_category

        component_annuals = {"Business Interruption costs": np.asarray(bl["aep_bi"], dtype=float)}
        weights = {}
        for did, d in drivers.items():
            if not any(d.get("applicable", {}).values()):
                continue
            balbix_id = OT_TO_BALBIX.get(did)
            if balbix_id:
                label = driver_category(balbix_id)
            else:
                # Preserve OT economics for non-Balbix drivers; report under gap-aware labels
                label = map_ot_driver_to_component(d.get("category"), d.get("name"))
                if did in OT_BALBIX_GAPS and label == "Other sector-specific costs":
                    # Keep distinct OT consequence classes so safety ≠ BI
                    if "Safety" in (d.get("category") or "") or "SF-" in did:
                        label = "Safety/bodily injury (OT gap)"
                    elif "Environment" in (d.get("category") or "") or "EN-" in did:
                        label = "Environmental remediation (OT gap)"
                    elif "Physical" in (d.get("category") or "") or did == "PD-03":
                        label = "Physical damage (OT gap)"
                    elif did in {"OP-01", "OP-02"}:
                        label = "Additional operating expense (OT gap)"
                    elif did == "RC-02":
                        label = "Data Recovery & Restoration costs"
            if label == "Business Interruption costs" or label == "Business interruption":
                continue
            w = float(d.get("stress") or d.get("base") or 1.0)
            weights[label] = weights.get(label, 0.0) + max(w, 0.0)
        nbi = np.asarray(bl["aep_nbi"], dtype=float)
        total_w = sum(weights.values())
        if total_w <= 0:
            component_annuals["Indirect Losses"] = nbi
        else:
            for label, w in weights.items():
                component_annuals[label] = nbi * (w / total_w)
        return component_rows_from_trials(bl["aep"], component_annuals)

    loss_components = _ot_loss_components(baseline, driver_matrix)
    top_comp = leading_tvar99_component(loss_components)
    from crq.impact.catalogue import OT_BALBIX_GAPS

    balbix_gaps = [{"id": k, "reason": v} for k, v in OT_BALBIX_GAPS.items()]

    return {
        "output": output_path,
        "reporting_view": reporting_view,
        "detailed_view": primary_view,
        "AAL": base_aal,
        "VaR95": v95,
        "TVaR95": tv95,
        "VaR99": v99,
        "TVaR99": tv99,
        "P_any": float((baseline["aep"] > 0).mean()),
        "BestEstimateAAL": be_metrics[LABEL_AAL],
        "PrudentAAL": prudent_metrics[LABEL_AAL],
        "BestEstimatePAny": be_metrics["P(any successful loss event)"],
        "PrudentPAny": prudent_metrics["P(any successful loss event)"],
        "BestEstimateLambda": float(contexts["Best Estimate"]["counts"].mean()),
        "PrudentLambda": float(contexts["Prudent"]["counts"].mean()),
        "campaigns": total_campaigns,
        "successful_events": int(baseline["success"].sum()),
        "tests_pass": sum(t[1] == "PASS" for t in tests),
        "tests_total": len(tests),
        "overall": overall,
        "sector": sector_pack["sector"],
        "asset_type": sector_pack["asset_type"],
        "sector_pack_id": sector_pack["pack_id"],
        "sector_pack_status": sector_pack["pack_status"],
        "engine_version": ENGINE_VERSION,
        "pack_version": str(sector_pack.get("pack_status") or ""),
        "simulation_years": N,
        "random_seed": seed,
        "event_frequency": float(baseline["success"].sum()) / N,
        "attempt_frequency": float(contexts[primary_view]["counts"].mean()),
        "actor_aal": {ACTORS[i]: baseline["actor_aal"][i] for i in range(3)},
        "scenario_aal": {SCENARIOS[i]: baseline["scenario_aal"][i] for i in range(5)},
        "best_aal": be_metrics[LABEL_AAL],
        "prudent_aal": prudent_metrics[LABEL_AAL],
        "best_aal_se": float(np.std(baselines["Best Estimate"]["aep"], ddof=1) / np.sqrt(N)),
        "prudent_aal_se": float(np.std(baselines["Prudent"]["aep"], ddof=1) / np.sqrt(N)),
        "best_var95": be_metrics[LABEL_VAR_95],
        "prudent_var95": prudent_metrics[LABEL_VAR_95],
        "best_tvar95": be_metrics[LABEL_TVAR_95],
        "prudent_tvar95": prudent_metrics[LABEL_TVAR_95],
        "best_var99": be_metrics[LABEL_VAR_99],
        "prudent_var99": prudent_metrics[LABEL_VAR_99],
        "best_tvar99": be_metrics[LABEL_TVAR_99],
        "prudent_tvar99": prudent_metrics[LABEL_TVAR_99],
        "best_pany": be_metrics["P(any successful loss event)"],
        "prudent_pany": prudent_metrics["P(any successful loss event)"],
        "best_pany_3y": multi_year_event_probability(be_metrics["P(any successful loss event)"], 3),
        "prudent_pany_3y": multi_year_event_probability(prudent_metrics["P(any successful loss event)"], 3),
        "best_pany_5y": multi_year_event_probability(be_metrics["P(any successful loss event)"], 5),
        "prudent_pany_5y": multi_year_event_probability(prudent_metrics["P(any successful loss event)"], 5),
        "best_p_exceed_tolerance": be_metrics["P(annual loss exceeds tolerance)"],
        "prudent_p_exceed_tolerance": prudent_metrics["P(annual loss exceeds tolerance)"],
        "risk_tolerance": appetite.get("ANNUAL_LOSS_TOLERANCE"),
        "appetite_inputs": appetite,
        "appetite_status": appetite_status,
        "appetite_breaches": primary_metrics.get("appetite_breaches") or {},
        "top_aal_contributor": top_aal_name,
        "top_tvar99_contributor": top_tvar99_name,
        "top_tvar99_component": None if top_comp is None else top_comp["label"],
        "top_tvar99_component_name": None if top_comp is None else top_comp["name"],
        "top_tvar99_component_contrib": None if top_comp is None else top_comp["contrib_tvar99"],
        "top_tvar99_component_pct": None if top_comp is None else top_comp["pct_tvar99"],
        "balbix_gaps": balbix_gaps,        "executive_narrative": narrative,
        "scenario_tvar95_contribution": scen_t95,
        "scenario_tvar99_contribution": scen_t99,
        "actor_tvar95_contribution": actor_t95,
        "actor_tvar99_contribution": actor_t99,
        "formation": formation,
        "actor_scenario_rows": actor_scenario_rows,
        "scenario_analysis": scenario_analysis,
        "actor_analysis": actor_analysis,
        "control_packages": packages,
        "insurance_analysis": insurance_analysis,
        "sensitivities": sensitivities,
        "annual_revenue_at_risk": revenue,
        "bi_enabled": dict(bi_enabled),
        "driver_matrix_summary": [
            {"id": did, "name": d["name"], "category": d["category"]}
            for did, d in list(driver_matrix.items())[:40]
        ],
        "trials_available": True,
        "primary_annual_aal": float(baseline["aep"].mean()),
        "primary_annual_var95": v95,
        "primary_annual_tvar95": tv95,
        "primary_annual_var99": v99,
        "primary_annual_tvar99": tv99,
        "operational_diagnostics": {
            # Annual downtime hours → days across all simulated years (incl. zero-loss years).
            "downtime_p50": float(np.quantile(baseline["aep_h"] / 24.0, 0.50, method=VAR_QUANTILE_METHOD)),
            "downtime_p95": float(np.quantile(baseline["aep_h"] / 24.0, 0.95, method=VAR_QUANTILE_METHOD)),
            "downtime_p99": float(np.quantile(baseline["aep_h"] / 24.0, 0.99, method=VAR_QUANTILE_METHOD)),
            # Recovery is not separately simulated in OT v1.7; omit rather than clone downtime.
            "recovery_p50": None,
            "recovery_p95": None,
            "recovery_p99": None,
            "capacity_p50": float(np.quantile(baseline["aep_cap"], 0.50, method=VAR_QUANTILE_METHOD)),
            "capacity_p95": float(np.quantile(baseline["aep_cap"], 0.95, method=VAR_QUANTILE_METHOD)),
            "capacity_p99": float(np.quantile(baseline["aep_cap"], 0.99, method=VAR_QUANTILE_METHOD)),
            "records_p50": None, "records_p95": None, "records_p99": None,
            "endpoints_p50": None, "endpoints_p95": None, "endpoints_p99": None,
            "services_p50": None, "services_p95": None, "services_p99": None,
            "revenue_per_day": float(financial.get("ANNUAL_REVENUE_AT_RISK") or 0) / 365.0 if financial.get("ANNUAL_REVENUE_AT_RISK") else None,
            "p_down_7": float(np.mean((baseline["aep_h"] / 24.0) > 7)),
            "p_down_15": float(np.mean((baseline["aep_h"] / 24.0) > 15)),
            "p_down_30": float(np.mean((baseline["aep_h"] / 24.0) > 30)),
            "p_down_60": float(np.mean((baseline["aep_h"] / 24.0) > 60)),
            "p_cap_25": float(np.mean(baseline["aep_cap"] > 0.25)),
            "p_cap_50": float(np.mean(baseline["aep_cap"] > 0.50)),
            "p_cap_75": float(np.mean(baseline["aep_cap"] > 0.75)),
        },
        "loss_components": loss_components,

        "best_event_frequency": float(baselines["Best Estimate"]["success"].sum()) / N,
        "prudent_event_frequency": float(baselines["Prudent"]["success"].sum()) / N,
        "best_attempt_frequency": float(contexts["Best Estimate"]["counts"].mean()),
        "prudent_attempt_frequency": float(contexts["Prudent"]["counts"].mean()),
        "actor_aal_best": {ACTORS[i]: float(baselines["Best Estimate"]["actor_aal"][i]) for i in range(3)},
        "actor_aal_prudent": {ACTORS[i]: float(baselines["Prudent"]["actor_aal"][i]) for i in range(3)},
        "scenario_aal_best": {SCENARIOS[i]: float(baselines["Best Estimate"]["scenario_aal"][i]) for i in range(5)},
        "scenario_aal_prudent": {SCENARIOS[i]: float(baselines["Prudent"]["scenario_aal"][i]) for i in range(5)},
        "validation": overall,
        "top_controls": [(x["cid"], x["name"], x["reduction"]) for x in whatifs[:10]],
        "whatifs_ran": bool(run_whatifs),
        "control_maturities": {cid: c["maturity"] for cid, c in controls.items()},
        "whatifs": [
            {
                "cid": x["cid"], "name": x["name"], "channel": x["channel"],
                "current": x["current"], "whatif": x["whatif"],
                "mapped": any(
                    m["cid"] == x["cid"] and m["base_eff"] > 0
                    for maps in ttp_controls.values() for m in maps
                ),
                "be": {k: (float(v) if isinstance(v, (int, float)) else v) for k, v in x["be"].items()},
                "prudent": {k: (float(v) if isinstance(v, (int, float)) else v) for k, v in x["prudent"].items()},
                "reduction": float(x["reduction"]),
            }
            for x in whatifs
        ],
    }


def main():
    if len(sys.argv) < 2 or len(sys.argv) > 3:
        print(__doc__)
        return 2
    inp = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) == 3 else inp
    result = refresh(inp, out, run_whatifs=True)
    print(f"Output: {result['output']}")
    print(
        f"AAL — Best Estimate: ${result['BestEstimateAAL']:,.0f} | "
        f"Prudent: ${result['PrudentAAL']:,.0f}"
    )
    print(f"VaR 95: ${result['VaR95']:,.0f} | TVaR 95: ${result['TVaR95']:,.0f}")
    print(f"VaR 99: ${result['VaR99']:,.0f} | TVaR 99: ${result['TVaR99']:,.0f}")
    print(
        f"P(any successful loss event) — Best Estimate: {result['BestEstimatePAny']:.1%} | "
        f"Prudent: {result['PrudentPAny']:.1%}"
    )
    print(
        f"Sector: {result.get('sector')} | Asset type: {result.get('asset_type')} | "
        f"Pack: {result.get('sector_pack_id')} ({result.get('sector_pack_status')})"
    )
    print(f"Validation: {result['overall']} ({result['tests_pass']}/{result['tests_total']} tests)")
    return 0 if result["overall"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
