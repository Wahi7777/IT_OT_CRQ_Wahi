"""Extract OT sector packs in the Financial Services pack format and load them fail-closed."""

from __future__ import annotations

from pathlib import Path

import openpyxl
from openpyxl.styles import Alignment

from crq.pack_registry import OT_PACK_SCHEMA, project_root_from
from crq.sheet_names import OLD_TO_NEW
from crq.sheet_theme import ROLE_PACK, apply_column_headers, apply_freeze_at_headers, apply_title_banner, font_body, font_section, style_input_cell

ACTORS = ["Nation State", "Cybercriminal", "Malicious Insider"]
ACTOR_IDS = [("A_NS", "Nation State"), ("A_CC", "Cybercriminal"), ("A_MI", "Malicious Insider")]
OT_SCENARIOS = [
    "Operational Disruption",
    "Loss of Control or Visibility",
    "Process Manipulation",
    "Safety System Compromise",
    "Destructive or Integrity Attack",
]
OT_SCENARIO_IDS = [
    ("SC_1", "Operational Disruption"),
    ("SC_2", "Loss of Control or Visibility"),
    ("SC_3", "Process Manipulation"),
    ("SC_4", "Safety System Compromise"),
    ("SC_5", "Destructive or Integrity Attack"),
]
# Authoritative scenario-loss parameters on pack sheet 09 (row-oriented).
OT_SCENARIO_PARAM_SPECS = (
    {
        "id": "DOWNTIME_DAYS",
        "unit": "days",
        "description": (
            "Days of lost or reduced facility operation for this scenario. "
            "Drives business interruption and daily operating-cost drivers; "
            "not the same as restoration/rebuild effort days on driver rates."
        ),
    },
    {
        "id": "CAPACITY_AFFECTED",
        "unit": "share (0-1)",
        "description": (
            "Share of facility capacity or output affected while downtime runs (0 to 1). "
            "Scales business-interruption loss together with downtime days."
        ),
    },
)
OT_SCENARIO_PARAM_IDS = {spec["id"] for spec in OT_SCENARIO_PARAM_SPECS}



IT_PACK_SHEETS = [
    "00 Pack Guide",
    "01 Pack Metadata",
    "02 Actor Weights",
    "03 Actor Scenario",
    "04 Route Definitions",
    "05 Actor Route",
    "06 Scenario Route",
    "07 Stage Requirements",
    "08 Stage Priors",
    "09 Scenario Parameters",
    "10 Driver Rates",
    "11 Impact Driver Matrix",
    "12 TTP Catalogue",
    "13 Route TTP Map",
    "14 Control Reference",
    "15 Control TTP Map",
    "16 Sources",
    "17 Evidence Register",
    "18 Validation",
]

REQUIRED_OT_PACK_SHEETS = IT_PACK_SHEETS

SOURCE_SHEETS = {
    "Power Generation": ("30 Power Generation Pack", "OT PACK PG - Loaded Values"),
    "Energy Assets": ("31 Energy Assets Pack", "OT PACK EA - Loaded Values"),
    "Manufacturing": ("32 Manufacturing Pack", "OT PACK MF - Loaded Values"),
}


def _sheet(wb, *names: str):
    for name in names:
        if name in wb.sheetnames:
            return wb[name]
        mapped = OLD_TO_NEW.get(name)
        if mapped and mapped in wb.sheetnames:
            return wb[mapped]
    raise KeyError(names)


def _title(ws, heading: str, purpose: str) -> None:
    ws["A1"] = heading
    apply_title_banner(ws["A1"], ROLE_PACK)
    ws["A2"] = purpose
    ws["A2"].alignment = Alignment(wrap_text=True, vertical="center")
    ws["A2"].font = font_body()
    ws["A4"] = "SHEET TYPE: SECTOR PACK CALIBRATION - PACK OWNER ONLY"
    apply_title_banner(ws["A4"], ROLE_PACK)
    ws["A4"].font = font_section()
    ws.row_dimensions[1].height = 27
    ws.row_dimensions[2].height = 34
    ws.column_dimensions["A"].width = max(ws.column_dimensions["A"].width or 12, 28)


def _headers(ws, row: int, titles: list[str]) -> None:
    for c, title in enumerate(titles, 1):
        ws.cell(row, c, title)
    apply_column_headers(ws, row, len(titles), ROLE_PACK)
    apply_freeze_at_headers(ws, row)


def _input(cell, value) -> None:
    cell.value = value
    style_input_cell(cell)


def _clear_from(ws, start_row: int, cols: int = 16) -> None:
    for r in range(start_row, (ws.max_row or start_row) + 1):
        for c in range(1, cols + 1):
            target = ws.cell(r, c)
            if target.__class__.__name__ == "MergedCell":
                continue
            target.value = None


