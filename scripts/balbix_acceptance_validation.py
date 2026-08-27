#!/usr/bin/env python3
"""Balbix unified-impact acceptance validation (does NOT freeze goldens)."""

from __future__ import annotations

import json
import math
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import openpyxl

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from crq.impact import DEPENDENCY_MODEL, OT_BALBIX_GAPS, OT_TO_BALBIX, driver_category, formulas
from crq.metrics import annual_aggregate_metrics, tvar_tail_contributions
from crq.reporting_helpers import portfolio_tail_reconcile
from it_ot_crq.router import run_combined
from tests.helpers import configure_run
from tests.paths import COMBINED

OUT = ROOT / "outputs" / "balbix_acceptance"
SEED = 20260821
PRE = ROOT / "outputs" / "RAKBANK_results_pre_balbix_unified.xlsx"


def _commit_id() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        return "no-git-repository"


def _set_years(wb, years: int) -> None:
    if "IT 03 - Organisation Inputs" in wb.sheetnames:
        wb["IT 03 - Organisation Inputs"]["C30"] = years
        wb["IT 03 - Organisation Inputs"]["C31"] = SEED


def _summarise_engine(er: dict) -> dict:
    annual = None  # not always returned
    metrics = {
        "aal": er.get("AAL") or er.get("prudent_aal"),
        "var95": er.get("VaR95") or er.get("prudent_var95"),
        "tvar95": er.get("TVaR95") or er.get("prudent_tvar95"),
        "var99": er.get("VaR99") or er.get("prudent_var99"),
        "tvar99": er.get("TVaR99") or er.get("prudent_tvar99"),
        "p_any": er.get("P_any") or er.get("prudent_pany"),
        "event_frequency": er.get("event_frequency"),
        "aal_se": er.get("prudent_aal_se"),
        "validation": er.get("validation"),
        "pack_id": er.get("sector_pack_id"),
        "top_component": er.get("top_tvar99_component"),
        "top_driver": er.get("top_tvar99_driver"),
        "impact_reconcile": er.get("impact_reconcile"),
        "impact_dependency": er.get("impact_dependency"),
        "scenario_aal": er.get("scenario_aal") or er.get("scenario_aal_prudent"),
        "actor_aal": er.get("actor_aal") or er.get("actor_aal_prudent"),
        "scenario_tvar99_contribution": er.get("scenario_tvar99_contribution"),
        "actor_tvar99_contribution": er.get("actor_tvar99_contribution"),
        "scenario_tvar95_contribution": er.get("scenario_tvar95_contribution"),
        "actor_tvar95_contribution": er.get("actor_tvar95_contribution"),
        "loss_components": er.get("loss_components"),
        "loss_drivers": er.get("loss_drivers"),
        "control_packages": [
            {
                "name": p.get("name"),
                "aal": (p.get("metrics") or {}).get("aal") or p.get("aal"),
                "reduction": (p.get("metrics") or {}).get("reduction"),
            }
            for p in (er.get("control_packages") or [])[:8]
        ],
        "whatif_top": [
            {
                "name": w.get("name"),
                "current": w.get("current"),
                "next": w.get("next") or w.get("whatif"),
                "reduction": ((w.get("prudent") or w.get("be") or {}).get("reduction")),
            }
            for w in (er.get("whatifs") or [])[:10]
        ],
        "balbix_gaps": er.get("balbix_gaps"),
    }
    return metrics


def run_rakbank(years: int, *, whatifs: bool, label: str) -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    model = OUT / f"rakbank_model_{label}.xlsx"
    out = OUT / f"rakbank_out_{label}.xlsx"
    shutil.copy2(ROOT / "assessments" / "RAKBANK.xlsx", model)
    wb = openpyxl.load_workbook(model)
    _set_years(wb, years)
    wb.save(model)
    wb.close()
    os.environ["CRQ_RUN_SENSITIVITY"] = "0"
    t0 = time.time()
    result = run_combined(model, out, run_whatifs=whatifs)
    elapsed = time.time() - t0
    er = result.get("engine_result") or result
    summary = _summarise_engine(er)
    summary["years"] = years
    summary["elapsed_s"] = elapsed
    summary["output"] = str(out)
    summary["command"] = (
        f"PYTHONPATH=src:. CRQ_RUN_SENSITIVITY=0 python -m crq run "
        f"--model {model} --out {out}" + (" --no-whatifs" if not whatifs else "")
    )
    return summary


