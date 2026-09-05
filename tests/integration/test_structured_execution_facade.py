"""Engine-executing parity between workbook execution and the structured facade."""

from __future__ import annotations

import shutil

import openpyxl
import pytest

from crq.application import (
    RunConfig,
    extract_assessment,
    load_model_bundle,
    run_it_assessment,
    run_ot_assessment,
)
from crq.application.models import json_value
from tests.helpers import configure_run
from tests.paths import COMBINED, ROOT


CASES = (
    ("IT", "Financial Services", "Organisation"),
    ("OT", "Power Generation", "CCGT"),
    ("OT", "Energy Assets", "Upstream Onshore"),
    ("OT", "Manufacturing", "Process Manufacturing"),
)


@pytest.mark.production
@pytest.mark.parametrize("domain,sector,asset", CASES, ids=lambda value: str(value).replace(" ", "-"))
def test_structured_facade_is_lossless_and_quantitatively_exact(domain, sector, asset, tmp_path, monkeypatch):
    monkeypatch.setenv("OT_CRQ_USE_XLSX_BACKEND", "1")
    source = tmp_path / "source.xlsx"
    direct_output = tmp_path / "direct.xlsx"
    shutil.copy2(COMBINED, source)
    wb = openpyxl.load_workbook(source)
    configure_run(wb, sector, asset, basis="Prudent", outside_in="No")
    wb.save(source)
    wb.close()

    from it_ot_crq.router import run_combined

    direct = run_combined(
        source,
        output=direct_output,
        sector_pack_dir=ROOT / "sector_packs",
        work_dir=tmp_path / "direct-work",
        run_whatifs=False,
    )
    assessment = extract_assessment(source, run_whatifs=False)
    bundle = load_model_bundle(domain, sector, project_root=ROOT)
    runtime = assessment.to_dict()["runtime"]
    config = RunConfig(
        simulation_count=runtime["simulation_count"],
        random_seed=runtime["random_seed"],
        run_whatifs=False,
        run_packages=False,
        run_sensitivity=False,
    )
    facade = run_it_assessment if domain == "IT" else run_ot_assessment
    structured = facade(assessment, bundle, config).to_dict()

    expected_native = json_value({k: v for k, v in direct["engine_result"].items() if k != "output"})
    actual_native = {k: v for k, v in structured["compatibility"]["legacy_engine_extension"].items() if k != "output"}
    assert actual_native == expected_native
    assert structured["compatibility"]["lossless"] is True

    for basis, prefix in (("best_estimate", "best"), ("prudent", "prudent")):
        metrics = structured["summary"][basis]
        for canonical, native in (("aal", "aal"), ("var95", "var95"), ("var99", "var99"), ("tvar95", "tvar95"), ("tvar99", "tvar99"), ("event_frequency", "event_frequency"), ("p_any_event", "pany")):
            assert metrics[canonical] == direct["engine_result"][f"{prefix}_{native}"]
    assert structured["provenance"]["engine_version"] == direct["engine_result"]["engine_version"]
    assert structured["provenance"]["sector_pack_id"] == direct["pack_id"]
    assert structured["provenance"]["bundle_hash"] == bundle.to_dict()["bundle_hash"]
    assert structured["decomposition"]["actors"]
    assert structured["decomposition"]["scenarios"]
    assert structured["loss"]["categories"] == direct["engine_result"].get("loss_components", [])
    assert structured["treatments"]["individual_controls"] == direct["engine_result"].get("whatifs", [])
    assert structured["insurance"] == json_value(direct["engine_result"].get("insurance_analysis") or {})


def test_assessment_ownership_excludes_governed_pack_cells(tmp_path):
    source = tmp_path / "source.xlsx"
    shutil.copy2(COMBINED, source)
    assessment = extract_assessment(source)
    records = assessment.to_dict()["compatibility"]["workbook_cells"]
    assert records
    assert {row["classification"] for row in records} <= {
        "USER_INPUT", "PERMITTED_OVERRIDE", "EVIDENCE_ONLY", "INACTIVE_LEGACY"
    }
    assert not any(row["sheet"].startswith("OT PACK") or row["sheet"].startswith("IT PACK") for row in records)
    assert assessment.to_dict()["compatibility"]["inactive_legacy"]["employees"] == 1000


def test_model_bundle_is_content_hashed_and_immutable():
    bundle = load_model_bundle("OT", "Power Generation", project_root=ROOT)
    data = bundle.to_dict()
    assert len(data["bundle_hash"]) == 64
    assert data["sector_pack"]["pack_hash"] == "77b3d0b86a6ed82c66063d40663a308e35a6ad357f08e493e03d1a9ae321cf0b"
    assert data["assumptions"]["governed_mappings"]["pack_workbook_snapshot"]
    with pytest.raises(TypeError):
        bundle._data["engine_version"] = "changed"