def extract_ot_packs(combined_path: Path, project_root: Path | None = None) -> list[Path]:
    """Write three OT packs using the Financial Services pack workbook format."""
    root = project_root or project_root_from(combined_path)
    dest_dir = root / "sector_packs" / "OT"
    dest_dir.mkdir(parents=True, exist_ok=True)
    it_template = root / "sector_packs" / "IT" / "IT_CRQ_Sector_Pack_Financial_Services_v1_1_1.xlsx"
    if not it_template.is_file():
        raise FileNotFoundError(f"IT pack template not found: {it_template}")

    src = openpyxl.load_workbook(combined_path, data_only=False)
    written = []
    try:
        registry = _sheet(src, "28 Sector Pack Registry", "OT PACK - Loaded Registry")
        rationale = _sheet(src, "29 Sector TTP Rationale", "OT PACK - Loaded TTP Rationale")
        freq = _sheet(src, "06 Frequency Assumptions", "OT 06 - Assessment Adjustments")
        bia = _sheet(src, "05 Impact and BIA", "OT 05 - Impact & BIA")
        records = {
            "Power Generation": ("PG-v1.6", "1.6", "Reference pack / working calibration", "OT_CRQ_Sector_Pack_Power_Generation_v1_6.xlsx"),
            "Energy Assets": ("EA-v1.0", "1.0", "Working pack — controlled calibration", "OT_CRQ_Sector_Pack_Energy_Assets_v1_0.xlsx"),
            "Manufacturing": ("MF-v1.0", "1.0", "Working pack — controlled calibration", "OT_CRQ_Sector_Pack_Manufacturing_v1_0.xlsx"),
        }
        for sector, (pack_id, version, status, filename) in records.items():
            wb = openpyxl.load_workbook(it_template)
            _fill_guide(wb["00 Pack Guide"], sector, pack_id, version)
            _fill_metadata(wb["01 Pack Metadata"], sector, pack_id, version, status, registry)
            _fill_actors(wb["02 Actor Weights"], freq, sector, pack_id, registry)
            _fill_actor_scenario(wb["03 Actor Scenario"], freq)
            _fill_placeholder_core(
                wb["04 Route Definitions"],
                "04 — Route Definitions",
                "OT does not use IT composite routes. Attack stages S1–S5 and TTP gates are core OT methodology; sector TTP emphasis is on 12 TTP Catalogue.",
            )
            _fill_assets_on_actor_route(wb["05 Actor Route"], registry, sector, pack_id)
            _fill_placeholder_core(
                wb["06 Scenario Route"],
                "06 — Scenario-to-Route Propensity",
                "Not used by the OT engine. OT scenario propensity remains core methodology on OT CORE / OT 06.",
            )
            _fill_placeholder_core(
                wb["07 Stage Requirements"],
                "07 — Scenario-Aware Stage Requirements",
                "Five-stage path requirements are core OT methodology. This pack does not override them.",
            )
            _fill_placeholder_core(
                wb["08 Stage Priors"],
                "08 — Reference Stage-Through Priors",
                "Stage-through calculation is core OT methodology. Sector intensity is on 02 Actor Weights.",
            )
            _fill_scenarios(wb["09 Scenario Parameters"], bia)
            _fill_driver_rates(wb["10 Driver Rates"], bia)
            _fill_impact_matrix(wb["11 Impact Driver Matrix"], bia)
            _fill_ttp(wb["12 TTP Catalogue"], rationale, sector)
            _fill_placeholder_core(
                wb["13 Route TTP Map"],
                "13 — Route-to-TTP Mapping",
                "OT maps techniques through the core Scenario-TTP and TTP-Control sheets. Sector applicability is sheet 12.",
            )
            _fill_placeholder_core(
                wb["14 Control Reference"],
                "14 — Reference Control Profile",
                "OT control maturity scale and reference-relative adjustment are core OT methodology.",
            )
            _fill_placeholder_core(
                wb["15 Control TTP Map"],
                "15 — Control-to-TTP Efficacy Map",
                "TTP-control efficacy is core OT (OT CORE - TTP-Control Map). This pack does not duplicate it.",
            )
            _fill_sources(wb["16 Sources"], registry, sector)
            _fill_validation(wb["18 Validation"], pack_id)
            from crq.pack_sheet_guide import apply_pack_sheet_blurb

            for name in wb.sheetnames:
                apply_pack_sheet_blurb(wb[name], "OT")
            missing = [s for s in REQUIRED_OT_PACK_SHEETS if s not in wb.sheetnames]
            if missing:
                raise ValueError(f"{pack_id} missing sheets {missing}")
            out = dest_dir / filename
            wb.save(out)
            wb.close()
            written.append(out)
    finally:
        src.close()
    return written