def severity_bridge_from_workbook(model_path: Path) -> dict:
    """Compare block-sum vs driver-sum severity and sample event losses under dependency."""
    from it_crq.engine import _cells, _load_main, _load_pack, _lognormal, _prepare, _severity, _simulate
    import tempfile

    # Stage via a mini combined run's work dir is heavy; use router staging by running
    # prepare path: copy assessment through run_combined work — instead load pack from FS
    # and read org inputs from assessment IT sheet into a staged IT template.
    from it_ot_crq.router import IT_INPUT_SHEETS, IT_SHEET_MAP

    td = Path(tempfile.mkdtemp())
    it_path = td / "it.xlsx"
    shutil.copy2(ROOT / "model" / "it" / "Guided_IT_CRQ_Model_v1_1_1_Dashboard.xlsx", it_path)
    combined = openpyxl.load_workbook(model_path)
    staged = openpyxl.load_workbook(it_path)

    def copy_values(src, dst):
        for r in range(1, max(src.max_row, dst.max_row) + 1):
            for c in range(1, max(src.max_column, dst.max_column) + 1):
                cell = dst.cell(r, c)
                if cell.__class__.__name__ == "MergedCell":
                    continue
                cell.value = src.cell(r, c).value

    for n in IT_INPUT_SHEETS:
        if n in combined.sheetnames and IT_SHEET_MAP[n] in staged.sheetnames:
            copy_values(combined[n], staged[IT_SHEET_MAP[n]])
    staged["03 Organisation Inputs"]["C19"] = "Financial Services"
    staged["03 Organisation Inputs"]["C30"] = 50000
    staged["03 Organisation Inputs"]["C31"] = SEED
    staged.save(it_path)
    combined.close()
    staged.close()

    wb = openpyxl.load_workbook(it_path)
    pack = _load_pack(wb, it_path)
    _prepare(wb, pack)
    main = _load_main(wb, pack)
    severity, audit = _severity(main, pack)
    cells, _, _ = _cells(main, pack, severity)
    rho = pack["settings"]["LOSS_BLOCK_RHO"]

    # Scenario-level: sum driver P50/P99 and former block-fit means for first actor route cell per scenario
    by_sc = {}
    for c in cells:
        sid = c["scenario_id"]
        if sid not in by_sc:
            by_sc[sid] = c
    bridge = []
    for sid, c in by_sc.items():
        drivers = c.get("drivers") or []
        blocks = c.get("blocks") or []
        sum_p50 = sum(d["p50"] for d in drivers)
        sum_p99 = sum(d["p99"] for d in drivers)
        block_p50 = sum(b["p50"] for b in blocks)
        block_p99 = sum(b["p99"] for b in blocks)
        # Sample event losses under channel-comonotonic draws (fixed event count)
        tiny = [{**c, "event_rate": 1e9}]  # force many events in 1 year — better: direct draw
        # Direct sample of one-event severity distribution
        rng = np.random.default_rng(SEED)
        n_ev = 20000
        common = rng.standard_normal(n_ev)
        channel_z = {
            ch: math.sqrt(rho) * common + math.sqrt(max(1 - rho, 0)) * rng.standard_normal(n_ev)
            for ch in ("Duration", "Exposure", "Direct")
        }
        loss = np.zeros(n_ev)
        for d in drivers:
            z = channel_z[d["block"]]
            loss += np.exp(d["mu"] + d["sigma"] * z)
        # Former block-level sampling
        loss_block = np.zeros(n_ev)
        rng2 = np.random.default_rng(SEED)
        common2 = rng2.standard_normal(n_ev)
        for b in blocks:
            z = math.sqrt(rho) * common2 + math.sqrt(max(1 - rho, 0)) * rng2.standard_normal(n_ev)
            loss_block += np.exp(b["mu"] + b["sigma"] * z)
        bridge.append(
            {
                "scenario": c["scenario"],
                "scenario_id": sid,
                "sum_driver_p50": sum_p50,
                "sum_driver_p99": sum_p99,
                "block_channel_p50_sum": block_p50,
                "block_channel_p99_sum": block_p99,
                "expected_event_mean_drivers": sum(d["mean"] for d in drivers),
                "expected_event_mean_blocks": sum(b["mean"] for b in blocks),
                "sim_driver_p50": float(np.quantile(loss, 0.50)),
                "sim_driver_p95": float(np.quantile(loss, 0.95)),
                "sim_driver_p99": float(np.quantile(loss, 0.99)),
                "sim_driver_mean": float(loss.mean()),
                "sim_block_p50": float(np.quantile(loss_block, 0.50)),
                "sim_block_p95": float(np.quantile(loss_block, 0.95)),
                "sim_block_p99": float(np.quantile(loss_block, 0.99)),
                "sim_block_mean": float(loss_block.mean()),
                "n_drivers": len(drivers),
                "n_blocks": len(blocks),
            }
        )
    # Fraud calibration check from audit / org
    org = main["org"]
    fraud_rows = [a for a in audit if a[4] == "FRAUD_NET_RECOVERY" and a[5] == "P50" and a[7]]
    return {
        "rho": rho,
        "dependency": DEPENDENCY_MODEL,
        "org_exposures": {
            "ANNUAL_REVENUE_AT_RISK": org.get("ANNUAL_REVENUE_AT_RISK"),
            "ANNUAL_PAYMENT_VALUE": org.get("ANNUAL_PAYMENT_VALUE"),
            "BI_LOSS_FACTOR": org.get("BI_LOSS_FACTOR"),
            "SENSITIVE_RECORDS": org.get("SENSITIVE_RECORDS"),
            "CRITICAL_ENDPOINTS": org.get("CRITICAL_ENDPOINTS"),
            "CRITICAL_SERVERS": org.get("CRITICAL_SERVERS"),
        },
        "scenarios": bridge,
        "note": (
            "block_channel_p50_sum equals sum_driver_p50 by construction (channels sum driver P50s). "
            "sim_block_* uses lognormals fitted to channel sums; sim_driver_* sums comonotonic "
            "per-driver lognormals — these differ by design."
        ),
    }


