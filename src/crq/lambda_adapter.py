"""Minimal API Gateway HTTP API v2 adapter for the Phase 3A service.

This hosting adapter contains no quantitative methodology.
"""

from __future__ import annotations

import base64
import binascii
import logging
import re
import time
import uuid
from typing import Any, Mapping

from crq.application.errors import ErrorCode
from crq.application.serialization import dumps
from crq.application.service import AssessmentRunResponse, execute_assessment
from crq.versions import PLATFORM_VERSION
from it_ot_crq.router import IT_ENGINE_VERSION, OT_ENGINE_VERSION


MAX_REQUEST_BODY_BYTES = 1_048_576
_SAFE_ID = re.compile(r"^[A-Za-z0-9_.:-]{1,128}$")
_CONTENT_HEADERS = {"content-type": "application/json", "cache-control": "no-store"}
_ERROR_STATUS = {
    ErrorCode.INVALID_REQUEST.value: 400,
    ErrorCode.INVALID_ASSESSMENT.value: 422,
    ErrorCode.UNSUPPORTED_DOMAIN.value: 422,
    ErrorCode.UNSUPPORTED_SECTOR.value: 422,
    ErrorCode.MODEL_BUNDLE_NOT_FOUND.value: 404,
    ErrorCode.MODEL_BUNDLE_INCOMPATIBLE.value: 422,
    ErrorCode.SCHEMA_VERSION_UNSUPPORTED.value: 422,
    ErrorCode.VALIDATION_FAILED.value: 422,
    ErrorCode.EXECUTION_FAILED.value: 500,
    ErrorCode.RESULT_VALIDATION_FAILED.value: 500,
}
_LOGGER = logging.getLogger("crq.lambda")
_LOGGER.setLevel(logging.INFO)


def handler(event: Mapping[str, Any], context: Any) -> dict[str, Any]:
    """Handle only GET /health and POST /v1/assessments/run."""
    started = time.perf_counter()
    correlation_id = _correlation_id(event, context)
    method, path = _method_path(event)
    if path == "/health":
        if method != "GET":
            return _boundary_error(405, ErrorCode.INVALID_REQUEST, "Method not allowed.", correlation_id, started)
        payload = {
            "status": "ok",
            "platform_version": PLATFORM_VERSION,
            "engine_versions": {"it": IT_ENGINE_VERSION, "ot": OT_ENGINE_VERSION},
        }
        response = _http_response(200, payload)
        _log(correlation_id, None, None, "HEALTHY", started, None)
        return response
    if path != "/v1/assessments/run":
        return _boundary_error(404, ErrorCode.INVALID_REQUEST, "Route not found.", correlation_id, started)
    if method != "POST":
        return _boundary_error(405, ErrorCode.INVALID_REQUEST, "Method not allowed.", correlation_id, started)

    headers = {str(key).lower(): str(value) for key, value in (event.get("headers") or {}).items()}
    content_type = headers.get("content-type", "").split(";", 1)[0].strip().lower()
    if content_type != "application/json":
        return _boundary_error(415, ErrorCode.INVALID_REQUEST, "Content-Type must be application/json.", correlation_id, started)
    try:
        body = _body_bytes(event)
    except ValueError:
        return _boundary_error(400, ErrorCode.INVALID_REQUEST, "The request body encoding is invalid.", correlation_id, started)
    if not body:
        return _boundary_error(400, ErrorCode.INVALID_REQUEST, "A JSON request body is required.", correlation_id, started)
    if len(body) > MAX_REQUEST_BODY_BYTES:
        return _boundary_error(413, ErrorCode.INVALID_REQUEST, "The request body exceeds the permitted size.", correlation_id, started)

    try:
        application_response = execute_assessment(body)
    except Exception:
        application_response = _error_envelope(ErrorCode.EXECUTION_FAILED, "The assessment could not be executed.")
    status_code = 200 if application_response.status == "SUCCESS" else _ERROR_STATUS.get(application_response.error["code"], 500)
    payload = application_response.to_dict()
    response = _http_response(status_code, payload)
    result = application_response.result or {}
    provenance = result.get("provenance") or {}
    domain = (result.get("compatibility") or {}).get("native_domain")
    engine_ms = (application_response.validation.get("timing_ms") or {}).get("engine_execution_ms")
    _log(correlation_id, domain, provenance.get("sector_pack_id"), application_response.status, started, engine_ms)
    return response


def _method_path(event: Mapping[str, Any]) -> tuple[str, str]:
    request_context = event.get("requestContext") or {}
    http = request_context.get("http") or {}
    method = str(http.get("method") or event.get("httpMethod") or "").upper()
    path = str(event.get("rawPath") or event.get("path") or "")
    return method, path


def _body_bytes(event: Mapping[str, Any]) -> bytes:
    body = event.get("body")
    if body is None:
        return b""
    if not isinstance(body, (str, bytes)):
        raise ValueError("body must be text")
    raw = body.encode("utf-8") if isinstance(body, str) else body
    if event.get("isBase64Encoded"):
        try:
            return base64.b64decode(raw, validate=True)
        except (ValueError, binascii.Error) as exc:
            raise ValueError("invalid base64 body") from exc
    return raw


def _correlation_id(event: Mapping[str, Any], context: Any) -> str:
    candidates = [
        getattr(context, "aws_request_id", None),
        (event.get("requestContext") or {}).get("requestId"),
    ]
    for value in candidates:
        if isinstance(value, str) and _SAFE_ID.fullmatch(value):
            return value
    return str(uuid.uuid4())


def _error_envelope(code: ErrorCode, message: str) -> AssessmentRunResponse:
    return AssessmentRunResponse(
        request_id=None,
        status="ERROR",
        result=None,
        warnings=(),
        validation={"stages": {}, "timing_ms": {}},
        error={"code": code.value, "message": message, "details": {}},
    )


def _boundary_error(
    status_code: int,
    code: ErrorCode,
    message: str,
    correlation_id: str,
    started: float,
) -> dict[str, Any]:
    response = _error_envelope(code, message)
    _log(correlation_id, None, None, "ERROR", started, None)
    return _http_response(status_code, response.to_dict())


def _http_response(status_code: int, value: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": dict(_CONTENT_HEADERS),
        "isBase64Encoded": False,
        "body": dumps(value),
    }


def _log(
    request_id: str,
    domain: str | None,
    bundle_id: str | None,
    status: str,
    started: float,
    engine_duration_ms: float | None,
) -> None:
    _LOGGER.info(dumps({
        "request_id": request_id,
        "domain": domain,
        "bundle_id": bundle_id,
        "status": status,
        "duration_ms": (time.perf_counter() - started) * 1000.0,
        "engine_duration_ms": engine_duration_ms,
    }))
