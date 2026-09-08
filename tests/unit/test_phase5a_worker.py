from __future__ import annotations

import json
from pathlib import Path

import pytest

import crq.product.api_lambda as api
import crq.product.worker_lambda as worker
from crq.application.service import AssessmentRunResponse
from crq.product.storage import MemoryJobQueue, MemoryObjectStore


ROOT = Path(__file__).resolve().parents[2]
REQUEST = json.loads((ROOT / "contracts/examples/assessment-run-request-it-fs.json").read_text())
APPROVED = json.loads((ROOT / "contracts/examples/assessment-run-response-it-fs.json").read_text())


def event(method, path, body=None, headers=None):
    return {"version": "2.0", "rawPath": path, "headers": {"content-type": "application/json", **(headers or {})}, "requestContext": {"requestId": "test", "http": {"method": method, "path": path}, "authorizer": {"jwt": {"claims": {"sub": "user-a", "custom:tenant_id": "tenant-a"}}}}, "body": None if body is None else json.dumps(body), "isBase64Encoded": False}


@pytest.fixture
def prepared(monkeypatch):
    store, queue = MemoryObjectStore(), MemoryJobQueue()
    monkeypatch.setattr(api, "_STORE", store)
    monkeypatch.setattr(api, "_QUEUE", queue)
    monkeypatch.setattr(worker, "_STORE", store)
    assert api.handler(event("POST", "/v1/assessments", REQUEST["assessment"]), None)["statusCode"] == 201
    body = {key: REQUEST[key] for key in ("schema_version", "request_id", "model_bundle_reference", "run_config")}
    accepted = api.handler(event("POST", "/v1/assessments/IT-CRQ-001/run", body, {"idempotency-key": "phase5a-worker-test-01"}), None)
    return store, queue, json.loads(accepted["body"])["run_id"]


def sqs(queue):
    return {"Records": [{"messageId": "message-1", "body": json.dumps(queue.messages[0]), "attributes": {"ApproximateReceiveCount": "1"}}]}


def success_response():
    payload = APPROVED
    return AssessmentRunResponse(request_id=payload["request_id"], status="SUCCESS", result=payload["result"], warnings=tuple(payload["warnings"]), validation=payload["validation"], error=None)


def test_worker_completes_and_duplicate_delivery_does_not_recompute(prepared, monkeypatch):
    store, queue, run_id = prepared
    calls = []
    monkeypatch.setattr(worker, "execute_assessment", lambda request: calls.append(request) or success_response())
    assert worker.handler(sqs(queue), None) == {"batchItemFailures": []}
    assert worker.handler(sqs(queue), None) == {"batchItemFailures": []}
    assert len(calls) == 1
    status = json.loads(api.handler(event("GET", f"/v1/runs/{run_id}"), None)["body"])
    assert status["status"] == "COMPLETED"
    assert status["result_available"] is True
    result = api.handler(event("GET", f"/v1/runs/{run_id}/result"), None)
    assert result["statusCode"] == 200
    assert json.loads(result["body"])["summary"] == APPROVED["result"]["summary"]


def test_governed_application_failure_becomes_failed(prepared, monkeypatch):
    _, queue, run_id = prepared
    monkeypatch.setattr(worker, "execute_assessment", lambda request: AssessmentRunResponse(request_id="x", status="ERROR", result=None, warnings=(), validation={}, error={"code": "VALIDATION_FAILED", "message": "The request failed validation.", "details": {}}))
    assert worker.handler(sqs(queue), None) == {"batchItemFailures": []}
    status = json.loads(api.handler(event("GET", f"/v1/runs/{run_id}"), None)["body"])
    assert status["status"] == "FAILED"
    assert status["error_code"] == "VALIDATION_FAILED"
    assert api.handler(event("GET", f"/v1/runs/{run_id}/result"), None)["statusCode"] == 409


def test_unexpected_failure_is_safe_and_requests_retry(prepared, monkeypatch):
    _, queue, run_id = prepared
    monkeypatch.setattr(worker, "execute_assessment", lambda request: (_ for _ in ()).throw(RuntimeError("secret assessment content")))
    assert worker.handler(sqs(queue), None) == {"batchItemFailures": [{"itemIdentifier": "message-1"}]}
    status = json.loads(api.handler(event("GET", f"/v1/runs/{run_id}"), None)["body"])
    assert status["status"] == "FAILED"
    assert status["error_code"] == "WORKER_EXECUTION_FAILED"
    assert "secret" not in json.dumps(status).lower()