def read_pre_refactor() -> dict:
    wb = openpyxl.load_workbook(PRE, data_only=True)
    ws = wb["01 Executive Risk Story"]
    out = {
        "aal": ws["B6"].value,
        "var95": ws["B7"].value,
        "tvar95": ws["B8"].value,
        "var99": ws["B9"].value,
        "tvar99": ws["B10"].value,
        "p_any": ws["B5"].value,
        "top_component": ws["B25"].value,
        "target_aal": ws["B31"].value,
    }
    ws = wb["04 Business Impact"]
    comps = []
    for r in range(36, 45):
        name = ws.cell(r, 1).value
        if not name:
            break
        comps.append(
            {
                "name": name,
                "aal": ws.cell(r, 2).value,
                "contrib_tvar99": ws.cell(r, 4).value,
            }
        )
    out["loss_components"] = comps
    # Scenario analysis sheet
    if "03 Scenario Analysis" in wb.sheetnames:
        ws = wb["03 Scenario Analysis"]
        # best-effort scrape
    wb.close()
    return out


def convergence_check(rows: list[dict]) -> dict:
    """Documented bands from scripts/tiered_e2e_validation.py, applied across N ladder."""
    tolerances = {"aal": 0.05, "var95": 0.08, "tvar95": 0.12, "var99": 0.10, "tvar99": 0.15}
    base = next(r for r in rows if r["years"] == 500000)
    checks = []
    for r in rows:
        if r["years"] == 500000:
            continue
        entry = {"years": r["years"], "metrics": {}}
        for metric, tol in tolerances.items():
            a, b = r.get(metric), base.get(metric)
            if a is None or b is None:
                continue
            abs_d = float(b) - float(a)
            pct = abs_d / float(a) if a else None
            se = r.get("aal_se")
            within = abs(pct) <= tol if pct is not None else None
            if metric == "aal" and within is False and se is not None:
                # scale SE from smaller N toward comparison with 500k: accept |Δ| ≤ 2× SE(small)
                if abs(abs_d) <= 2.0 * float(se):
                    within = True
            entry["metrics"][metric] = {
                "at_n": a,
                "at_500k": b,
                "abs_diff": abs_d,
                "pct_diff": pct,
                "tolerance_pct": tol,
                "within_tolerance": within,
                "aal_se_at_n": se if metric == "aal" else None,
            }
        checks.append(entry)
    overall = all(
        m.get("within_tolerance") for c in checks for m in c["metrics"].values() if m.get("within_tolerance") is not None
    )
    return {"checks": checks, "overall_pass": overall, "method": "tiered_e2e_validation bands"}


