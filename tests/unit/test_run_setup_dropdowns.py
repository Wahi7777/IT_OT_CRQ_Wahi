from it_ot_crq.router import apply_run_setup_asset_dropdowns
import openpyxl
from crq.sheet_names import COMMON_RUN_SETUP, OT_FACILITY
from tests.paths import COMBINED


def test_run_setup_domain_filters_sector_and_asset():
    wb = openpyxl.load_workbook(COMBINED)
    apply_run_setup_asset_dropdowns(wb)
    setup = wb[COMMON_RUN_SETUP]
    formulas = []
    has_domain = False
    has_sector = False
    for dv in setup.data_validations.dataValidation:
        ref = str(dv.sqref)
        if "C8" in ref:
            formulas.append(str(dv.formula1))
        if "C6" in ref:
            has_domain = True
        if "C7" in ref:
            has_sector = True
    assert formulas and all("INDIRECT" in f and "$C$7" in f for f in formulas)
    assert has_domain and has_sector
    assert "IT_Sectors" in {str(n) for n in wb.defined_names}
    fac = str(wb[OT_FACILITY]["A3"].value or "")
    assert "C6" in fac and "OT" in fac
    wb.close()
