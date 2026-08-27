"""Canonical combined-workbook sheet names and old-to-new mapping."""

from __future__ import annotations

# Longest old names first when rewriting formulas.
OLD_TO_NEW = {
    "IT 03 Organisation Inputs": "IT 03 - Organisation Inputs",
    "IT 04 Exposure Adjustments": "IT 04 - Exposure Adjustments",
    "IT 05 Control Assessment": "IT 05 - Control Assessment",
    "IT 06 Impact and BIA": "IT 06 - Impact & BIA Overrides",
    "IT 07 Frequency Assumptions": "IT 07 - Assessment Adjustments",
    "IT 08 Tail Risk Settings": "IT 08 - Reporting Settings",
    "IT 09 Sector Pack Registry": "IT 09 - Sector Pack Registry",
    "IT 01 Model Guide": "IT CORE - Model Guide",
    "IT 02 Executive Summary": "IT 02 - Executive Summary",
    "IT 10 TTP Relevance Calc": "IT CALC - TTP Relevance",
    "IT 11 Attack Path Calc": "IT CALC - Attack Path",
    "IT 12 Frequency and Success": "IT CALC - Frequency and Success",
    "IT 13 Consequence Calc": "IT CALC - Consequence",
    "IT 14 Actor Scenario Matrix": "IT CALC - Actor Scenario Matrix",
    "IT 15 Tail Risk Metrics": "IT CALC - Tail Risk Metrics",
    "IT 16 Control What-If": "IT CALC - Control What-If",
    "IT 17 Aggregate LECs": "IT CALC - Aggregate LECs",
    "IT 18 Scenario LECs": "IT CALC - Scenario LECs",
    "IT 19 Actor LECs": "IT CALC - Actor LECs",
    "IT 20 Risk Charts": "IT CALC - Risk Charts",
    "IT 21 Sources and Evidence": "IT 21 - Sources and Evidence",
    "IT 22 Validation Tests": "IT 22 - Validation Tests",
    "00 Run Setup": "00 COMMON - Run Setup",
    "00 Outside-In": "00 COMMON - Outside-In",
    "00 Output Bridge": "00 COMMON - Output Bridge",
    "00 OI Adjustment Rationale": "00 COMMON - OI Audit Trail",
    "00 Engine Results": "00 COMMON - Engine Results",
    "03 Facility Inputs": "OT 03 - Facility Inputs",
    "04 Control Assessment": "OT 04 - Control Assessment",
    "05 Impact and BIA": "OT 05 - Impact & BIA",
    "06 Frequency Assumptions": "OT 06 - Assessment Adjustments",
    "07 Control Assumptions": "OT CORE - Control Method",
    "08 Scenario Definitions": "OT CORE - Scenario Definitions",
    "09 Scenario-TTP Map": "OT CORE - Scenario-TTP Map",
    "10 Mapping Change Log": "OT CORE - Mapping Change Log",
    "11 Actor-TTP Applicability": "OT CORE - Actor-TTP Map",
    "12 Facility Feasibility": "OT CORE - Facility Feasibility",
    "13 TTP-Control Map": "OT CORE - TTP-Control Map",
    "14 TTP Relevance Calc": "OT CALC - TTP Relevance",
    "15 Attack Path Calc": "OT CALC - Attack Path",
    "16 Threat and Loss Frequency": "OT CALC - Threat Frequency",
    "17 Consequence Calc": "OT CALC - Consequence",
    "18 Actor-Scenario Matrix": "OT CALC - Actor-Scenario Matrix",
    "19 Tail Risk Metrics": "OT CALC - Tail Risk Metrics",
    "20 Control What-If": "OT CALC - Control What-If",
    "21 Aggregate LECs": "OT CALC - Aggregate LECs",
    "22 Scenario LECs": "OT CALC - Scenario LECs",
    "23 Actor LECs": "OT CALC - Actor LECs",
    "24 Actor-Scenario LEC Data": "OT CALC - Actor-Scenario LEC",
    "25 Risk Charts": "OT CALC - Risk Charts",
    "26 Sources and Evidence": "OT 26 - Sources and Evidence",
    "27 Validation Tests": "OT 27 - Validation Tests",
    "01 Model Guide": "OT CORE - Model Guide",
    "02 Executive Summary": "OT 02 - Executive Summary",
    "28 Sector Pack Registry": "OT PACK - Loaded Registry",
    "29 Sector TTP Rationale": "OT PACK - Loaded TTP Rationale",
    "30 Power Generation Pack": "OT PACK PG - Loaded Values",
    "31 Energy Assets Pack": "OT PACK EA - Loaded Values",
    "32 Manufacturing Pack": "OT PACK MF - Loaded Values",
    "33 Sector Pack Comparison": "OT PACK - Loaded Comparison",
    "1 Executive Dashboards": "1 Executive dashboards",
    "2 User Inputs": "2 User-input navigation",
    "3 Key Assumptions": "3 Assumption Ownership",
    "4 Modelled Results": "4 Results and audit trail",
    "5 Other": "5 Advanced - Governed",
}