def reconcile_tables(er_summary: dict) -> dict:
    aal = float(er_summary["aal"])
    t95 = float(er_summary["tvar95"])
    t99 = float(er_summary["tvar99"])

    def _sum_rows(rows, key="aal"):
        return float(sum(float(r.get(key) or 0) for r in (rows or [])))

    def _sum_dict(d):
        return float(sum(float(v) for v in (d or {}).values()))

    def _row(name, total, agg):
        diff = total - agg
        pct = (diff / agg) if agg else None
        return {
            "view": name,
            "sum": total,
            "aggregate": agg,
            "abs_diff": diff,
            "pct_diff": pct,
            "ok": abs(diff) <= max(1.0, abs(agg) * 1e-6),
        }

    comps = er_summary.get("loss_components") or []
    drvs = er_summary.get("loss_drivers") or []
    return {
        "aal_drivers": _row("driver AAL", _sum_rows(drvs, "aal"), aal),
        "aal_categories": _row("category AAL", _sum_rows(comps, "aal"), aal),
        "aal_scenarios": _row("scenario AAL", _sum_dict(er_summary.get("scenario_aal")), aal),
        "aal_actors": _row("actor AAL", _sum_dict(er_summary.get("actor_aal")), aal),
        "tvar95_drivers": _row("driver TVaR95 c", _sum_rows(drvs, "contrib_tvar95"), t95),
        "tvar95_categories": _row("category TVaR95 c", _sum_rows(comps, "contrib_tvar95"), t95),
        "tvar95_scenarios": _row(
            "scenario TVaR95 c", _sum_dict(er_summary.get("scenario_tvar95_contribution")), t95
        ),
        "tvar95_actors": _row(
            "actor TVaR95 c", _sum_dict(er_summary.get("actor_tvar95_contribution")), t95
        ),
        "tvar99_drivers": _row("driver TVaR99 c", _sum_rows(drvs, "contrib_tvar99"), t99),
        "tvar99_categories": _row("category TVaR99 c", _sum_rows(comps, "contrib_tvar99"), t99),
        "tvar99_scenarios": _row(
            "scenario TVaR99 c", _sum_dict(er_summary.get("scenario_tvar99_contribution")), t99
        ),
        "tvar99_actors": _row(
            "actor TVaR99 c", _sum_dict(er_summary.get("actor_tvar99_contribution")), t99
        ),
    }


def workbook_qa(path: Path) -> list[dict]:
    wb = openpyxl.load_workbook(path, data_only=True)
    findings = []
    ws = wb["04 Business Impact"]
    cats = []
    for r in range(36, 48):
        if ws.cell(r, 1).value:
            cats.append(ws.cell(r, 1).value)
    drivers = []
    for r in range(50, 80):
        if ws.cell(r, 1).value and ws.cell(r, 2).value:
            drivers.append((ws.cell(r, 1).value, ws.cell(r, 2).value))
    findings.append({"check": "categories present", "pass": bool(cats), "detail": cats})
    findings.append({"check": "drivers present", "pass": bool(drivers), "detail": len(drivers)})
    findings.append(
        {
            "check": "fraud not labelled Incident response",
            "pass": not any("Incident response" == c for c in cats)
            and any("Direct Loss of Funds" in str(c) for c in cats),
            "detail": cats,
        }
    )
    ws = wb["01 Executive Risk Story"]
    headline = ws["B25"].value
    findings.append(
        {
            "check": "executive headline is Direct Loss of Funds",
            "pass": headline is not None and "Direct Loss of Funds" in str(headline),
            "detail": headline,
        }
    )
    findings.append(
        {
            "check": "no See Business Impact placeholder",
            "pass": "See Business Impact" not in str(headline or ""),
            "detail": headline,
        }
    )
    # Category AAL vs driver AAL
    cat_aal = sum(float(ws.cell(r, 2).value or 0) for r in range(36, 48) if wb["04 Business Impact"].cell(r, 1).value)
    # re-read BI
    bi = wb["04 Business Impact"]
    cat_aal = sum(float(bi.cell(r, 2).value or 0) for r in range(36, 48) if bi.cell(r, 1).value)
    drv_aal = sum(float(bi.cell(r, 3).value or 0) for r in range(50, 80) if bi.cell(r, 1).value and bi.cell(r, 2).value)
    findings.append(
        {
            "check": "category AAL ≈ driver AAL on sheet",
            "pass": abs(cat_aal - drv_aal) <= max(1.0, 1e-4 * max(cat_aal, 1)),
            "detail": {"category_aal": cat_aal, "driver_aal": drv_aal, "diff": cat_aal - drv_aal},
        }
    )
    wb.close()
    return findings


