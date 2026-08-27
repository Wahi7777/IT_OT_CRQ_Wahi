import json
import os

import pytest

from tests.paths import ROOT

FIXTURES = [
    "whatif_fs_500k.json",
    "whatif_pg_500k.json",
    "whatif_ea_500k.json",
    "whatif_mf_500k.json",
]


@pytest.mark.production
@pytest.mark.parametrize("name", FIXTURES)
def test_whatif_production_fixture(name):
    path = ROOT / "tests" / "fixtures" / name
    if not path.is_file():
        if os.environ.get("CRQ_REQUIRE_GOLDENS") == "1":
            pytest.fail(f"Missing what-if golden {path}. Run freeze_whatifs.py")
        pytest.skip(f"Missing what-if golden {path}")
    data = json.loads(path.read_text())
    assert data["N"] == 500_000
    assert data["validation"] == "PASS"
    assert data["monotonicity_prudent"] >= -1e-6
    reds = [c["aal_reduction"] for c in data["top_controls"]]
    assert reds == sorted(reds, reverse=True)
    assert data["whatifs_ran"] is True