def _fill_guide(ws, sector, pack_id, version) -> None:
    _clear_from(ws, 3, 12)
    _title(ws, f"OT Sector Pack - {sector} - {pack_id}", "Separate, schema-governed calibration pack for the common facility-level OT-CRQ engine.")
    ws["A3"] = (
        f"This workbook contains {sector} reference calibration. "
        "Do not enter client-specific or assessment-specific data in this workbook."
    )
    ws["A6"] = "Purpose"
    ws["A7"] = (
        f"Supply {sector} actor-intensity, asset-archetype, TTP applicability, frequency overlay "
        "and BIA reference assumptions for pack ID " + pack_id + f" / v{version}."
    )
    ws["A9"] = "Calculation / decision logic"
    ws["A10"] = "Python validates pack identity, schema, TTP coverage and multipliers, then applies assessment overrides separately."
    ws["A12"] = "Outputs / downstream use"
    ws["A13"] = "Loaded by Guided_IT_OT_CRQ_Model_v1_0.xlsx. The combined workbook must not retain a second authoritative copy of these values."
    ws["A15"] = "Workbook convention"
    ws["A16"] = "Yellow cells with blue font are pack-owner editable. Do not enter assessment data here."
    ws["A20"] = "PACK DESIGN PRINCIPLES"
    ws["A21"] = "1"
    ws["B21"] = "One common OT-CRQ engine; packs contain sector data and rationale only."
    ws["A22"] = "2"
    ws["B22"] = "Same pack workbook format as the Financial Services IT pack (guide, metadata, row-15 tables, evidence columns)."
    ws["A23"] = "3"
    ws["B23"] = "Core path, control and Monte Carlo mechanics stay in the OT engine."


def _fill_metadata(ws, sector, pack_id, version, status, registry) -> None:
    _title(ws, "01 — Pack Metadata", "The engine resolves and validates this metadata before loading any pack assumptions.")
    _headers(ws, 15, ["Key", "Value", "Description", "Evidence grade", "Source ID"])
    evidence = _registry_cell(registry, sector, 8)
    rows = [
        ("PACK_ID", pack_id, "Unique pack identifier", "D", "SRC-OT-01"),
        ("SECTOR", sector, "Exact combined-workbook sector selection", "D", "SRC-OT-01"),
        ("DOMAIN", "OT", "Model domain", "D", "SRC-OT-01"),
        ("PACK_VERSION", version, "Pack content version", "D", "SRC-OT-01"),
        ("SCHEMA_VERSION", OT_PACK_SCHEMA, "Required table schema", "D", "SRC-OT-01"),
        ("MIN_ENGINE_VERSION", "1.7.1", "Minimum compatible Python engine", "D", "SRC-OT-01"),
        ("STATUS", status, "Must not be described as fully externally validated unless that evidence exists", "D", "SRC-OT-01"),
        ("UNIT_OF_ANALYSIS", "Facility", "OT unit of analysis", "D", "SRC-OT-01"),
        ("PACK_OWNER", "Sector Pack Owner", "Editable during assessment: No", "D", "SRC-OT-01"),
        ("PRIMARY_EVIDENCE", evidence, "Primary evidence cited in the former embedded registry", "C", "SRC-OT-01"),
    ]
    _clear_from(ws, 16)
    for i, row in enumerate(rows):
        ws.cell(16 + i, 1, row[0])
        _input(ws.cell(16 + i, 2), row[1])
        ws.cell(16 + i, 3, row[2])
        _input(ws.cell(16 + i, 4), row[3])
        _input(ws.cell(16 + i, 5), row[4])


def _fill_actors(ws, freq, sector, pack_id, registry) -> None:
    _title(ws, "02 — Threat-Actor Weights", "Sector actor-intensity multipliers for this OT pack. These are multipliers, not a campaign-share mix that must sum to 1.")
    _headers(ws, 15, ["Actor ID", "Threat actor", "Weight", "Basis / limitation", "Evidence grade", "Source ID"])
    _clear_from(ws, 16)
    freq_row = None
    for r in range(73, 76):
        if str(freq.cell(r, 1).value or "").strip() == sector:
            freq_row = r
            break
    if freq_row is None:
        raise ValueError(f"Missing frequency sector row for {sector}")
    basis = freq.cell(freq_row, 5).value
    for i, (aid, name) in enumerate(ACTOR_IDS):
        ws.cell(16 + i, 1, aid)
        ws.cell(16 + i, 2, name)
        _input(ws.cell(16 + i, 3), freq.cell(freq_row, 2 + i).value)
        ws.cell(16 + i, 4, basis)
        _input(ws.cell(16 + i, 5), "D")
        _input(ws.cell(16 + i, 6), "SRC-OT-01")
    ws.cell(19, 1, "CHECK")
    ws.cell(19, 2, "Pack ID")
    ws.cell(19, 3, pack_id)

    ws["A23"] = "ASSET-TYPE FREQUENCY OVERLAYS"
    ws["A23"].font = font_section(color="000000")
    _headers(ws, 24, ["Asset type", "Nation State", "Cybercriminal", "Malicious Insider", "Parameter type", "Status", "Rationale / how used", "Evidence grade", "Source ID"])
    out_r = 25
    for r in range(45, 60):
        if str(registry.cell(r, 1).value or "").strip() != sector:
            continue
        _input(ws.cell(out_r, 1), registry.cell(r, 2).value)
        for c in range(2, 5):
            _input(ws.cell(out_r, c), registry.cell(r, c + 1).value)
        ws.cell(out_r, 5, registry.cell(r, 6).value)
        ws.cell(out_r, 6, registry.cell(r, 7).value)
        ws.cell(out_r, 7, registry.cell(r, 8).value)
        _input(ws.cell(out_r, 8), "D")
        _input(ws.cell(out_r, 9), "SRC-OT-01")
        out_r += 1


