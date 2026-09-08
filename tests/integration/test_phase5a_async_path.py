from __future__ import annotations

import copy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import crq.product.api_lambda as api
import crq.product.worker_lambda as worker
from crq.application.serialization import dumps
from crq.application.models import CRQResult
from crq.product.storage import MemoryJobQueue, MemoryObjectStore


ROOT = Path(__file__).resolve().parents[2]
CONTEXT = SimpleNamespace(aws_request_id="phase5a-integration")


def _event(method: str, path: str, body=None, headers=None):
    return {
        "version": "2.0",
        "rawPath": path,
        "headers": {"content-type": "application/json", **(headers or {})},
        "requestContext": {
            "requestId": "gateway-phase5a",
            "http": {"method": method, "path": path},
            "authorizer": {"jwt": {"claims": {"sub": "approved-test-user", "custom:tenant_id": "approved-test-tenant"}}},
        },
        "isBase64Encoded": False,
        "body": None if body is None else dumps(body),
    }


def _body(response):
    return json.loads(response["body"])


def _canonical(value):
    payload = copy.deepcopy(value)
    for key in ("run_id", "started_at", "completed_at"):
        payload["run"].pop(key, None)
    payload["provenance"]["result_hash"] = ""
    for key in ("run_id", "timestamp", "input_hash"):
        payload["compatibility"]["router_metadata"].pop(key, None)
    return payload


@pytest.mark.production
@pytest.mark.parametrize("case_id", ("it-fs", "ot-pg"))
def test_authenticated_async_product_path_preserves_approved_result(monkeypatch, case_id):
    request = json.loads((ROOT / f"contracts/examples/assessment-run-request-{case_id}.json").read_text())
    approved = json.loads((ROOT / f"contracts/examples/assessment-run-response-{case_id}.json").read_text())
    store, queue = MemoryObjectStore(), MemoryJobQueue()
    monkeypatch.setattr(api, "_STORE", store)
    monkeypatch.setattr(api, "_QUEUE", queue)
    monkeypatch.setattr(worker, "_STORE", store)

    created = api.handler(_event("POST", "/v1/assessments", request["assessment"]), CONTEXT)
    assert created["statusCode"] == 201
    assessment_id = request["assessment"]["assessment"]["assessment_id"]
    run_body = {key: request[key] for key in ("schema_version", "request_id", "model_bundle_reference", "run_config")}
    accepted = api.handler(
        _event("POST", f"/v1/assessments/{assessment_id}/run", run_body, {"idempotency-key": f"phase5a-{case_id}-approved"}),
        CONTEXT,
    )
    assert accepted["statusCode"] == 202
    run_id = _body(accepted)["run_id"]
    assert len(queue.messages) == 1

    worker_response = worker.handler({"Records": [{"messageId": f"job-{case_id}", "body": dumps(queue.messages[0])}]}, CONTEXT)
    assert worker_response == {"batchItemFailures": []}
    status = _body(api.handler(_event("GET", f"/v1/runs/{run_id}"), CONTEXT))
    assert status["status"] == "COMPLETED"
    assert status["result_available"] is True
    result_response = api.handler(_event("GET", f"/v1/runs/{run_id}/result"), CONTEXT)
    assert result_response["statusCode"] == 200
    result = _body(result_response)
    assert CRQResult.from_dict(result).to_dict() == result
    assert dumps(_canonical(result)) == dumps(_canonical(approved["result"]))
