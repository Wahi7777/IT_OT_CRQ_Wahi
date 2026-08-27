import json
import os

import pytest

from tests.paths import ROOT

FIXTURES = [
    "regression_it_fs_500k.json",
    "regression_ot_power_generation.json",
    "regression_ot_energy_assets.json",
    "regression_ot_manufacturing.json",
]


@pytest.mark.production
@pytest.mark.parametrize("name", FIXTURES)
def test_production_golden_fixture(name):
    path = ROOT / "tests" / "fixtures" / name
    if not path.is_file():
        if os.environ.get("CRQ_REQUIRE_GOLDENS") == "1":
            pytest.fail(f"Missing production golden {path}. Run freeze_goldens.py")
        pytest.skip(f"Missing production golden {path}")
    data = json.loads(path.read_text())
    assert data["simulation_years"] == 500_000
    assert data["validation"] == "PASS"
    assert data["outside_in_applied"] == "No"
    total_actors = sum(data["actor_aal"].values())
    total_scen = sum(data["scenario_aal"].values())
    assert abs(total_actors - data["prudent_aal"]) <= max(1.0, 1e-6 * abs(data["prudent_aal"]))
    assert abs(total_scen - data["prudent_aal"]) <= max(1.0, 1e-6 * abs(data["prudent_aal"]))
    assert data["input_sha256"]
    assert data.get("native_vs_combined") == "exact-or-1e-6-rel"
