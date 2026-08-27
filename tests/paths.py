from pathlib import Path

from it_ot_crq.navigation import NAV_TAB_ORDER as EXPECTED_TAB_ORDER

ROOT = Path(__file__).resolve().parents[1]
_v1 = ROOT / "model" / "Guided_IT_OT_CRQ_Model_v1_0.xlsx"
_v03 = ROOT / "model" / "Guided_IT_OT_CRQ_Combined_Model_v0_3.xlsx"
COMBINED = _v1 if _v1.is_file() else _v03
