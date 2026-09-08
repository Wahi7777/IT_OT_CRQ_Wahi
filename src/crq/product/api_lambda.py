"""Authenticated Phase 5A API Lambda over S3 and SQS.

This adapter validates, authorizes and persists. It never invokes an engine or
calculates a quantitative metric.
"""

from __future__ import annotations

import base64
import binascii
import json
import logging
import os
import re
import time
import uuid
from dataclasses import dataclass
from typing import Any, Mapping

from crq.application.bundle_resolver import resolve_approved_bundle
from crq.application.errors import ApplicationError
from crq.application.request_adapter import assessment_from_public_payload, public_assessment_payload
from crq.application.serialization import dumps, loads
from crq.application.service import AssessmentRunRequest
from crq.product.contracts import ProductJob, assessment_key, run_key, safe_identifier
from crq.product.records import metadata_record, utc_now
from crq.product.storage import JobQueue, ObjectConflict, ObjectNotFound, ObjectStore, S3ObjectStore, SQSJobQueue
from crq.versions import METHODOLOGY_VERSION, PLATFORM_VERSION
from it_ot_crq.router import IT_ENGINE_VERSION, OT_ENGINE_VERSION


MAX_REQUEST_BODY_BYTES = 1_048_576
_ASSESSMENT_ROUTE = re.compile(r"^/v1/assessments/([^/]+)$")
_RUN_SUBMIT_ROUTE = re.compile(r"^/v1/assessments/([^/]+)/run$")
_RUN_ROUTE = re.compile(r"^/v1/runs/([^/]+)$")
_RESULT_ROUTE = re.compile(r"^/v1/runs/([^/]+)/result$")
_CONTENT_HEADERS = {"content-type": "application/json", "cache-control": "no-store"}
_LOGGER = logging.getLogger("crq.product.api")
_LOGGER.setLevel(logging.INFO)
_STORE: ObjectStore | None = None
_QUEUE: JobQueue | None = None


@dataclass(frozen=True)
class Principal:
    tenant_id: str
    user_id: str


def handler(event: Mapping[str, Any], context: Any) -> dict[str, Any]:
    started = time.perf_counter()
    request_id = _request_id(event, context)
    method, path = _method_path(event)
    if method == "GET" and path == "/health":
        return _respond(200, {"status": "ok", "platform_version": PLATFORM_VERSION, "engine_versions": {"it": IT_ENGINE_VERSION, "ot": OT_ENGINE_VERSION}})
    try:
        principal = _principal(event)
        store, queue = _services()
        if method == "POST" and path == "/v1/assessments":
            response = _create_assessment(event, principal, store)
        elif method == "GET" and (match := _ASSESSMENT_ROUTE.fullmatch(path)):
            response = _get_assessment(match.group(1), principal, store)
        elif method == "POST" and (match := _RUN_SUBMIT_ROUTE.fullmatch(path)):
            response = _submit_run(match.group(1), event, principal, store, queue)
        elif method == "GET" and (match := _RESULT_ROUTE.fullmatch(path)):
            response = _get_result(match.group(1), principal, store)
        elif method == "GET" and (match := _RUN_ROUTE.fullmatch(path)):
            response = _get_run(match.group(1), principal, store)
        else:
            response = _problem(404, "NOT_FOUND", "Route not found.", request_id)
        _safe_log(request_id=request_id, principal=principal, status=response["statusCode"], started=started)
        return response
    except PermissionError:
        response = _problem(401, "UNAUTHORIZED", "Authentication is required.", request_id)
    except ObjectNotFound:
        response = _problem(404, "NOT_FOUND", "The requested resource was not found.", request_id)
    except ApplicationError as exc:
        status = 404 if exc.code.value == "MODEL_BUNDLE_NOT_FOUND" else 422
        response = _problem(status, exc.code.value, exc.message, request_id)
    except (ValueError, TypeError, KeyError, json.JSONDecodeError):
        response = _problem(400, "INVALID_REQUEST", "The request is invalid.", request_id)
    except Exception:
        _LOGGER.error(dumps({"request_id": request_id, "status": "INTERNAL_ERROR"}))
        response = _problem(500, "INTERNAL_ERROR", "The request could not be completed.", request_id)
    _safe_log(request_id=request_id, principal=None, status=response["statusCode"], started=started)
    return response


