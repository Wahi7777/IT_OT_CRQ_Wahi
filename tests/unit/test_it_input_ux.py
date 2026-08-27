import shutil

import openpyxl

from it_ot_crq.navigation import apply_workbook_navigation
from tests.paths import COMBINED


def test_it_06_scale_links_to_it_03_and_dropdowns_restored(tmp_path):
    dest = tmp_path / "ux.xlsx"
    shutil.copy2(COMBINED, dest)
    wb = openpyxl.load_workbook(dest)
    apply_workbook_navigation(wb, domain="IT")
    org = wb["IT 03 - Organisation Inputs"]
    bia = wb["IT 06 - Impact & BIA Overrides"]
    assert org["C19"].value == "='00 COMMON - Run Setup'!C7"
    assert bia["B7"].value == "='IT 03 - Organisation Inputs'!C21"
    assert bia["B8"].value == "='IT 03 - Organisation Inputs'!C22"
    org_dvs = {str(dv.sqref) for dv in org.data_validations.dataValidation}
    assert any("C20" in s for s in org_dvs)
    assert any("C29" in s for s in org_dvs)
    exp = wb["IT 04 - Exposure Adjustments"]
    assert exp.data_validations.dataValidation
    ctrl = wb["IT 05 - Control Assessment"]
    assert ctrl.data_validations.dataValidation
    wb.close()
