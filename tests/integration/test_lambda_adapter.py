from __future__ import annotations

import copy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from crq.application.serialization import dumps
from crq.application.service import validate_response_payload
from crq.lambda_adapter import handler


ROOT = Path(__file__).resolve().parents[2]
CASES = ("it-fs", "ot-pg")


def _canonical(value):
    payload = copy.deepcopy(value)
    for key in ("run_id", "started_at", "completed_at"):
        payload["run"].pop(key, None)
    payload["provenance"]["result_hash"] = ""
    for key in ("run_id", "timestamp", "input_hash"):
        payload["compatibility"]["router_metadata"].pop(key, None)
    return payload


@pytest.mark.production
@pytest.mark.parametrize("case_id", CASES)
def test_lambda_boundary_preserves_phase3a_result(case_id):
    request = json.loads((ROOT / f"contracts/examples/assessment-run-request-{case_id}.json").read_text())
    approved = json.loads((ROOT / f"contracts/examples/assessment-run-response-{case_id}.json").read_text())
    event = {
        "version": "2.0",
        "rawPath": "/v1/assessments/run",
        "headers": {"content-type": "application/json; charset=utf-8"},
        "requestContext": {"requestId": f"gateway-{case_id}", "http": {"method": "POST", "path": "/v1/assessments/run"}},
        "isBase64Encoded": False,
        "body": dumps(request),
    }
    response = handler(event, SimpleNamespace(aws_request_id=f"lambda-{case_id}"))
    assert response["statusCode"] == 200
    assert response["headers"]["content-type"] == "application/json"
    payload = json.loads(response["body"])
    validate_response_payload(payload)
    assert payload["status"] == "SUCCESS"
    assert dumps(_canonical(payload["result"])) == dumps(_canonical(approved["result"]))
