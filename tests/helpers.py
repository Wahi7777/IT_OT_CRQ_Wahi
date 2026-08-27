"""Shared workbook setup for tests after domain-first Run Setup."""

from crq.sheet_names import COMMON_RUN_SETUP, IT_ORG, OT_FACILITY
from it_ot_crq.router import SECTOR_DOMAIN


def configure_run(wb, sector: str, asset: str, basis: str = "Prudent", outside_in: str = "No") -> None:
    domain = SECTOR_DOMAIN[sector]
    setup = wb[COMMON_RUN_SETUP if COMMON_RUN_SETUP in wb.sheetnames else "00 Run Setup"]
    if setup.title.startswith("00 COMMON"):
        setup["C6"] = domain
        setup["C7"] = sector
        setup["C8"] = asset
    else:
        setup["C6"] = sector
        setup["C8"] = asset
    setup["C9"] = basis
    setup["C10"] = outside_in
    if domain == "OT":
        fac = OT_FACILITY if OT_FACILITY in wb.sheetnames else "03 Facility Inputs"
        if fac in wb.sheetnames:
            wb[fac]["C20"] = sector
            wb[fac]["C21"] = asset
