"""OT pack resolution without Monte Carlo."""
import shutil

import openpyxl
import pytest

from tests.helpers import configure_run
from tests.paths import COMBINED


@pytest.mark.parametrize(
    "sector,asset,pack",
    [
        ("Power Generation", "CCGT", "PG-v1.6"),
        ("Energy Assets", "Upstream Onshore", "EA-v1.0"),
        ("Manufacturing", "Process Manufacturing", "MF-v1.0"),
    ],
)
def test_ot_sector_pack_resolution(tmp_path, monkeypatch, sector, asset, pack):
    dest = tmp_path / f"{pack}.xlsx"
    shutil.copy2(COMBINED, dest)
    wb = openpyxl.load_workbook(dest)
    configure_run(wb, sector, asset)
    wb.save(dest)
    wb.close()
    monkeypatch.setenv("OT_CRQ_USE_XLSX_BACKEND", "1")
    from ot_crq.engine import refresh
    result = refresh(str(dest), str(dest), run_whatifs=False, simulate=False)
    assert result["sector"] == sector
    assert result["asset_type"] == asset
    assert result["sector_pack_id"] == pack
    assert len(result["combos"]) == 15
    # Financial Services must never be loadable as an OT pack
    assert result["sector"] != "Financial Services"


def test_invalid_asset_type_fails_closed(tmp_path, monkeypatch):
    dest = tmp_path / "bad.xlsx"
    shutil.copy2(COMBINED, dest)
    wb = openpyxl.load_workbook(dest)
    wb["OT 03 - Facility Inputs"]["C20"] = "Power Generation"
    wb["OT 03 - Facility Inputs"]["C21"] = "Not An Asset"
    wb.save(dest)
    wb.close()
    monkeypatch.setenv("OT_CRQ_USE_XLSX_BACKEND", "1")
    from ot_crq.engine import refresh
    with pytest.raises(ValueError, match="exactly one row"):
        refresh(str(dest), str(dest), simulate=False)