def _create_assessment(event: Mapping[str, Any], principal: Principal, store: ObjectStore) -> dict[str, Any]:
    body = _json_body(event)
    canonical = assessment_from_public_payload(body)
    canonical_data = canonical.to_dict()
    public = public_assessment_payload(canonical)
    identity = canonical_data["assessment"]
    assessment_id = safe_identifier(identity["assessment_id"], "assessment_id")
    now = utc_now()
    metadata = metadata_record(
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        assessment_id=assessment_id,
        assessment_version=identity["assessment_version"],
        created_at=now,
        domain=identity["domain"],
        sector=identity["sector"],
        bundle_id=None,
        engine_version=None,
        methodology_version=METHODOLOGY_VERSION,
        assessment_hash=canonical_data["assessment_hash"],
        status="DRAFT",
    )
    input_record = {**metadata, "assessment": public}
    input_key = assessment_key(principal.tenant_id, assessment_id, "input.json")
    metadata_key = assessment_key(principal.tenant_id, assessment_id, "metadata.json")
    try:
        store.put(input_key, input_record, if_none_match=True)
        store.put(metadata_key, metadata, if_none_match=True)
        status = 201
    except ObjectConflict:
        existing = store.get(input_key).value
        if existing.get("assessment_hash") != metadata["assessment_hash"] or existing.get("assessment_version") != metadata["assessment_version"]:
            return _problem(409, "ASSESSMENT_VERSION_CONFLICT", "Increment assessment_version before replacing an existing assessment.", None)
        status = 200
        metadata = {key: existing.get(key) for key in metadata}
    return _respond(status, {"metadata": metadata, "assessment": public})


def _get_assessment(assessment_id: str, principal: Principal, store: ObjectStore) -> dict[str, Any]:
    key = assessment_key(principal.tenant_id, assessment_id, "input.json")
    value = store.get(key).value
    _assert_owner(value, principal, assessment_id=assessment_id)
    return _respond(200, {"metadata": _metadata_projection(value), "assessment": value["assessment"]})


def _submit_run(assessment_id: str, event: Mapping[str, Any], principal: Principal, store: ObjectStore, queue: JobQueue) -> dict[str, Any]:
    assessment_id = safe_identifier(assessment_id, "assessment_id")
    headers = {str(key).lower(): str(value) for key, value in (event.get("headers") or {}).items()}
    idempotency_key = headers.get("idempotency-key", "")
    if not 16 <= len(idempotency_key) <= 128 or any(ord(char) < 33 or ord(char) > 126 for char in idempotency_key):
        raise ValueError("invalid idempotency key")
    stored = store.get(assessment_key(principal.tenant_id, assessment_id, "input.json")).value
    _assert_owner(stored, principal, assessment_id=assessment_id)
    body = _json_body(event)
    if not isinstance(body, dict) or set(body) != {"schema_version", "request_id", "model_bundle_reference", "run_config"}:
        raise ValueError("invalid run submission")
    request = AssessmentRunRequest.from_dict({**body, "assessment": stored["assessment"]})
    identity = stored["assessment"]["assessment"]
    bundle = resolve_approved_bundle(
        request.model_bundle_reference.bundle_id,
        request.model_bundle_reference.bundle_version,
        identity["domain"],
        identity["sector"],
        identity["asset_type"],
    ).to_dict()
    run_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"crq:{principal.tenant_id}:{assessment_id}:{idempotency_key}"))
    now = utc_now()
    metadata = metadata_record(
        tenant_id=principal.tenant_id,
        user_id=principal.user_id,
        assessment_id=assessment_id,
        assessment_version=stored["assessment_version"],
        created_at=now,
        domain=identity["domain"],
        sector=identity["sector"],
        bundle_id=request.model_bundle_reference.bundle_id,
        engine_version=bundle["engine_version"],
        methodology_version=bundle["methodology_version"],
        assessment_hash=stored["assessment_hash"],
        run_id=run_id,
        status="QUEUED",
    )
    request_record = {**metadata, "request": request.to_dict()}
    status_record = {**metadata, "submitted_at": now, "started_at": None, "completed_at": None, "result_available": False, "error_code": None, "error_message": None, "retryable": None, "attempt": 0, "lease_expires_at": None, "enqueued_at": None}
    request_key = run_key(principal.tenant_id, run_id, "request.json")
    status_key = run_key(principal.tenant_id, run_id, "status.json")
    try:
        store.put(request_key, request_record, if_none_match=True)
        status_etag = store.put(status_key, status_record, if_none_match=True)
    except ObjectConflict:
        stored_status = store.get(status_key)
        existing = stored_status.value
        _assert_owner(existing, principal, run_id=run_id)
        if existing.get("status") == "QUEUED" and not existing.get("enqueued_at"):
            job = ProductJob(run_id=run_id, assessment_id=assessment_id, tenant_id=principal.tenant_id, bundle_id=request.model_bundle_reference.bundle_id, run_config=dict(request.run_config))
            queue.send(job.to_dict())
            existing = _record_enqueued(store, status_key, stored_status.etag, existing)
        return _respond(202, _public_status(existing))
    job = ProductJob(run_id=run_id, assessment_id=assessment_id, tenant_id=principal.tenant_id, bundle_id=request.model_bundle_reference.bundle_id, run_config=dict(request.run_config))
    queue.send(job.to_dict())
    status_record = _record_enqueued(store, status_key, status_etag, status_record)
    return _respond(202, _public_status(status_record))


def _record_enqueued(store: ObjectStore, key: str, etag: str, status: Mapping[str, Any]) -> dict[str, Any]:
    updated = dict(status)
    updated["enqueued_at"] = utc_now()
    updated["updated_at"] = updated["enqueued_at"]
    try:
        store.put(key, updated, if_match=etag)
        return updated
    except ObjectConflict:
        return store.get(key).value


