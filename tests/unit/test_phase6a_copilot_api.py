from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import crq.product.api_lambda as api
from crq.product.contracts import run_key
from crq.product.storage import MemoryJobQueue, MemoryObjectStore


ROOT = Path(__file__).resolve().parents[2]
REQUEST = json.loads((ROOT / "contracts/examples/assessment-run-request-it-fs.json").read_text())
RESULT = json.loads((ROOT / "contracts/examples/assessment-run-response-it-fs.json").read_text())["result"]
CONTEXT = SimpleNamespace(aws_request_id="phase6a-api-test")


def event(method, path, body=None, *, tenant="tenant-a", user="user-a", authenticated=True):
    claims = {"sub": user, "custom:tenant_id": tenant} if authenticated else {}
    return {"version": "2.0", "rawPath": path, "headers": {"content-type": "application/json"}, "requestContext": {"requestId": "gateway-test", "http": {"method": method, "path": path}, "authorizer": {"jwt": {"claims": claims}}}, "isBase64Encoded": False, "body": None if body is None else json.dumps(body)}


def parsed(response):
    return json.loads(response["body"])


class StubCopilot:
    def __init__(self):
        self.calls = []

    def query(self, **kwargs):
        self.calls.append(kwargs)
        return {"status": "VERIFIED", "answer": "Verified against supplied facts.", "supporting_fact_ids": ["vf_stub"]}


@pytest.fixture
def services(monkeypatch):
    store, queue, copilot = MemoryObjectStore(), MemoryJobQueue(), StubCopilot()
    monkeypatch.setattr(api, "_STORE", store)
    monkeypatch.setattr(api, "_QUEUE", queue)
    monkeypatch.setattr(api, "_COPILOT", copilot)
    created = api.handler(event("POST", "/v1/assessments", REQUEST["assessment"]), CONTEXT)
    assert created["statusCode"] == 201
    return store, copilot


def add_result(store, *, tenant="tenant-a", run_id="run-phase6a"):
    common = {"tenant_id": tenant, "user_id": "user-a", "assessment_id": "IT-CRQ-001", "assessment_version": 1, "run_id": run_id, "result_hash": "result-hash-1"}
    store.put(run_key(tenant, run_id, "result.json"), {**common, "result": RESULT})
    store.put(run_key(tenant, run_id, "request.json"), {**common, "request": REQUEST})


def test_copilot_requires_authentication_and_rejects_client_facts(services):
    body = {"assessment_id": "IT-CRQ-001", "current_view": "assessment.organization", "question": "Explain this"}
    assert api.handler(event("POST", "/v1/copilot/query", body, authenticated=False), CONTEXT)["statusCode"] == 401
    assert api.handler(event("POST", "/v1/copilot/query", {**body, "facts": [{"value": 999}]}), CONTEXT)["statusCode"] == 400


def test_assessment_copilot_builds_context_server_side(services):
    _, copilot = services
    response = api.handler(event("POST", "/v1/copilot/query", {"assessment_id": "IT-CRQ-001", "current_view": "assessment.architecture", "question": "What does Unknown mean?"}), CONTEXT)
    assert response["statusCode"] == 200
    assert parsed(response)["status"] == "VERIFIED"
    assert copilot.calls[0]["result"] is None
    assert copilot.calls[0]["current_view"] == "assessment.architecture"


def test_selected_entity_accepts_governed_user_facing_labels(services):
    _, copilot = services
    body = {"assessment_id": "IT-CRQ-001", "current_view": "assessment.architecture", "selected_entity": {"entity_type": "route", "entity_id": "Identity and credential compromise"}, "question": "Why are we asking this?"}
    response = api.handler(event("POST", "/v1/copilot/query", body), CONTEXT)
    assert response["statusCode"] == 200
    assert copilot.calls[-1]["selected_entity"]["entity_id"] == "Identity and credential compromise"


def test_result_copilot_enforces_tenant_and_loads_result_by_reference(services):
    store, copilot = services
    add_result(store)
    body = {"780": "not accepted", "assessment_id": "IT-CRQ-001", "run_id": "run-phase6a", "current_view": "results.overview", "question": "Explain headline metrics"}
    assert api.handler(event("POST", "/v1/copilot/query", body), CONTEXT)["statusCode"] == 400
    body.pop("780")
    assert api.handler(event("POST", "/v1/copilot/query", body, tenant="tenant-b", user="user-b"), CONTEXT)["statusCode"] == 404
    response = api.handler(event("POST", "/v1/copilot/query", body), CONTEXT)
    assert response["statusCode"] == 200
    assert copilot.calls[-1]["result"]["summary"]["prudent"]["aal"] == RESULT["summary"]["prudent"]["aal"]


def test_verified_executive_narrative_is_bound_to_result_hash_and_persisted(services):
    store, copilot = services
    add_result(store)
    created = api.handler(event("POST", "/v1/runs/run-phase6a/narrative"), CONTEXT)
    fetched = api.handler(event("GET", "/v1/runs/run-phase6a/narrative"), CONTEXT)
    assert created["statusCode"] == 201
    assert fetched["statusCode"] == 200
    assert copilot.calls[-1]["current_view"] == "results.executive"
    persisted = store.get(run_key("tenant-a", "run-phase6a", "narrative.json")).value
    assert persisted["result_hash"] == "result-hash-1"
    assert "question" not in persisted
