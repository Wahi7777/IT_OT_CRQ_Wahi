"""IT engine functional path with reduced years (CI-feasible)."""
import json
import shutil

import openpyxl
import pytest

from tests.helpers import configure_run
from tests.paths import COMBINED, ROOT

FIXTURE = ROOT / "tests" / "fixtures" / "regression_it_fs.json"


@pytest.mark.integration
def test_financial_services_it_engine(tmp_path):
    dest = tmp_path / "fs.xlsx"
    shutil.copy2(COMBINED, dest)
    wb = openpyxl.load_workbook(dest)
    configure_run(wb, "Financial Services", "Organisation")
    wb["IT 03 - Organisation Inputs"]["C30"] = 50000
    wb.save(dest)
    wb.close()

    from it_ot_crq.router import run_combined
    out = tmp_path / "fs_out.xlsx"
    result = run_combined(
        dest,
        output=out,
        sector_pack_dir=ROOT / "sector_packs",
        work_dir=tmp_path / "work",
        run_whatifs=False,
    )
    assert result["domain"] == "IT"
    assert result["pack_id"] == "FS-v1.1.1"
    er = result["engine_result"]
    assert er["validation"] == "PASS"
    view_aal = er["prudent_aal"]
    actor_sum = sum(er["actor_aal"].values())
    scenario_sum = sum(er["scenario_aal"].values())
    assert abs(actor_sum - view_aal) < max(1.0, 1e-6 * abs(view_aal))
    assert abs(scenario_sum - view_aal) < max(1.0, 1e-6 * abs(view_aal))

    snapshot = {
        "sector": "Financial Services",
        "engine_version": er["engine_version"],
        "pack_id": er["pack_id"],
        "seed": er["random_seed"],
        "n": er["simulation_years"],
        "best_aal": er["best_aal"],
        "prudent_aal": er["prudent_aal"],
        "best_var95": er["best_var95"],
        "prudent_tvar99": er["prudent_tvar99"],
        "event_frequency": er["event_frequency"],
        "actor_aal": er["actor_aal"],
        "scenario_aal": er["scenario_aal"],
    }
    FIXTURE.parent.mkdir(parents=True, exist_ok=True)
    if not FIXTURE.exists():
        FIXTURE.write_text(json.dumps(snapshot, indent=2))
    golden = json.loads(FIXTURE.read_text())
    assert golden["pack_id"] == snapshot["pack_id"]
    assert snapshot["n"] == 50000
    assert abs(snapshot["best_aal"] - golden["best_aal"]) <= max(1.0, 0.02 * abs(golden["best_aal"]))
    assert abs(snapshot["prudent_aal"] - golden["prudent_aal"]) <= max(1.0, 0.02 * abs(golden["prudent_aal"]))
    # Fixture stores full five-metric set after Outcome B re-freeze
    if "best_var95" in golden:
        assert abs(er["best_var95"] - golden["best_var95"]) <= max(1.0, 0.05 * abs(golden["best_var95"]))
        assert abs(er["prudent_tvar99"] - golden["prudent_tvar99"]) <= max(1.0, 0.08 * abs(golden["prudent_tvar99"]))

    out_wb = openpyxl.load_workbook(out)
    assert out_wb["00 COMMON - Output Bridge"]["I7"].value == "IT"
    assert out_wb["00 COMMON - Output Bridge"]["H43"].value == "IT engine version"
    assert not str(out_wb["00 COMMON - Output Bridge"]["A43"].value).startswith("=")
    assert out_wb["00 Dashboard"]["B34"].number_format == r"$#,##0"
    assert out_wb["00 Dashboard"]["A34"].value == "Hacktivist"
    assert "IT view" in str(out_wb["00 Risk Drivers"]["A2"].value)
    assert out_wb["00 Risk Drivers"]["D4"].value == "Critical business-service disruption"
    assert "IT CALC - Frequency" in str(out_wb["00 Risk Drivers"]["B8"].value)
    assert "Move into OT" not in str(out_wb["00 Risk Drivers"]["G16"].value or "")
    out_wb.close()