def _fill_actor_scenario(ws, freq) -> None:
    _title(ws, "03 — Actor-to-Scenario Propensity", "Sector actor-to-scenario mix. The OT engine loads this table from the pack as the authoritative propensity input.")
    _headers(ws, 15, ["Actor ID", *OT_SCENARIOS, "Row total"])
    _clear_from(ws, 16)
    for i, (aid, name) in enumerate(ACTOR_IDS):
        src_r = 35 + i
        ws.cell(16 + i, 1, aid)
        for c in range(5):
            _input(ws.cell(16 + i, 2 + c), freq.cell(src_r, 2 + c).value)
        ws.cell(16 + i, 7, f"=SUM(B{16+i}:F{16+i})")


def _fill_placeholder_core(ws, heading: str, purpose: str) -> None:
    _title(ws, heading, purpose)
    _headers(ws, 15, ["Item", "Value", "Description", "Evidence grade", "Source ID"])
    _clear_from(ws, 16)
    ws.cell(16, 1, "OT_CORE")
    _input(ws.cell(16, 2), "Held in core OT methodology")
    ws.cell(16, 3, purpose)
    _input(ws.cell(16, 4), "D")
    _input(ws.cell(16, 5), "SRC-OT-01")


def _fill_assets_on_actor_route(ws, registry, sector, pack_id) -> None:
    _title(ws, "05 — Asset Archetypes", "Registered plant / asset types for this sector pack. Same table layout as other pack sheets (headers on row 15).")
    _headers(ws, 15, ["Sector", "Plant / asset type", "Pack ID", "Operating profile", "Safety / protection context", "BIA treatment", "Calibration status", "Evidence grade", "Source ID"])
    _clear_from(ws, 16)
    out_r = 16
    for r in range(25, 40):
        if str(registry.cell(r, 1).value or "").strip() != sector:
            continue
        for c in range(1, 8):
            val = registry.cell(r, c).value
            if c in (1, 2, 3):
                _input(ws.cell(out_r, c), val)
            else:
                ws.cell(out_r, c, val)
        _input(ws.cell(out_r, 8), "D")
        _input(ws.cell(out_r, 9), "SRC-OT-01")
        if str(ws.cell(out_r, 3).value or "") != pack_id:
            raise ValueError(f"Asset pack ID mismatch for {sector}")
        out_r += 1


def _fill_scenarios(ws, bia) -> None:
    """Write row-oriented OT scenario downtime/capacity parameters (no IT enterprise columns)."""
    _title(
        ws,
        "09 — Scenario Impact Parameters",
        "Sector P50/P99 downtime and capacity assumptions. One parameter per row. "
        "The OT engine loads this sheet as the authoritative scenario-impact input.",
    )
    headers = [
        "Scenario ID",
        "Scenario",
        "Parameter ID",
        "P50",
        "P99",
        "Unit",
        "Applies?",
        "Evidence grade",
        "Source ID",
        "Description / rationale",
    ]
    _headers(ws, 15, headers)
    # Wipe legacy wide IT-style columns (and any prior rows) so removed parameters do not linger.
    max_col = max(40, ws.max_column or 40)
    max_row = max(40, ws.max_row or 40)
    for r in range(15, max_row + 1):
        for c in range(1, max_col + 1):
            ws.cell(r, c).value = None
    _headers(ws, 15, headers)
    by_name = {}
    for r in range(58, 63):
        name = str(bia.cell(r, 1).value or "").strip()
        if name in OT_SCENARIOS:
            by_name[name] = {
                "DOWNTIME_DAYS": (bia.cell(r, 2).value, bia.cell(r, 3).value),
                "CAPACITY_AFFECTED": (bia.cell(r, 4).value, bia.cell(r, 5).value),
                "note": bia.cell(r, 7).value,
            }
    out_r = 16
    for sid, name in OT_SCENARIO_IDS:
        if name not in by_name:
            raise ValueError(f"OT BIA is missing scenario calibration for {name!r}.")
        block = by_name[name]
        for spec in OT_SCENARIO_PARAM_SPECS:
            pid = spec["id"]
            p50, p99 = block[pid]
            ws.cell(out_r, 1, sid)
            ws.cell(out_r, 2, name)
            ws.cell(out_r, 3, pid)
            _input(ws.cell(out_r, 4), p50)
            _input(ws.cell(out_r, 5), p99)
            ws.cell(out_r, 6, spec["unit"])
            _input(ws.cell(out_r, 7), "Yes")
            _input(ws.cell(out_r, 8), "D")
            _input(ws.cell(out_r, 9), "SRC-OT-01")
            desc = spec["description"]
            note = str(block.get("note") or "").strip()
            if note:
                desc = f"{desc} Sector note: {note}"
            ws.cell(out_r, 10, desc)
            ws.cell(out_r, 10).alignment = Alignment(wrap_text=True, vertical="center")
            if pid == "DOWNTIME_DAYS":
                ws.cell(out_r, 4).number_format = "0.0"
                ws.cell(out_r, 5).number_format = "0.0"
            else:
                ws.cell(out_r, 4).number_format = "0%"
                ws.cell(out_r, 5).number_format = "0%"
            out_r += 1
    for col, width in enumerate((12, 28, 20, 10, 10, 14, 10, 14, 12, 56), 1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(col)].width = width
    ws.auto_filter.ref = f"A15:J{out_r - 1}"
    apply_freeze_at_headers(ws, 15)


