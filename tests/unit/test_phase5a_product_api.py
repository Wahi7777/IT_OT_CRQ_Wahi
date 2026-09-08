from __future__ import annotations

import copy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import crq.product.api_lambda as api
from crq.product.storage import MemoryJobQueue, MemoryObjectStore


ROOT = Path(__file__).resolve().parents[2]
ASSESSMENT = json.loads((ROOT / "contracts/examples/assessment-run-request-it-fs.json").read_text())
CONTEXT = SimpleNamespace(aws_request_id="phase5a-api-test")


def event(method: str, path: str, body=None, *, tenant="tenant-a", user="user-a", authenticated=True, headers=None):
    claims = {"sub": user, "custom:tenant_id": tenant} if authenticated else {}
    return {
        "version": "2.0",
        "rawPath": path,
        "headers": {"content-type": "application/json", **(headers or {})},
        "requestContext": {"requestId": "gateway-test", "http": {"method": method, "path": path}, "authorizer": {"jwt": {"claims": claims}}},
        "isBase64Encoded": False,
        "body": None if body is None else json.dumps(body),
    }


def parsed(response):
    return json.loads(response["body"])


@pytest.fixture
def services(monkeypatch):
    store, queue = MemoryObjectStore(), MemoryJobQueue()
    monkeypatch.setattr(api, "_STORE", store)
    monkeypatch.setattr(api, "_QUEUE", queue)
    return store, queue


def create(services, tenant="tenant-a", user="user-a"):
    response = api.handler(event("POST", "/v1/assessments", ASSESSMENT["assessment"], tenant=tenant, user=user), CONTEXT)
    assert response["statusCode"] == 201
    return response


def run_body():
    return {key: ASSESSMENT[key] for key in ("schema_version", "request_id", "model_bundle_reference", "run_config")}


def test_health_is_public_and_protected_routes_require_verified_claims(services):
    assert api.handler(event("GET", "/health", authenticated=False), CONTEXT)["statusCode"] == 200
    assert api.handler(event("GET", "/v1/assessments/a", authenticated=False), CONTEXT)["statusCode"] == 401


def test_create_read_and_tenant_isolation(services):
    create(services)
    own = api.handler(event("GET", "/v1/assessments/IT-CRQ-001"), CONTEXT)
    other = api.handler(event("GET", "/v1/assessments/IT-CRQ-001", tenant="tenant-b", user="user-b"), CONTEXT)
    assert own["statusCode"] == 200
    assert parsed(own)["metadata"]["tenant_id"] == "tenant-a"
    assert other["statusCode"] == 404


def test_caller_cannot_inject_paths_or_governed_assumptions(services):
    injected = copy.deepcopy(ASSESSMENT["assessment"])
    injected["s3_key"] = "runs/tenant-b/secret/result.json"
    assert api.handler(event("POST", "/v1/assessments", injected), CONTEXT)["statusCode"] in {400, 422}
    governed = copy.deepcopy(ASSESSMENT["assessment"])
    governed["assumptions"] = {"frequency_priors": {"override": 999}}
    assert api.handler(event("POST", "/v1/assessments", governed), CONTEXT)["statusCode"] in {400, 422}


def test_submit_is_idempotent_and_message_is_minimal(services):
    _, queue = services
    create(services)
    headers = {"idempotency-key": "phase5a-idempotency-0001"}
    first = api.handler(event("POST", "/v1/assessments/IT-CRQ-001/run", run_body(), headers=headers), CONTEXT)
    second = api.handler(event("POST", "/v1/assessments/IT-CRQ-001/run", run_body(), headers=headers), CONTEXT)
    assert first["statusCode"] == second["statusCode"] == 202
    assert parsed(first)["run_id"] == parsed(second)["run_id"]
    assert len(queue.messages) == 1
    assert set(queue.messages[0]) == {"job_schema_version", "run_id", "assessment_id", "tenant_id", "bundle_id", "run_config"}
    serialized = json.dumps(queue.messages[0]).lower()
    assert not any(word in serialized for word in ("financial_exposure", "controls", "insurance", "architecture", "s3_key"))


def test_submit_retry_recovers_a_persisted_but_not_enqueued_run(services, monkeypatch):
    _, queue = services
    create(services)

    class FailOnceQueue:
        def __init__(self):
            self.failed = False

        def send(self, message):
            if not self.failed:
                self.failed = True
                raise RuntimeError("simulated queue outage")
            queue.send(message)

    flaky = FailOnceQueue()
    monkeypatch.setattr(api, "_QUEUE", flaky)
    request = event("POST", "/v1/assessments/IT-CRQ-001/run", run_body(), headers={"idempotency-key": "phase5a-recover-enqueue-1"})
    assert api.handler(request, CONTEXT)["statusCode"] == 500
    assert api.handler(request, CONTEXT)["statusCode"] == 202
    assert len(queue.messages) == 1


def test_run_and_result_are_tenant_isolated_and_pending_is_deterministic(services):
    create(services)
    response = api.handler(event("POST", "/v1/assessments/IT-CRQ-001/run", run_body(), headers={"idempotency-key": "phase5a-idempotency-0002"}), CONTEXT)
    run_id = parsed(response)["run_id"]
    assert api.handler(event("GET", f"/v1/runs/{run_id}"), CONTEXT)["statusCode"] == 200
    assert api.handler(event("GET", f"/v1/runs/{run_id}/result"), CONTEXT)["statusCode"] == 202
    assert api.handler(event("GET", f"/v1/runs/{run_id}", tenant="tenant-b"), CONTEXT)["statusCode"] == 404
    assert api.handler(event("GET", f"/v1/runs/{run_id}/result", tenant="tenant-b"), CONTEXT)["statusCode"] == 404


def test_arbitrary_bundle_path_is_rejected(services):
    create(services)
    body = run_body()
    body["model_bundle_reference"]["path"] = "s3://attacker/bundle.xlsx"
    response = api.handler(event("POST", "/v1/assessments/IT-CRQ-001/run", body, headers={"idempotency-key": "phase5a-idempotency-0003"}), CONTEXT)
    assert response["statusCode"] in {400, 422}
