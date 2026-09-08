"""SQS worker that delegates all quantitative work to execute_assessment()."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import logging
import os
import time
from typing import Any, Mapping

from crq.application.serialization import dumps, loads
from crq.application.service import execute_assessment
from crq.product.contracts import ProductJob, run_key
from crq.product.records import utc_now
from crq.product.storage import ObjectConflict, ObjectNotFound, ObjectStore, S3ObjectStore, StoredObject


MAX_ATTEMPTS = 3
LEASE_MINUTES = 16
_LOGGER = logging.getLogger("crq.product.worker")
_LOGGER.setLevel(logging.INFO)
_STORE: ObjectStore | None = None


def handler(event: Mapping[str, Any], context: Any) -> dict[str, Any]:
    failures = []
    for record in event.get("Records") or []:
        message_id = str(record.get("messageId") or "unknown")
        try:
            job = ProductJob.from_dict(loads(record.get("body", "")))
            processed = _process(job, _store())
            _safe_log(job, "PROCESSED" if processed else "SKIPPED", None)
        except Exception:
            job = _job_if_safe(record)
            if job is not None:
                _mark_failed(job, _store(), "WORKER_EXECUTION_FAILED", "The governed run could not be completed.")
                _safe_log(job, "FAILED", "WORKER_EXECUTION_FAILED")
            failures.append({"itemIdentifier": message_id})
    return {"batchItemFailures": failures}


def _process(job: ProductJob, store: ObjectStore) -> bool:
    status_key = run_key(job.tenant_id, job.run_id, "status.json")
    result_key = run_key(job.tenant_id, job.run_id, "result.json")
    status_object = store.get(status_key)
    status = status_object.value
    _assert_job_matches(status, job)
    if status.get("status") == "COMPLETED":
        return False
    try:
        existing_result = store.get(result_key).value
    except ObjectNotFound:
        existing_result = None
    if existing_result is not None:
        _complete_from_existing(store, status_key, status_object, existing_result)
        return False
    if status.get("status") == "RUNNING" and not _lease_expired(status.get("lease_expires_at")):
        return False
    if int(status.get("attempt") or 0) >= MAX_ATTEMPTS:
        raise RuntimeError("governed retry limit reached")
    claimed = dict(status)
    now = utc_now()
    claimed.update({
        "status": "RUNNING",
        "updated_at": now,
        "started_at": status.get("started_at") or now,
        "attempt": int(status.get("attempt") or 0) + 1,
        "lease_expires_at": (datetime.now(timezone.utc) + timedelta(minutes=LEASE_MINUTES)).isoformat(),
        "error_code": None,
        "error_message": None,
        "retryable": None,
    })
    try:
        claimed_etag = store.put(status_key, claimed, if_match=status_object.etag)
    except ObjectConflict:
        return False
    request_record = store.get(run_key(job.tenant_id, job.run_id, "request.json")).value
    _assert_job_matches(request_record, job)
    started = time.perf_counter()
    response = execute_assessment(request_record["request"])
    duration_ms = (time.perf_counter() - started) * 1000.0
    if response.status != "SUCCESS" or response.result is None:
        error = response.error or {}
        _write_failure(store, status_key, claimed, claimed_etag, str(error.get("code") or "EXECUTION_FAILED"), str(error.get("message") or "The assessment could not be executed."), False)
        _safe_log(job, "FAILED", str(error.get("code") or "EXECUTION_FAILED"), duration_ms)
        return True
    result = response.result
    result_hash = (result.get("provenance") or {}).get("result_hash")
    result_record = {**{key: claimed.get(key) for key in _metadata_keys()}, "updated_at": utc_now(), "result_hash": result_hash, "status": "COMPLETED", "result": result}
    try:
        store.put(result_key, result_record, if_none_match=True)
    except ObjectConflict:
        result_record = store.get(result_key).value
        result_hash = result_record.get("result_hash")
    complete = dict(claimed)
    complete.update({"status": "COMPLETED", "updated_at": utc_now(), "completed_at": utc_now(), "result_available": True, "result_hash": result_hash, "lease_expires_at": None, "error_code": None, "error_message": None, "retryable": None})
    try:
        store.put(status_key, complete, if_match=claimed_etag)
    except ObjectConflict:
        if store.get(status_key).value.get("status") != "COMPLETED":
            raise
    _safe_log(job, "COMPLETED", None, duration_ms)
    return True


def _complete_from_existing(store: ObjectStore, key: str, status_object: StoredObject, result: Mapping[str, Any]) -> None:
    status = dict(status_object.value)
    status.update({"status": "COMPLETED", "updated_at": utc_now(), "completed_at": status.get("completed_at") or utc_now(), "result_available": True, "result_hash": result.get("result_hash"), "lease_expires_at": None})
    try:
        store.put(key, status, if_match=status_object.etag)
    except ObjectConflict:
        pass


def _mark_failed(job: ProductJob, store: ObjectStore, code: str, message: str) -> None:
    try:
        stored = store.get(run_key(job.tenant_id, job.run_id, "status.json"))
        if stored.value.get("status") == "COMPLETED":
            return
        _write_failure(store, run_key(job.tenant_id, job.run_id, "status.json"), stored.value, stored.etag, code, message, True)
    except (ObjectNotFound, ObjectConflict):
        return


def _write_failure(store: ObjectStore, key: str, status: Mapping[str, Any], etag: str, code: str, message: str, retryable: bool) -> None:
    failed = dict(status)
    failed.update({"status": "FAILED", "updated_at": utc_now(), "completed_at": utc_now(), "result_available": False, "lease_expires_at": None, "error_code": code, "error_message": message, "retryable": retryable})
    store.put(key, failed, if_match=etag)


def _assert_job_matches(value: Mapping[str, Any], job: ProductJob) -> None:
    expected = {"tenant_id": job.tenant_id, "run_id": job.run_id, "assessment_id": job.assessment_id, "bundle_id": job.bundle_id}
    if any(value.get(key) != item for key, item in expected.items()):
        raise ValueError("job does not match persisted server-owned identifiers")


def _lease_expired(value: Any) -> bool:
    if not isinstance(value, str):
        return True
    try:
        return datetime.fromisoformat(value) <= datetime.now(timezone.utc)
    except ValueError:
        return True


def _job_if_safe(record: Mapping[str, Any]) -> ProductJob | None:
    try:
        return ProductJob.from_dict(loads(record.get("body", "")))
    except Exception:
        return None


def _store() -> ObjectStore:
    global _STORE
    if _STORE is None:
        _STORE = S3ObjectStore(os.environ.get("CRQ_BUCKET", ""))
    return _STORE


def _metadata_keys() -> tuple[str, ...]:
    return ("object_schema_version", "tenant_id", "user_id", "assessment_id", "assessment_version", "run_id", "created_at", "updated_at", "created_by", "domain", "sector", "bundle_id", "engine_version", "methodology_version", "assessment_hash", "result_hash", "status")


def _safe_log(job: ProductJob, status: str, error_code: str | None, duration_ms: float | None = None) -> None:
    _LOGGER.info(dumps({"run_id": job.run_id, "assessment_id": job.assessment_id, "tenant_id": job.tenant_id, "bundle_id": job.bundle_id, "status": status, "error_code": error_code, "duration_ms": duration_ms}))