def _get_run(run_id: str, principal: Principal, store: ObjectStore) -> dict[str, Any]:
    value = store.get(run_key(principal.tenant_id, run_id, "status.json")).value
    _assert_owner(value, principal, run_id=run_id)
    return _respond(200, _public_status(value))


def _get_result(run_id: str, principal: Principal, store: ObjectStore) -> dict[str, Any]:
    status = store.get(run_key(principal.tenant_id, run_id, "status.json")).value
    _assert_owner(status, principal, run_id=run_id)
    if status["status"] == "FAILED":
        return _problem(409, status.get("error_code") or "RUN_FAILED", "The run failed and has no result.", None)
    if status["status"] != "COMPLETED":
        return _respond(202, _public_status(status))
    result_record = store.get(run_key(principal.tenant_id, run_id, "result.json")).value
    _assert_owner(result_record, principal, run_id=run_id)
    return _respond(200, result_record["result"])


def _principal(event: Mapping[str, Any]) -> Principal:
    claims = (((event.get("requestContext") or {}).get("authorizer") or {}).get("jwt") or {}).get("claims") or {}
    user_id = claims.get("sub")
    if not isinstance(user_id, str) or not user_id:
        raise PermissionError("missing verified subject")
    tenant = claims.get("custom:tenant_id") or os.environ.get("CRQ_DEFAULT_TENANT_ID")
    return Principal(safe_identifier(tenant, "tenant_id"), safe_identifier(user_id, "user_id"))


def _services() -> tuple[ObjectStore, JobQueue]:
    global _STORE, _QUEUE
    if _STORE is None:
        _STORE = S3ObjectStore(os.environ.get("CRQ_BUCKET", ""))
    if _QUEUE is None:
        _QUEUE = SQSJobQueue(os.environ.get("CRQ_QUEUE_URL", ""))
    return _STORE, _QUEUE


def _json_body(event: Mapping[str, Any]) -> dict[str, Any]:
    headers = {str(key).lower(): str(value) for key, value in (event.get("headers") or {}).items()}
    if headers.get("content-type", "").split(";", 1)[0].lower() != "application/json":
        raise ValueError("content type")
    body = event.get("body")
    if not isinstance(body, (str, bytes)):
        raise ValueError("body")
    raw = body.encode() if isinstance(body, str) else body
    if event.get("isBase64Encoded"):
        try:
            raw = base64.b64decode(raw, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ValueError("body encoding") from exc
    if not raw or len(raw) > MAX_REQUEST_BODY_BYTES:
        raise ValueError("body size")
    value = loads(raw)
    if not isinstance(value, dict):
        raise ValueError("body object")
    return value


def _assert_owner(value: Mapping[str, Any], principal: Principal, **identifiers: str) -> None:
    if value.get("tenant_id") != principal.tenant_id:
        raise ObjectNotFound("resource")
    for name, expected in identifiers.items():
        if value.get(name) != expected:
            raise ObjectNotFound("resource")


def _metadata_projection(value: Mapping[str, Any]) -> dict[str, Any]:
    keys = ("tenant_id", "user_id", "assessment_id", "assessment_version", "run_id", "created_at", "updated_at", "created_by", "domain", "sector", "bundle_id", "engine_version", "methodology_version", "assessment_hash", "result_hash", "status")
    return {key: value.get(key) for key in keys}


def _public_status(value: Mapping[str, Any]) -> dict[str, Any]:
    payload = {key: value.get(key) for key in ("run_id", "assessment_id", "status", "submitted_at", "started_at", "completed_at", "domain", "bundle_id", "engine_version", "methodology_version", "result_available", "error_code")}
    payload["schema_version"] = "1.0.0-draft"
    payload["links"] = {"status": f"/v1/runs/{value.get('run_id')}", "result": f"/v1/runs/{value.get('run_id')}/result"}
    return payload


def _method_path(event: Mapping[str, Any]) -> tuple[str, str]:
    http = (event.get("requestContext") or {}).get("http") or {}
    return str(http.get("method") or event.get("httpMethod") or "").upper(), str(event.get("rawPath") or event.get("path") or "")


def _request_id(event: Mapping[str, Any], context: Any) -> str:
    value = getattr(context, "aws_request_id", None) or (event.get("requestContext") or {}).get("requestId")
    try:
        return safe_identifier(value, "request_id")
    except ValueError:
        return str(uuid.uuid4())


def _respond(status: int, value: Mapping[str, Any]) -> dict[str, Any]:
    return {"statusCode": status, "headers": dict(_CONTENT_HEADERS), "isBase64Encoded": False, "body": dumps(value)}


def _problem(status: int, code: str, message: str, request_id: str | None) -> dict[str, Any]:
    return _respond(status, {"code": code, "message": message, "request_id": request_id})


def _safe_log(*, request_id: str, principal: Principal | None, status: int, started: float) -> None:
    _LOGGER.info(dumps({"request_id": request_id, "tenant_id": principal.tenant_id if principal else None, "status": status, "duration_ms": (time.perf_counter() - started) * 1000.0}))