def sector_pack_runs() -> list[dict]:
    OUT.mkdir(parents=True, exist_ok=True)
    configs = [
        ("Financial Services", "Organisation", 25000, True),
        ("Power Generation", "CCGT", None, False),
        ("Energy Assets", "Upstream Onshore", None, False),
        ("Manufacturing", "Process Manufacturing", None, False),
    ]
    rows = []
    for sector, asset, years, is_it in configs:
        model = OUT / f"pack_{sector.replace(' ', '_')}.xlsx"
        out = OUT / f"pack_out_{sector.replace(' ', '_')}.xlsx"
        shutil.copy2(COMBINED, model)
        wb = openpyxl.load_workbook(model)
        configure_run(wb, sector, asset)
        if years:
            _set_years(wb, years)
        wb.save(model)
        wb.close()
        os.environ["CRQ_RUN_SENSITIVITY"] = "0"
        os.environ["OT_CRQ_USE_XLSX_BACKEND"] = "1"
        result = run_combined(model, out, run_whatifs=False)
        er = result.get("engine_result") or result
        row = {
            "sector": sector,
            "asset": asset,
            "domain": "IT" if is_it else "OT",
            "validation": er.get("validation"),
            "aal": er.get("AAL") or er.get("prudent_aal"),
            "tvar99": er.get("TVaR99") or er.get("prudent_tvar99"),
            "pack_id": er.get("sector_pack_id"),
            "top_component": er.get("top_tvar99_component"),
            "impact_reconcile_ok": (er.get("impact_reconcile") or {}).get("ok"),
            "balbix_gaps": er.get("balbix_gaps")
            or ([{"id": k, "reason": v} for k, v in OT_BALBIX_GAPS.items()] if not is_it else []),
            "categories": [c.get("name") for c in (er.get("loss_components") or [])],
            "drivers": [d.get("name") for d in (er.get("loss_drivers") or [])] if is_it else None,
            "ot_to_balbix_map": OT_TO_BALBIX if not is_it else None,
        }
        rows.append(row)
    return rows


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "commit": _commit_id(),
        "seed": SEED,
        "pack": "FS-v1.1.1",
        "model": "Guided_IT_OT_CRQ_Model_v1_0 / assessments/RAKBANK.xlsx",
        "dependency": DEPENDENCY_MODEL,
        "pre_refactor": read_pre_refactor(),
    }

    # Severity bridge from RAKBANK assessment
    print("=== severity bridge ===", flush=True)
    model_copy = OUT / "rakbank_bridge_model.xlsx"
    shutil.copy2(ROOT / "assessments" / "RAKBANK.xlsx", model_copy)
    report["severity_bridge"] = severity_bridge_from_workbook(model_copy)

    # Convergence ladder (no whatifs)
    print("=== convergence ladder ===", flush=True)
    ladder = []
    for n in (25000, 100000, 250000, 500000):
        print(f"--- N={n} ---", flush=True)
        whatifs = n == 500000
        s = run_rakbank(n, whatifs=whatifs, label=f"n{n}")
        ladder.append(s)
        (OUT / f"summary_n{n}.json").write_text(json.dumps(s, indent=2, default=str))
    report["convergence_ladder"] = ladder
    report["convergence_check"] = convergence_check(ladder)
    prod = next(r for r in ladder if r["years"] == 500000)
    report["production_500k"] = prod
    report["reconciliation"] = reconcile_tables(prod)

    # Copy production workbook to canonical RAKBANK_results path for QA
    shutil.copy2(prod["output"], ROOT / "outputs" / "RAKBANK_results.xlsx")
    report["workbook_qa"] = workbook_qa(ROOT / "outputs" / "RAKBANK_results.xlsx")

    print("=== sector packs ===", flush=True)
    report["sector_packs"] = sector_pack_runs()

    print("=== pytest ===", flush=True)
    py = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "--tb=line"],
        cwd=ROOT,
        env={**os.environ, "PYTHONPATH": f"{ROOT / 'src'}:{ROOT}"},
        capture_output=True,
        text=True,
    )
    report["pytest"] = {
        "returncode": py.returncode,
        "stdout_tail": "\n".join(py.stdout.splitlines()[-20:]),
        "stderr_tail": "\n".join(py.stderr.splitlines()[-20:]),
    }

    (OUT / "acceptance_report.json").write_text(json.dumps(report, indent=2, default=str))
    print("Wrote", OUT / "acceptance_report.json", flush=True)
    print("pytest rc", py.returncode, flush=True)


if __name__ == "__main__":
    main()
