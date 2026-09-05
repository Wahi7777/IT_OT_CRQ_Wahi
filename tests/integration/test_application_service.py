from __future__ import annotations

import copy
import shutil

import openpyxl
import pytest

from crq.application import RunConfig, extract_assessment, public_assessment_payload, run_it_assessment, run_ot_assessment
from crq.application.bundle_resolver import resolve_approved_bundle
from crq.application.request_adapter import assessment_from_public_payload
from crq.application.serialization import dumps, loads
from crq.application.service import execute_assessment, validate_response_payload
from tests.helpers import configure_run
from tests.paths import COMBINED


CASES = (
    ("IT", "Financial Services", "Organisation", "FS-v1.1.1"),
    ("OT", "Power Generation", "CCGT", "PG-v1.6"),
    ("OT", "Energy Assets", "Upstream Onshore", "EA-v1.0"),
    ("OT", "Manufacturing", "Process Manufacturing", "MF-v1.0"),
)


def _without_transient_run_identity(value):
    payload = copy.deepcopy(value)
    for key in ("run_id", "started_at", "completed_at"):
        payload["run"].pop(key, None)
    payload["provenance"]["result_hash"] = ""
    router = payload["compatibility"]["router_metadata"]
    # The compatibility workbook is regenerated in a fresh XLSX archive for
    # each invocation; ZIP timestamps make its binary file hash transient.
    # Canonical assessment_hash is compared elsewhere and is stable.
    for key in ("run_id", "timestamp", "input_hash"):
        router.pop(key, None)
    return payload


@pytest.mark.production
@pytest.mark.parametrize("domain,sector,asset,bundle_id", CASES, ids=lambda value: str(value).replace(" ", "-"))
def test_application_service_exactly_matches_phase2_facade(domain, sector, asset, bundle_id, tmp_path):
    source = tmp_path / "source.xlsx"
    shutil.copy2(COMBINED, source)
    wb = openpyxl.load_workbook(source)
    configure_run(wb, sector, asset, basis="Prudent", outside_in="No")
    wb.save(source)
    wb.close()
    public = public_assessment_payload(extract_assessment(source, run_whatifs=False))
    runtime = public["runtime"]
    request = {
        "schema_version": "1.0.0",
        "request_id": f"parity-{bundle_id}",
        "assessment": public,
        "model_bundle_reference": {"bundle_id": bundle_id, "bundle_version": "1.0.0"},
        "run_config": {
            "reporting_basis": "Prudent",
            "simulation_count": runtime["simulation_count"],
            "random_seed": runtime["random_seed"],
        },
    }
    response = execute_assessment(request)
    assert response.status == "SUCCESS", response.error
    validate_response_payload(response.to_dict())

    assessment = assessment_from_public_payload(public)
    bundle = resolve_approved_bundle(bundle_id, "1.0.0", domain, sector)
    config = RunConfig(runtime["simulation_count"], runtime["random_seed"])
    facade = run_it_assessment if domain == "IT" else run_ot_assessment
    expected = facade(assessment, bundle, config).to_dict()

    assert dumps(_without_transient_run_identity(response.result)) == dumps(_without_transient_run_identity(expected))
    assert response.result["compatibility"]["legacy_engine_extension"] == expected["compatibility"]["legacy_engine_extension"]
    serialized = response.to_json()
    assert loads(serialized) == response.to_dict()
    assert '"NaN"' not in serialized and ':NaN' not in serialized
    assert "Infinity" not in serialized
    assert "output" not in response.result["compatibility"]["legacy_engine_extension"]
