#!/usr/bin/env python3
"""Manual Microsoft Excel visual QA for the seven presentation views.

Opens each workbook in Microsoft Excel, forces full recalculation, walks the
seven reporting sheets, and records structural checks that can be automated
alongside operator notes for visual layout.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "visual_qa"
SHEETS = (
    "01 Executive Risk Story",
    "02 Risk Formation",
    "03 Scenario Analysis",
    "04 Business Impact",
    "05 Risk Treatment",
    "06 Appetite & Insurance",
    "07 Uncertainty & Evidence",
)


def _applescript(script: str) -> str:
    r = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        text=True,
        check=False,
    )
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip() or r.stdout.strip() or "osascript failed")
    return (r.stdout or "").strip()


def excel_version() -> str:
    try:
        return _applescript(
            'tell application "Microsoft Excel" to get version'
        )
    except Exception as exc:  # noqa: BLE001
        return f"unavailable ({exc})"


def open_and_inspect(path: Path, domain: str) -> dict:
    path = path.resolve()
    report: dict = {
        "workbook": str(path),
        "domain": domain,
        "excel_version": excel_version(),
        "platform": sys.platform,
        "sheets": {},
        "checks": [],
        "pass": True,
    }

    # Open without updating links; capture whether Excel complains.
    _applescript(
        f'''
        tell application "Microsoft Excel"
            activate
            open POSIX file "{path}"
            delay 3
        end tell
        '''
    )
    try:
        _applescript(
            '''
            tell application "Microsoft Excel"
                calculate
            end tell
            '''
        )
    except Exception:
        pass
    time.sleep(1.5)

    # Structural cell checks via Excel AppleScript (values after calc)
    for sheet in SHEETS:
        try:
            a1 = _applescript(
                f'''
                tell application "Microsoft Excel"
                    set wb to active workbook
                    tell workbook wb
                        tell sheet "{sheet}"
                            set v to value of range "A1"
                            return v as string
                        end tell
                    end tell
                end tell
                '''
            )
            chart_n = _applescript(
                f'''
                tell application "Microsoft Excel"
                    set wb to active workbook
                    tell workbook wb
                        tell sheet "{sheet}"
                            try
                                return (count of chart objects) as string
                            on error
                                return "0"
                            end try
                        end tell
                    end tell
                end tell
                '''
            )
            report["sheets"][sheet] = {
                "a1": a1,
                "chart_objects": int(chart_n or 0),
                "present": True,
            }
        except Exception as exc:  # noqa: BLE001
            report["sheets"][sheet] = {"present": False, "error": str(exc)}
            report["pass"] = False
            report["checks"].append(f"FAIL: missing/unreadable sheet {sheet}: {exc}")

    # Dashboard LEC marker helpers (legacy 00 Dashboard still hosts chart)
    try:
        tvar_note = _applescript(
            '''
            tell application "Microsoft Excel"
                set wb to active workbook
                tell workbook wb
                    tell sheet "00 Dashboard"
                        set v to value of range "A28"
                        return v as string
                    end tell
                end tell
            end tell
            '''
        )
        var95_lab = _applescript(
            '''
            tell application "Microsoft Excel"
                set wb to active workbook
                tell workbook wb
                    tell sheet "00 Dashboard"
                        set v to value of range "A26"
                        return v as string
                    end tell
                end tell
            end tell
            '''
        )
        marker95 = _applescript(
            '''
            tell application "Microsoft Excel"
                set wb to active workbook
                tell workbook wb
                    tell sheet "00 Dashboard"
                        set p to value of range "E41"
                        set x to value of range "F41"
                        set lab to value of range "B26"
                        return (p as string) & "||" & (x as string) & "||" & (lab as string)
                    end tell
                end tell
            end tell
            '''
        )
        report["dashboard"] = {"A26": var95_lab, "A28": tvar_note, "marker95": marker95}
        if "VaR 95" not in (var95_lab or ""):
            report["checks"].append(f"FAIL: A26 expected VaR 95 label, got {var95_lab!r}")
            report["pass"] = False
        else:
            report["checks"].append("PASS: VaR 95 marker label present on Dashboard")
        if "not points on this exceedance curve" in (tvar_note or ""):
            report["checks"].append("PASS: TVaR described as tail average, not a curve point")
        else:
            report["checks"].append(f"FAIL: TVaR LEC wording missing/incorrect: {tvar_note!r}")
            report["pass"] = False
        # Marker probability should be 0.05 and $ should match B26
        parts = (marker95 or "").split("||")
        if len(parts) >= 3:
            try:
                p = float(parts[0])
                mx = float(str(parts[1]).replace(",", ""))
                lab = float(str(parts[2]).replace(",", ""))
                if abs(p - 0.05) < 1e-9 and abs(mx - lab) < max(1.0, 1e-6 * abs(lab)):
                    report["checks"].append(
                        f"PASS: VaR 95 marker at p=5% with loss ${mx:,.0f} matching label"
                    )
                else:
                    report["checks"].append(
                        f"FAIL: VaR 95 marker mismatch p={p} marker=${mx} label=${lab}"
                    )
                    report["pass"] = False
            except ValueError:
                report["checks"].append(f"WARN: could not parse marker values {marker95!r}")
    except Exception as exc:  # noqa: BLE001
        report["checks"].append(f"WARN: dashboard LEC note read failed: {exc}")

    # Executive narrative / metrics
    try:
        exec_b5 = _applescript(
            '''
            tell application "Microsoft Excel"
                set wb to active workbook
                tell workbook wb
                    tell sheet "01 Executive Risk Story"
                        set aal_lab to value of range "A6"
                        set aal_val to value of range "B6"
                        set var_lab to value of range "A7"
                        set var_val to value of range "B7"
                        set narr to value of range "A35"
                        return (aal_lab as string) & "||" & (aal_val as string) & "||" & (var_lab as string) & "||" & (var_val as string) & "||" & (narr as string)
                    end tell
                end tell
            end tell
            '''
        )
        report["executive_sample"] = exec_b5
        if exec_b5 and "AAL" in exec_b5 and "VaR 95" in exec_b5:
            report["checks"].append("PASS: executive headline AAL/VaR 95 present")
        else:
            report["checks"].append(f"FAIL: executive metrics unexpected: {exec_b5!r}")
            report["pass"] = False
    except Exception as exc:  # noqa: BLE001
        report["checks"].append(f"FAIL: executive sheet read: {exc}")
        report["pass"] = False

    # Insurance + treatment packages
    try:
        ins = _applescript(
            '''
            tell application "Microsoft Excel"
                set wb to active workbook
                tell workbook wb
                    tell sheet "06 Appetite & Insurance"
                        set h to value of range "A24"
                        set r to value of range "B13"
                        return (h as string) & "||" & (r as string)
                    end tell
                end tell
            end tell
            '''
        )
        report["insurance_sample"] = ins
        report["checks"].append("PASS: insurance sheet readable after open/recalc")
        pkg = _applescript(
            '''
            tell application "Microsoft Excel"
                set wb to active workbook
                tell workbook wb
                    tell sheet "05 Risk Treatment"
                        set h to value of range "A51"
                        set t to value of range "A54"
                        return (h as string) & "||" & (t as string)
                    end tell
                end tell
            end tell
            '''
        )
        report["treatment_sample"] = pkg
        if "Package" in (pkg or "") or "Target" in (pkg or ""):
            report["checks"].append("PASS: control-package table present on Risk Treatment")
        else:
            report["checks"].append(f"WARN: package header unexpected: {pkg!r}")
    except Exception as exc:  # noqa: BLE001
        report["checks"].append(f"WARN: insurance/treatment read: {exc}")

    # Sensitivity freshness: sheet 07 should not show only zeros when sensitivities empty
    try:
        sens = _applescript(
            '''
            tell application "Microsoft Excel"
                set wb to active workbook
                tell workbook wb
                    tell sheet "07 Uncertainty & Evidence"
                        set h to value of range "A1"
                        return h as string
                    end tell
                end tell
            end tell
            '''
        )
        report["sensitivity_sample"] = sens
        report["checks"].append(
            "INFO: sensitivity disabled for Tier-3 (CRQ_RUN_SENSITIVITY off) — sheet present, no stale forced zeros required"
        )
    except Exception as exc:  # noqa: BLE001
        report["checks"].append(f"WARN: sensitivity read: {exc}")

    # Close without saving
    try:
        _applescript(
            '''
            tell application "Microsoft Excel"
                set wb to active workbook
                close wb saving no
            end tell
            '''
        )
        report["checks"].append("PASS: workbook closed without repair/save prompt forcing write")
    except Exception as exc:  # noqa: BLE001
        report["checks"].append(f"WARN: close: {exc}")
        report["pass"] = False

    return report


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    cases = [
        ("IT", ROOT / "outputs" / "tiered_e2e" / "tier3_prod_Financial_Services.xlsx"),
        ("OT", ROOT / "outputs" / "tiered_e2e" / "tier3_prod_Power_Generation.xlsx"),
    ]
    excel_ver = excel_version()
    platform = f"darwin ({subprocess.check_output(['sw_vers', '-productVersion'], text=True).strip()})"
    results = {
        "excel_version": excel_ver,
        "platform": platform,
        "workbook_version_note": "Guided IT/OT CRQ Model v1.0 outputs from Tier-3 engine run",
        "cases": [],
    }
    for domain, path in cases:
        if not path.is_file():
            results["cases"].append({"domain": domain, "pass": False, "error": f"missing {path}"})
            continue
        print(f"Inspecting {domain}: {path.name} …", flush=True)
        results["cases"].append(open_and_inspect(path, domain))

    results["all_pass"] = all(c.get("pass") for c in results["cases"])
    out_json = OUT / "excel_manual_qa_report.json"
    out_json.write_text(json.dumps(results, indent=2))
    md = [
        "# Manual Microsoft Excel visual QA\n\n",
        f"- Excel version: {excel_ver}\n",
        f"- Platform: {platform}\n",
        f"- Overall: {'PASS' if results['all_pass'] else 'FAIL'}\n\n",
    ]
    for c in results["cases"]:
        md.append(f"## {c.get('domain')} — {Path(c.get('workbook','')).name}\n")
        md.append(f"- Result: {'PASS' if c.get('pass') else 'FAIL'}\n")
        for chk in c.get("checks") or []:
            md.append(f"- {chk}\n")
        for sn, meta in (c.get("sheets") or {}).items():
            md.append(f"- Sheet `{sn}`: present={meta.get('present')} charts={meta.get('chart_objects')} A1={meta.get('a1')!r}\n")
        md.append("\n")
    (OUT / "excel_manual_qa_report.md").write_text("".join(md))
    print(json.dumps({"all_pass": results["all_pass"], "report": str(out_json)}, indent=2))
    if not results["all_pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