NEW_TO_OLD = {v: k for k, v in OLD_TO_NEW.items()}

COMMON_RUN_SETUP = "00 COMMON - Run Setup"
COMMON_OUTSIDE_IN = "00 COMMON - Outside-In"
COMMON_BRIDGE = "00 COMMON - Output Bridge"
COMMON_OI_AUDIT = "00 COMMON - OI Audit Trail"
COMMON_ENGINE = "00 COMMON - Engine Results"

IT_ORG = "IT 03 - Organisation Inputs"
IT_EXPOSURE = "IT 04 - Exposure Adjustments"
IT_CONTROLS = "IT 05 - Control Assessment"
IT_BIA = "IT 06 - Impact & BIA Overrides"
IT_FREQ = "IT 07 - Assessment Adjustments"
IT_REPORT = "IT 08 - Reporting Settings"

OT_FACILITY = "OT 03 - Facility Inputs"
OT_CONTROLS = "OT 04 - Control Assessment"
OT_BIA = "OT 05 - Impact & BIA"
OT_FREQ = "OT 06 - Assessment Adjustments"

IT_FILL = (IT_ORG, IT_EXPOSURE, IT_CONTROLS, IT_BIA, IT_FREQ, IT_REPORT)
OT_FILL = (OT_FACILITY, OT_CONTROLS, OT_BIA, OT_FREQ)

DIV_DASHBOARDS = "1 Executive dashboards"
DIV_NAV = "2 User-input navigation"
DIV_OWNERSHIP = "3 Assumption Ownership"
DIV_RESULTS = "4 Results and audit trail"
DIV_ADVANCED = "5 Advanced - Governed"
DIV_FILL_IT = "FILL IT assessment only"
DIV_FILL_OT = "FILL OT assessment only"


def current_name(wb, *candidates: str) -> str:
    names = set(wb.sheetnames)
    for name in candidates:
        if name in names:
            return name
        mapped = OLD_TO_NEW.get(name)
        if mapped and mapped in names:
            return name if name in names else mapped
        legacy = NEW_TO_OLD.get(name)
        if legacy and legacy in names:
            return legacy
    raise KeyError(f"None of {candidates} exist in workbook")


def rewrite_formula_text(text: str) -> str:
    if not isinstance(text, str) or not text.startswith("="):
        return text
    out = text
    for old, new in sorted(OLD_TO_NEW.items(), key=lambda kv: len(kv[0]), reverse=True):
        out = out.replace(f"'{old}'", f"'{new}'")
        out = out.replace(f'"{old}"', f'"{new}"')
    out = out.replace("'00 COMMON - Run Setup'!C7=\"IT\"", "'00 COMMON - Run Setup'!C6=\"IT\"")
    out = out.replace("'00 COMMON - Run Setup'!C7=\"OT\"", "'00 COMMON - Run Setup'!C6=\"OT\"")
    out = out.replace("C7=\"IT\"", "C6=\"IT\"")
    out = out.replace("C7=\"OT\"", "C6=\"OT\"")
    return out
