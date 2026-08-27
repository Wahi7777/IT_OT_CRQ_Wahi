"""Freeze production-N goldens. Invoked by `python -m crq validate-release --production` or directly."""
from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
os.environ.setdefault("OT_CRQ_USE_XLSX_BACKEND", "1")

from crq.io_safety import sha256_file  # noqa: E402
from it_ot_crq.router import run_combined  # noqa: E402
from tests.helpers import configure_run  # noqa: E402

COMBINED = ROOT / "model" / "Guided_IT_OT_CRQ_Model_v1_0.xlsx"
if not COMBINED.is_file():
    COMBINED = ROOT / "model" / "Guided_IT_OT_CRQ_Combined_Model_v0_3.xlsx"

CASES = [
    ("Financial Services", "Organisation", "regression_it_fs_500k.json", True),
    ("Power Generation", "CCGT", "regression_ot_power_generation.json", False),
    ("Energy Assets", "Upstream Onshore", "regression_ot_energy_assets.json", False),
    ("Manufacturing", "Process Manufacturing", "regression_ot_manufacturing.json", False),
]


def _payload(sector, asset, result, input_hash):
    er = result["engine_result"]
    return {
        "sector": sector,
        "asset_type": asset,
        "domain": result["domain"],
        "combined_version": "1.0.0",
        "engine_version": er.get("engine_version") or result.get("engine_version"),
        "pack_id": result.get("pack_id"),
        "pack_status": result.get("pack_status"),
        "seed": er.get("random_seed"),
        "simulation_years": er.get("simulation_years"),
        "input_sha256": input_hash,
        "outside_in_applied": "No",
        "validation": result.get("validation"),
        "best_aal": er.get("best_aal"),
        "prudent_aal": er.get("prudent_aal"),
        "best_var95": er.get("best_var95"),
        "prudent_var95": er.get("prudent_var95"),
        "best_tvar95": er.get("best_tvar95"),
        "prudent_tvar95": er.get("prudent_tvar95"),
        "best_var99": er.get("best_var99"),
        "prudent_var99": er.get("prudent_var99"),
        "best_tvar99": er.get("best_tvar99"),
        "prudent_tvar99": er.get("prudent_tvar99"),
        "best_pany": er.get("best_pany"),
        "prudent_pany": er.get("prudent_pany"),
        "best_attempt_frequency": er.get("best_attempt_frequency", er.get("BestEstimateLambda")),
        "prudent_attempt_frequency": er.get("prudent_attempt_frequency", er.get("PrudentLambda")),
        "best_event_frequency": er.get("best_event_frequency", er.get("event_frequency")),
        "prudent_event_frequency": er.get("prudent_event_frequency"),
        "attempt_frequency": er.get("attempt_frequency"),
        "event_frequency": er.get("event_frequency"),
        "actor_aal": er.get("actor_aal"),
        "scenario_aal": er.get("scenario_aal"),
    }


def freeze_one(sector, asset, filename, is_it, out_dir: Path, work: Path):
    import openpyxl

    src = work / f"in_{filename.replace('.json', '')}.xlsx"
    dest = work / f"out_{filename.replace('.json', '')}.xlsx"
    shutil.copy2(COMBINED, src)
    wb = openpyxl.load_workbook(src)
    configure_run(wb, sector, asset)
    if is_it:
        from crq.sheet_names import IT_ORG
        name = IT_ORG if IT_ORG in wb.sheetnames else "IT 03 Organisation Inputs"
        wb[name]["C30"] = 500_000
    wb.save(src)
    wb.close()
    input_hash = sha256_file(src)
    result = run_combined(
        src,
        output=dest,
        sector_pack_dir=ROOT / "sector_packs",
        work_dir=work / "it_stage",
        run_whatifs=False,
    )
    payload = _payload(sector, asset, result, input_hash)

    native = work / f"native_{filename.replace('.json', '')}.xlsx"
    shutil.copy2(src, native)
    if is_it:
        from it_ot_crq.router import _run_it
        native_result = _run_it(native, ROOT / "sector_packs" / "IT", work / "native_it", ROOT)
    else:
        from it_ot_crq.router import _run_ot
        native_result = _run_ot(native, run_whatifs=False)
    er = result["engine_result"]
    for key in ("best_aal", "prudent_aal", "best_tvar99", "prudent_tvar99", "best_pany", "prudent_pany"):
        a, b = er.get(key), native_result.get(key)
        if a is None or b is None:
            raise SystemExit(f"Missing {key} in native/combined compare")
        if abs(float(a) - float(b)) > 1e-6 * max(1.0, abs(float(a))):
            raise SystemExit(f"No-scan invariance failed for {sector} {key}: combined={a} native={b}")
    payload["native_vs_combined"] = "exact-or-1e-6-rel"
    path = out_dir / filename
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(f"WROTE {path} validation={payload['validation']} prudent_aal={payload['prudent_aal']}")
    return payload


def main():
    out_dir = ROOT / "tests" / "fixtures"
    out_dir.mkdir(parents=True, exist_ok=True)
    work = ROOT / "_work" / "golden_freeze"
    work.mkdir(parents=True, exist_ok=True)
    only = sys.argv[1:]
    for sector, asset, filename, is_it in CASES:
        if only and filename not in only and sector not in only:
            continue
        freeze_one(sector, asset, filename, is_it, out_dir, work)


if __name__ == "__main__":
    main()
