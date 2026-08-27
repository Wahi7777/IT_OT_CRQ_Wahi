from ot_crq.packs import load_ot_pack
from tests.paths import ROOT

PACK = ROOT / "sector_packs" / "OT" / "OT_CRQ_Sector_Pack_Manufacturing_v1_0.xlsx"


def test_manufacturing_pack_supplies_scenario_propensity():
    import openpyxl

    wb = openpyxl.load_workbook(PACK, read_only=True, data_only=False)
    ids = []
    ws = wb["12 TTP Catalogue"]
    for r in range(16, 40):
        tid = str(ws.cell(r, 1).value or "").strip()
        if tid:
            ids.append(tid)
    wb.close()
    loaded = load_ot_pack(PACK, "Manufacturing", "Process Manufacturing", ids, "MF-v1.0")
    assert set(loaded["scenario_propensity"]) == {"Nation State", "Cybercriminal", "Malicious Insider"}
    for actor, row in loaded["scenario_propensity"].items():
        assert abs(sum(row.values()) - 1.0) < 1e-9, actor
