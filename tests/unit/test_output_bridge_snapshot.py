from it_ot_crq.router import _write_python_snapshot
import openpyxl
from tests.paths import COMBINED


def test_snapshot_overwrites_bridge_formulas_with_engine_numbers(tmp_path):
    wb = openpyxl.load_workbook(COMBINED)
    result = {
        "best_aal": 11.0,
        "prudent_aal": 22.0,
        "best_var95": 1.0,
        "prudent_var95": 2.0,
        "best_tvar95": 3.0,
        "prudent_tvar95": 4.0,
        "best_var99": 5.0,
        "prudent_var99": 6.0,
        "best_tvar99": 7.0,
        "prudent_tvar99": 8.0,
        "best_pany": 0.1,
        "prudent_pany": 0.2,
        "best_event_frequency": 0.3,
        "prudent_event_frequency": 0.4,
        "best_attempt_frequency": 0.5,
        "prudent_attempt_frequency": 0.6,
        "actor_aal": {"Nation State": 10.0, "Cybercriminal": 12.0},
        "scenario_aal": {"S1": 22.0},
        "random_seed": 1,
        "simulation_years": 10,
        "validation": "PASS",
    }
    meta = {
        "sector": "Power Generation",
        "domain": "OT",
        "engine_version": "1.7",
        "pack_id": "PG-v1.6",
        "pack_status": "test",
        "outside_in_applied": "No",
        "input_hash": "abc",
        "oi_hash": None,
        "timestamp": "t",
        "run_id": "r",
        "oi_schema": "1.0.0",
        "reporting_view": "Prudent",
        "asset_type": "CCGT",
    }
    _write_python_snapshot(wb, result, meta)
    bridge = wb["00 COMMON - Output Bridge"]
    assert bridge["B15"].value == 11.0
    assert bridge["C15"].value == 22.0
    assert bridge["A16"].value == "VaR 95"
    assert bridge["A17"].value == "TVaR 95"
    assert bridge["A18"].value == "VaR 99"
    assert bridge["A19"].value == "TVaR 99"
    assert bridge["A24"].value == "Risk-appetite status"
    assert not str(bridge["B21"].value).startswith("=")
    assert bridge["C21"].value == 0.4
    assert bridge["A27"].value == "Nation State"
    assert bridge["B27"].value == 10.0
    dash = wb["00 Dashboard"]
    assert dash["B31"].value == 10.0
    assert dash["B31"].number_format == r"$#,##0"
    drivers = wb["00 Risk Drivers"]
    assert "OT view" in str(drivers["A2"].value)
    assert drivers["B4"].value == "Cybercriminal"
    eng = wb["00 COMMON - Engine Results"]
    assert eng["C3"].value == 22.0
    dash = wb["00 Dashboard"]
    assert dash["B71"].value == 22.0
    assert dash["A7"].value == "P(ANY SUCCESSFUL EVENT / YR)"
    assert dash["D7"].value == "AAL"
    assert dash["G7"].value == "VaR 95"
    assert dash["J7"].value == "TVaR 95"
    out = tmp_path / "snap.xlsx"
    wb.save(out)
    wb.close()
    again = openpyxl.load_workbook(out)
    assert again["00 COMMON - Output Bridge"]["C15"].value == 22.0
    again.close()
