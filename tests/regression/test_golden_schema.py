import json

from tests.paths import ROOT

REGRESSION_DIR = ROOT / "tests" / "fixtures"


def test_regression_fixture_schema():
    path = REGRESSION_DIR / "regression_it_fs.json"
    if not path.exists():
        return
    data = json.loads(path.read_text())
    for key in (
        "sector", "engine_version", "pack_id", "seed", "best_aal", "prudent_aal",
        "actor_aal", "scenario_aal", "event_frequency",
    ):
        assert key in data