def _fill_driver_rates(ws, bia) -> None:
    _title(ws, "10 — Impact Driver Rates", "Pack base/stress rates for the common 18-driver OT BIA. Facility quantities remain assessment inputs.")
    _headers(ws, 15, ["Rate ID", "Driver", "P50", "P99", "Unit", "Source / status", "Evidence grade", "Source ID"])
    _clear_from(ws, 16)
    out_r = 16
    for r in range(67, 90):
        did = str(bia.cell(r, 1).value or "").strip()
        if not did:
            continue
        ws.cell(out_r, 1, did)
        ws.cell(out_r, 2, bia.cell(r, 2).value)
        _input(ws.cell(out_r, 3), bia.cell(r, 3).value)
        _input(ws.cell(out_r, 4), bia.cell(r, 4).value)
        ws.cell(out_r, 5, bia.cell(r, 7).value)
        ws.cell(out_r, 6, bia.cell(r, 12).value)
        _input(ws.cell(out_r, 7), "D")
        _input(ws.cell(out_r, 8), "SRC-OT-01")
        out_r += 1


def _fill_impact_matrix(ws, bia) -> None:
    _title(ws, "11 — Actor and Scenario Impact Applicability", "Pack driver-to-scenario applicability (1 = applies). Copied from the governed OT BIA matrix.")
    _headers(ws, 15, ["Driver ID", "Driver", "Loss block", *OT_SCENARIOS, "Evidence grade", "Source ID"])
    _clear_from(ws, 16, 14)
    out_r = 16
    for r in range(28, 54):
        did = str(bia.cell(r, 2).value or "").strip()
        if not did:
            continue
        ws.cell(out_r, 1, did)
        ws.cell(out_r, 2, bia.cell(r, 3).value)
        ws.cell(out_r, 3, bia.cell(r, 1).value)
        for i in range(5):
            raw = bia.cell(r, 6 + i).value
            _input(ws.cell(out_r, 4 + i), 1 if str(raw).strip().upper() in {"TRUE", "YES", "1"} or raw is True else 0)
        _input(ws.cell(out_r, 9), "D")
        _input(ws.cell(out_r, 10), "SRC-OT-01")
        out_r += 1


def _fill_ttp(ws, rationale, sector) -> None:
    _title(ws, "12 — ATT&CK for ICS Catalogue", "Governed techniques for this sector, with default applicability and facility gates.")
    _headers(ws, 15, [
        "TTP ID", "Technique", "Stage", "Platforms", "MITRE URL",
        "Default applicable?", "Facility gate", "Rationale", "Sector guidance URL",
        "Calibration status", "Evidence grade", "Source ID",
    ])
    _clear_from(ws, 16, 14)
    out_r = 16
    start = 16
    header0 = str(rationale.cell(15, 1).value or "")
    if "Lookup" in header0 or "key" in header0.lower():
        start = 16
    for r in range(start, (rationale.max_row or start) + 1):
        row_sector = str(rationale.cell(r, 2).value or "").strip()
        tid = str(rationale.cell(r, 4).value or "").strip()
        if row_sector != sector or not tid:
            continue
        ws.cell(out_r, 1, tid)
        ws.cell(out_r, 2, rationale.cell(r, 5).value)
        ws.cell(out_r, 3, rationale.cell(r, 6).value)
        ws.cell(out_r, 4, rationale.cell(r, 3).value)
        ws.cell(out_r, 5, rationale.cell(r, 10).value)
        _input(ws.cell(out_r, 6), rationale.cell(r, 7).value)
        ws.cell(out_r, 7, rationale.cell(r, 8).value)
        ws.cell(out_r, 8, rationale.cell(r, 9).value)
        ws.cell(out_r, 9, rationale.cell(r, 11).value)
        ws.cell(out_r, 10, rationale.cell(r, 12).value)
        _input(ws.cell(out_r, 11), "D")
        _input(ws.cell(out_r, 12), "SRC-OT-01")
        out_r += 1
    if out_r == 16:
        raise ValueError(f"No TTP rationale rows for {sector}")


