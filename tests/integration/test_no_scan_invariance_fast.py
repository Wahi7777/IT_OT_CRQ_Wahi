"""Fast no-scan invariance: identical copies of the combined workbook, OI=No."""
import shutil

import openpyxl
import pytest

from tests.helpers import configure_run
from tests.paths import COMBINED


@pytest.mark.parametrize("sector,asset", [
    ("Power Generation", "CCGT"),
    ("Energy Assets", "Upstream Onshore"),
    ("Manufacturing", "Process Manufacturing"),
])
def test_ot_no_scan_native_equals_combined_deterministic(tmp_path, monkeypatch, sector, asset):
    monkeypatch.setenv("OT_CRQ_USE_XLSX_BACKEND", "1")
    from ot_crq.engine import refresh

    def prep(path):
        shutil.copy2(COMBINED, path)
        wb = openpyxl.load_workbook(path)
        configure_run(wb, sector, asset)
        wb.save(path)
        wb.close()

    native = tmp_path / "native.xlsx"
    combined = tmp_path / "combined.xlsx"
    prep(native)
    prep(combined)
    a = refresh(str(native), str(native), run_whatifs=False, simulate=False)
    b = refresh(str(combined), str(combined), run_whatifs=False, simulate=False)
    assert a["sector_pack_id"] == b["sector_pack_id"]
    assert a["lambda_be"] == pytest.approx(b["lambda_be"])
    assert a["facility_mult"] == pytest.approx(b["facility_mult"])
    for key in a["combos"]:
        assert a["combos"][key]["p_success"] == pytest.approx(b["combos"][key]["p_success"])
