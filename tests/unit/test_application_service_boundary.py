from __future__ import annotations

import copy
import shutil

import numpy as np
import openpyxl
import pytest

from crq.application import extract_assessment, public_assessment_payload
from crq.application.errors import ErrorCode
from crq.application.request_adapter import assessment_from_public_payload
from crq.application.serialization import dumps, loads
from crq.application.service import AssessmentRunRequest, execute_assessment, validate_response_payload
from tests.helpers import configure_run
from tests.paths import COMBINED


@pytest.fixture(scope="module")
def requests(tmp_path_factory):
    root = tmp_path_factory.mktemp("application-requests")
    output = {}
    for case_id, sector, asset, bundle in (
        ("it", "Financial Services", "Organisation", "FS-v1.1.1"),
        ("ot", "Power Generation", "CCGT", "PG-v1.6"),
    ):
        source = root / f"{case_id}.xlsx"
        shutil.copy2(COMBINED, source)
        wb = openpyxl.load_workbook(source)
        configure_run(wb, sector, asset, basis="Prudent", outside_in="No")
        wb.save(source)
        wb.close()
        assessment = public_assessment_payload(extract_assessment(source))
        output[case_id] = {
            "schema_version": "1.0.0",
            "request_id": f"unit-{case_id}",
            "assessment": assessment,
            "model_bundle_reference": {"bundle_id": bundle, "bundle_version": "1.0.0"},
            "run_config": {
                "reporting_basis": "Prudent",
                "simulation_count": assessment["runtime"]["simulation_count"],
                "random_seed": assessment["runtime"]["random_seed"],
            },
        }
    return output


def _error(request, code):
    response = execute_assessment(request)
    validate_response_payload(response.to_dict())
    assert response.status == "ERROR"
    assert response.error["code"] == code.value
    assert response.result is None
    assert "/Users/" not in response.to_json()


def test_request_round_trip_is_deterministic(requests):
    parsed = AssessmentRunRequest.from_dict(requests["it"])
    assert AssessmentRunRequest.from_json(parsed.to_json()).to_dict() == parsed.to_dict()


def test_it_assessment_hash_is_stable_across_json_key_order(requests):
    payload = copy.deepcopy(requests["it"]["assessment"])
    frequency = payload["domain_inputs"]["frequency_adjustments"]
    payload["domain_inputs"]["frequency_adjustments"] = dict(reversed(list(frequency.items())))
    before = assessment_from_public_payload(payload).to_dict()["assessment_hash"]
    after = assessment_from_public_payload(loads(dumps(payload))).to_dict()["assessment_hash"]
    assert before == after


def test_invalid_domain_is_rejected(requests):
    request = copy.deepcopy(requests["it"])
    request["assessment"]["assessment"]["domain"] = "Cloud"
    _error(request, ErrorCode.UNSUPPORTED_DOMAIN)


def test_unsupported_bundle_is_rejected(requests):
    request = copy.deepcopy(requests["it"])
    request["model_bundle_reference"]["bundle_id"] = "FS-v999"
    _error(request, ErrorCode.MODEL_BUNDLE_NOT_FOUND)


def test_it_assessment_with_ot_bundle_is_rejected(requests):
    request = copy.deepcopy(requests["it"])
    request["model_bundle_reference"]["bundle_id"] = "PG-v1.6"
    _error(request, ErrorCode.MODEL_BUNDLE_INCOMPATIBLE)


def test_ot_assessment_with_it_bundle_is_rejected(requests):
    request = copy.deepcopy(requests["ot"])
    request["model_bundle_reference"]["bundle_id"] = "FS-v1.1.1"
    _error(request, ErrorCode.MODEL_BUNDLE_INCOMPATIBLE)


def test_invalid_application_schema_version_is_rejected(requests):
    request = copy.deepcopy(requests["it"])
    request["schema_version"] = "9.0.0"
    _error(request, ErrorCode.SCHEMA_VERSION_UNSUPPORTED)


def test_invalid_assessment_schema_version_is_rejected(requests):
    request = copy.deepcopy(requests["ot"])
    request["assessment"]["schema_version"] = "9.0.0"
    _error(request, ErrorCode.SCHEMA_VERSION_UNSUPPORTED)


def test_unsupported_sector_is_rejected(requests):
    request = copy.deepcopy(requests["ot"])
    request["assessment"]["assessment"]["sector"] = "Water"
    _error(request, ErrorCode.UNSUPPORTED_SECTOR)


def test_incompatible_asset_type_is_rejected(requests):
    request = copy.deepcopy(requests["ot"])
    request["assessment"]["assessment"]["asset_type"] = "Upstream Onshore"
    _error(request, ErrorCode.MODEL_BUNDLE_INCOMPATIBLE)


@pytest.mark.parametrize("key", ["actor_priors", "dependency", "pack_path", "workbook_path"])
def test_governed_assumptions_and_paths_cannot_be_injected(requests, key):
    request = copy.deepcopy(requests["it"])
    request["assessment"]["domain_inputs"][key] = {"caller": "controlled"}
    _error(request, ErrorCode.INVALID_REQUEST)


def test_unknown_run_fields_are_rejected(requests):
    request = copy.deepcopy(requests["ot"])
    request["run_config"]["run_sensitivity"] = True
    _error(request, ErrorCode.INVALID_REQUEST)


def test_serialization_normalizes_numpy_and_rejects_non_finite_values():
    assert loads(dumps({"integer": np.int64(7), "number": np.float64(1.25)})) == {"integer": 7, "number": 1.25}
    with pytest.raises(ValueError):
        dumps({"not_a_number": np.float64("nan")})