def _fill_sources(ws, registry, sector) -> None:
    _title(ws, "16 — Sources and Evidence", "Sources support taxonomy and context; quantitative pack values remain working priors unless separately calibrated.")
    _headers(ws, 15, ["Source ID", "Source", "URL / file", "How used", "Limitation"])
    _clear_from(ws, 16)
    evidence = _registry_cell(registry, sector, 8)
    rows = [
        ("SRC-OT-01", "Embedded OT sector pack (extracted)", "OT CORE / former sheets 28–32", "Identity, archetypes, TTP rationale and frequency overlays", "Working prior unless a later pack revision cites new evidence."),
        ("SRC-OT-02", "MITRE ATT&CK for ICS", "https://attack.mitre.org/matrices/ics/", "Technique taxonomy", "ATT&CK is not a frequency dataset."),
        ("SRC-OT-03", "Primary registry evidence", str(evidence), "Sector evidence cited in the governed registry", "See pack STATUS."),
    ]
    for i, row in enumerate(rows):
        ws.cell(16 + i, 1, row[0])
        ws.cell(16 + i, 2, row[1])
        ws.cell(16 + i, 3, row[2])
        ws.cell(16 + i, 4, row[3])
        ws.cell(16 + i, 5, row[4])


def _fill_validation(ws, pack_id) -> None:
    _title(ws, "18 — Pack Validation", "Visible structural checks; the Python engine independently repeats targeted checks and fails closed.")
    _headers(ws, 15, ["Check", "Actual", "Expected", "Tolerance", "Status"])
    _clear_from(ws, 16)
    ws.cell(16, 1, "PACK_ID populated")
    ws.cell(16, 2, f"='01 Pack Metadata'!B16")
    ws.cell(16, 3, pack_id)
    ws.cell(16, 4, 0)
    ws.cell(16, 5, '=IF(B16=C16,"PASS","FAIL")')
    ws.cell(17, 1, "DOMAIN is OT")
    ws.cell(17, 2, "='01 Pack Metadata'!B18")
    ws.cell(17, 3, "OT")
    ws.cell(17, 5, '=IF(B17=C17,"PASS","FAIL")')
    ws.cell(18, 1, "TTP catalogue has rows")
    ws.cell(18, 2, '=COUNTA(\'12 TTP Catalogue\'!A16:A500)')
    ws.cell(18, 3, ">0")
    ws.cell(18, 5, '=IF(B18>0,"PASS","FAIL")')
    ws.cell(19, 1, "Asset archetypes have rows")
    ws.cell(19, 2, '=COUNTA(\'05 Actor Route\'!A16:A40)')
    ws.cell(19, 3, ">0")
    ws.cell(19, 5, '=IF(B19>0,"PASS","FAIL")')


def _registry_cell(registry, sector: str, col: int):
    for r in range(16, 19):
        if str(registry.cell(r, 1).value or "").strip() == sector:
            return registry.cell(r, col).value
    raise ValueError(f"No registry identity row for {sector}")


def _required_text(value, label):
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{label} must be populated.")
    return text


def _required_multiplier(value, label):
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


