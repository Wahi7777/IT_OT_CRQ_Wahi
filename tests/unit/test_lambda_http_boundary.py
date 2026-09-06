from __future__ import annotations

import copy
import json
from pathlib import Path
from types import SimpleNamespace

import crq.lambda_adapter as adapter
from crq.application.errors import ErrorCode
from crq.application.service import validate_response_payload
from crq.lambda_adapter import MAX_REQUEST_BODY_BYTES, handler


ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = json.loads((ROOT / "contracts/examples/assessment-run-request-it-fs.json").read_text())
CONTEXT = SimpleNamespace(aws_request_id="lambda-test-request")


def event(method="POST", path="/v1/assessments/run", body=None, content_type="application/json"):
    return {
        "version": "2.0",
        "rawPath": path,
        "headers": {"content-type": content_type},
        "requestContext": {"requestId": "gateway-test-request", "http": {"method": method, "path": path}},
        "isBase64Encoded": False,
        "body": body,
    }


def parsed(response):
    assert response["headers"]["content-type"] == "application/json"
    assert response["isBase64Encoded"] is False
    return json.loads(response["body"])


def assert_error(response, status, code):
    assert response["statusCode"] == status
    payload = parsed(response)
    validate_response_payload(payload)
    assert payload["status"] == "ERROR"
    assert payload["error"]["code"] == code.value
    assert "Traceback" not in response["body"]
    assert "/Users/" not in response["body"]


def test_health_is_lightweight(monkeypatch):
    def must_not_execute(_request):
        raise AssertionError("health must not execute assessment service")

    monkeypatch.setattr(adapter, "execute_assessment", must_not_execute)
    response = handler(event(method="GET", path="/health"), CONTEXT)
    assert response["statusCode"] == 200
    assert parsed(response) == {
        "status": "ok",
        "platform_version": "1.2.0",
        "engine_versions": {"it": "1.1.1", "ot": "1.7.1"},
    }


def test_malformed_json():
    assert_error(handler(event(body="{"), CONTEXT), 400, ErrorCode.INVALID_REQUEST)


def test_missing_body():
    assert_error(handler(event(body=None), CONTEXT), 400, ErrorCode.INVALID_REQUEST)


def test_oversized_payload():
    assert_error(handler(event(body="x" * (MAX_REQUEST_BODY_BYTES + 1)), CONTEXT), 413, ErrorCode.INVALID_REQUEST)


def test_non_json_content_type():
    assert_error(handler(event(body="{}", content_type="text/plain"), CONTEXT), 415, ErrorCode.INVALID_REQUEST)


def test_unsupported_method():
    assert_error(handler(event(method="PUT", body="{}"), CONTEXT), 405, ErrorCode.INVALID_REQUEST)


def test_unsupported_route():
    assert_error(handler(event(method="GET", path="/v1/models"), CONTEXT), 404, ErrorCode.INVALID_REQUEST)


def test_invalid_assessment():
    request = copy.deepcopy(EXAMPLE)
    request["assessment"]["assessment"]["domain"] = "Cloud"
    assert_error(handler(event(body=json.dumps(request)), CONTEXT), 422, ErrorCode.UNSUPPORTED_DOMAIN)


def test_missing_bundle_reference():
    request = copy.deepcopy(EXAMPLE)
    request.pop("model_bundle_reference")
    assert_error(handler(event(body=json.dumps(request)), CONTEXT), 400, ErrorCode.INVALID_REQUEST)


def test_unknown_bundle():
    request = copy.deepcopy(EXAMPLE)
    request["model_bundle_reference"]["bundle_id"] = "FS-v999"
    assert_error(handler(event(body=json.dumps(request)), CONTEXT), 404, ErrorCode.MODEL_BUNDLE_NOT_FOUND)


def test_incompatible_bundle():
    request = copy.deepcopy(EXAMPLE)
    request["model_bundle_reference"]["bundle_id"] = "PG-v1.6"
    assert_error(handler(event(body=json.dumps(request)), CONTEXT), 422, ErrorCode.MODEL_BUNDLE_INCOMPATIBLE)


def test_internal_failure_is_safe(monkeypatch):
    def fail(_request):
        raise RuntimeError("secret /Users/example/internal.py")

    monkeypatch.setattr(adapter, "execute_assessment", fail)
    response = handler(event(body=json.dumps(EXAMPLE)), CONTEXT)
    assert_error(response, 500, ErrorCode.EXECUTION_FAILED)
    assert "secret" not in response["body"]


def test_structured_log_excludes_assessment_values(caplog):
    with caplog.at_level("INFO", logger="crq.lambda"):
        handler(event(method="GET", path="/health"), CONTEXT)
    record = json.loads(caplog.records[-1].message)
    assert set(record) == {"request_id", "domain", "bundle_id", "status", "duration_ms", "engine_duration_ms"}
    assert record["request_id"] == "lambda-test-request"