def _load_scenario_parameters(ws) -> dict:
    """Fail-closed row-oriented scenario downtime/capacity from pack sheet 09."""
    id_to_name = {sid: name for sid, name in OT_SCENARIO_IDS}
    props = {name: {} for _, name in OT_SCENARIO_IDS}
    seen_keys = set()
    for r in range(16, (ws.max_row or 16) + 1):
        sid = str(ws.cell(r, 1).value or "").strip()
        if not sid:
            continue
        name = str(ws.cell(r, 2).value or "").strip()
        expected = id_to_name.get(sid)
        if expected is None:
            raise ValueError(f"09 Scenario Parameters row {r} has unknown Scenario ID {sid!r}.")
        if name != expected:
            raise ValueError(
                f"09 Scenario Parameters row {r}: Scenario {name!r} does not match ID {sid} ({expected})."
            )
        pid = str(ws.cell(r, 3).value or "").strip()
        if pid not in OT_SCENARIO_PARAM_IDS:
            raise ValueError(
                f"09 Scenario Parameters row {r}: unsupported Parameter ID {pid!r}. "
                f"OT packs may only use {sorted(OT_SCENARIO_PARAM_IDS)}."
            )
        key = (sid, pid)
        if key in seen_keys:
            raise ValueError(f"Duplicate scenario/parameter key on 09 Scenario Parameters: {sid}/{pid}.")
        seen_keys.add(key)
        applies = str(ws.cell(r, 7).value or "").strip().lower()
        if applies not in {"yes", "y", "true", "1"}:
            raise ValueError(
                f"{name} / {pid} must have Applies?=Yes; inactive scenario parameters are not permitted "
                "for the governed OT downtime/capacity set."
            )
        grade = str(ws.cell(r, 8).value or "").strip()
        source = str(ws.cell(r, 9).value or "").strip()
        if not grade or not source:
            raise ValueError(f"{name} / {pid} requires Evidence grade and Source ID.")
        p50 = ws.cell(r, 4).value
        p99 = ws.cell(r, 5).value
        if p50 in (None, "") or p99 in (None, ""):
            raise ValueError(f"{name} / {pid} P50 and P99 must be populated.")
        try:
            p50_f = float(p50)
            p99_f = float(p99)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{name} / {pid} P50/P99 must be numeric.") from exc
        if p50_f < 0 or p99_f < p50_f:
            raise ValueError(f"{name} / {pid} must be non-negative with P99 >= P50.")
        if pid == "CAPACITY_AFFECTED" and not (0.0 <= p50_f <= p99_f <= 1.0):
            raise ValueError(f"{name} / {pid} must satisfy 0 <= P50 <= P99 <= 1.")
        props[name][pid] = {"p50": p50_f, "p99": p99_f, "grade": grade, "source": source}

    expected_keys = {(sid, spec["id"]) for sid, _ in OT_SCENARIO_IDS for spec in OT_SCENARIO_PARAM_SPECS}
    missing = sorted(expected_keys - seen_keys)
    if missing:
        preview = ", ".join(f"{a}/{b}" for a, b in missing[:8])
        raise ValueError(f"09 Scenario Parameters is missing required rows: {preview}")

    scenario_impact = {}
    for _, name in OT_SCENARIO_IDS:
        downtime = props[name]["DOWNTIME_DAYS"]
        capacity = props[name]["CAPACITY_AFFECTED"]
        scenario_impact[name] = {
            "base_days": downtime["p50"],
            "stress_days": downtime["p99"],
            "base_capacity": capacity["p50"],
            "stress_capacity": capacity["p99"],
        }
    return scenario_impact


def rewrite_ot_pack_scenario_parameters(path: Path, combined_path: Path | None = None) -> None:
    """Rebuild sheet 09 on an existing OT pack from the governed combined BIA (or keep pack values)."""
    root = project_root_from()
    combined = Path(combined_path) if combined_path else root / "model" / "Guided_IT_OT_CRQ_Model_v1_0.xlsx"
    src = openpyxl.load_workbook(combined, data_only=False)
    try:
        bia = None
        for name in ("OT 05 - Impact & BIA", "05 Impact and BIA"):
            if name in src.sheetnames:
                bia = src[name]
                break
        if bia is None:
            raise ValueError("Combined workbook has no OT Impact & BIA sheet to seed pack 09.")
        wb = openpyxl.load_workbook(path)
        try:
            if "09 Scenario Parameters" not in wb.sheetnames:
                raise ValueError(f"{path.name} is missing 09 Scenario Parameters")
            _fill_scenarios(wb["09 Scenario Parameters"], bia)
            from crq.pack_sheet_guide import apply_pack_sheet_blurb

            apply_pack_sheet_blurb(wb["09 Scenario Parameters"], "OT")
            wb.save(path)
        finally:
            wb.close()
    finally:
        src.close()


def _load_actor_scenario(ws) -> dict:
    """Fail-closed actor-to-scenario propensity from pack sheet 03."""
    id_to_name = {aid: name for aid, name in ACTOR_IDS}
    props = {}
    for r in range(16, 19):
        aid = str(ws.cell(r, 1).value or "").strip()
        name = id_to_name.get(aid)
        if name is None:
            raise ValueError(f"03 Actor Scenario row {r} has unknown Actor ID {aid!r}.")
        row = {}
        for i, scenario in enumerate(OT_SCENARIOS):
            label = f"{name} / {scenario} pack propensity"
            raw = ws.cell(r, 2 + i).value
            if raw in (None, ""):
                raise ValueError(f"{label} must be populated in the sector pack.")
            try:
                row[scenario] = float(raw)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"{label} must be numeric.") from exc
            if row[scenario] < 0:
                raise ValueError(f"{label} cannot be negative.")
        total = sum(row.values())
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"{name} pack scenario propensities must sum to 1.0; got {total}.")
        props[name] = row
    if set(props) != set(ACTORS):
        raise ValueError(f"03 Actor Scenario must include all OT actors; found {sorted(props)}")
    return props


def _table_rows(ws, header_row: int, cols: int):
    rows = []
    for r in range(header_row + 1, (ws.max_row or header_row) + 1):
        vals = [ws.cell(r, c).value for c in range(1, cols + 1)]
        if any(v not in (None, "") for v in vals):
            rows.append(vals)
    return rows


def load_ot_pack(path: Path, sector: str, asset_type: str, governed_ttp_ids, pack_id: str) -> dict:
    """Fail-closed load of one external OT pack in the FS pack format."""
    wb = openpyxl.load_workbook(path, data_only=False)
    try:
        missing = [s for s in ("01 Pack Metadata", "02 Actor Weights", "03 Actor Scenario", "05 Actor Route", "09 Scenario Parameters", "12 TTP Catalogue") if s not in wb.sheetnames]
        if missing:
            raise ValueError(f"Required pack sheet missing: {missing}")

        assets = _table_rows(wb["05 Actor Route"], 15, 7)
        asset_row = _single_row(
            assets,
            lambda r: str(r[0]).strip() == sector and str(r[1]).strip() == asset_type,
            f"Registered sector/asset selection {sector!r} / {asset_type!r}",
        )
        if str(asset_row[2]).strip() != pack_id:
            raise ValueError(f"Asset row pack ID {asset_row[2]!r} does not match {pack_id!r}.")

        actor_ws = wb["02 Actor Weights"]
        sector_mults = {}
        for r in range(16, 19):
            name = str(actor_ws.cell(r, 2).value or "").strip()
            if name in ACTORS:
                sector_mults[name] = _required_multiplier(actor_ws.cell(r, 3).value, f"{sector}/{name} sector multiplier")
        if set(sector_mults) != set(ACTORS):
            raise ValueError(f"02 Actor Weights must include all OT actors; found {sorted(sector_mults)}")

        overlay_rows = _table_rows(actor_ws, 24, 4)
        overlay_row = _single_row(
            overlay_rows,
            lambda r: str(r[0]).strip() == asset_type,
            f"Asset-type frequency overlay for {sector!r} / {asset_type!r}",
        )
        asset_multipliers = {}
        for i, actor in enumerate(ACTORS):
            asset_multipliers[actor] = _required_multiplier(
                overlay_row[i + 1], f"{sector} / {asset_type} / {actor} asset multiplier"
            )

        rationale_ws = wb["12 TTP Catalogue"]
        rationale = {}
        for r in range(16, (rationale_ws.max_row or 16) + 1):
            tid = str(rationale_ws.cell(r, 1).value or "").strip()
            if not tid or tid == "TTP ID":
                continue
            if tid in rationale:
                raise ValueError(f"Duplicate sector rationale row for {sector!r} / {tid!r}.")
            raw_applicable = str(rationale_ws.cell(r, 6).value or "").strip()
            if raw_applicable.lower() not in {"yes", "no"}:
                raise ValueError(
                    f"Sector rationale applicability for {sector!r} / {tid!r} must be Yes or No."
                )
            rationale[tid] = {
                "asset_scope": rationale_ws.cell(r, 4).value,
                "applicable": raw_applicable.lower() == "yes",
                "facility_gate": rationale_ws.cell(r, 7).value,
                "rationale": _required_text(rationale_ws.cell(r, 8).value, f"Sector/asset rationale for {sector!r} / {tid!r}"),
                "guidance_url": _required_text(rationale_ws.cell(r, 9).value or rationale_ws.cell(r, 5).value, f"Sector guidance URL for {sector!r} / {tid!r}"),
                "calibration_status": rationale_ws.cell(r, 10).value,
            }
        governed = {str(x).strip() for x in governed_ttp_ids if str(x).strip()}
        missing_t = sorted(governed - set(rationale))
        if missing_t:
            preview = ", ".join(missing_t[:10])
            raise ValueError(
                f"Sector {sector!r} pack lacks rationale rows for {len(missing_t)} governed TTP(s): {preview}"
            )
        meta_map = {}
        for r in range(16, 40):
            k = str(wb["01 Pack Metadata"].cell(r, 1).value or "").strip()
            if k:
                meta_map[k] = wb["01 Pack Metadata"].cell(r, 2).value
        if str(meta_map.get("PACK_ID") or "").strip() != pack_id:
            raise ValueError("Pack metadata PACK_ID does not match registry.")
        scenario_propensity = _load_actor_scenario(wb["03 Actor Scenario"])
        scenario_impact = _load_scenario_parameters(wb["09 Scenario Parameters"])
        return {
            "sector": sector,
            "asset_type": asset_type,
            "pack_id": pack_id,
            "pack_status": str(meta_map.get("STATUS") or "").strip(),
            "asset_calibration_status": asset_row[6],
            "asset_multipliers": asset_multipliers,
            "sector_multipliers": sector_mults,
            "scenario_propensity": scenario_propensity,
            "scenario_impact": scenario_impact,
            "rationale": rationale,
            "governed_ttp_count": len(governed),
            "pack_path": str(path),
        }
    finally:
        wb.close()
