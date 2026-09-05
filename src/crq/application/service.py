"""Framework-neutral orchestration service over the Phase 2 CRQ facade.

This module validates and coordinates a run. It intentionally contains no
frequency, probability, severity, loss, dependency, path, control, appetite,
insurance, VaR, TVaR, or other quantitative methodology.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from typing import Any, Mapping

from crq.application.bundle_resolver import resolve_approved_bundle
from crq.application.errors import ApplicationError, ErrorCode, public_error
from crq.application.facade import run_it_assessment, run_ot_assessment
from crq.application.models import CRQResult, RunConfig, json_value
from crq.application.request_adapter import assessment_from_public_payload
from crq.application.serialization import assert_finite_json, dumps, loads
from crq.versions import (
    APPLICATION_REQUEST_SCHEMA_VERSION,
    APPLICATION_RESPONSE_SCHEMA_VERSION,
    INPUT_SCHEMA_VERSION,
    OUTPUT_SCHEMA_VERSION,
)


_REQUEST_FIELDS = {"schema_version", "request_id", "assessment", "model_bundle_reference", "run_config"}
_BUNDLE_FIELDS = {"bundle_id", "bundle_version"}
_RUN_FIELDS = {"reporting_basis", "simulation_count", "random_seed"}
_RESULT_SECTIONS = {
    "schema_version", "run", "provenance", "summary", "formation", "decomposition", "loss",
    "architecture", "impact", "treatments", "sensitivity", "uncertainty", "insurance",
    "limitations", "compatibility",
}


@dataclass(frozen=True)
class ModelBundleReference:
    bundle_id: str
    bundle_version: str

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ModelBundleReference":
        payload = _mapping(value, "model_bundle_reference")
        _reject_unknown(payload, _BUNDLE_FIELDS, "model_bundle_reference")
        bundle_id = _nonempty_string(payload.get("bundle_id"), "model_bundle_reference.bundle_id")
        bundle_version = _nonempty_string(payload.get("bundle_version"), "model_bundle_reference.bundle_version")
        return cls(bundle_id=bundle_id, bundle_version=bundle_version)

    def to_dict(self) -> dict[str, str]:
        return {"bundle_id": self.bundle_id, "bundle_version": self.bundle_version}


@dataclass(frozen=True)
class AssessmentRunRequest:
    request_id: str
    assessment: dict[str, Any]
    model_bundle_reference: ModelBundleReference
    run_config: dict[str, Any]
    schema_version: str = APPLICATION_REQUEST_SCHEMA_VERSION

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "AssessmentRunRequest":
        try:
            payload = json_value(value)
            assert_finite_json(payload)
        except (TypeError, ValueError) as exc:
            raise public_error(ErrorCode.INVALID_REQUEST, "The request is not finite JSON data.") from exc
        if not isinstance(payload, dict):
            raise public_error(ErrorCode.INVALID_REQUEST, "The request must be a JSON object.")
        _reject_unknown(payload, _REQUEST_FIELDS, "request")
        if payload.get("schema_version") != APPLICATION_REQUEST_SCHEMA_VERSION:
            raise public_error(
                ErrorCode.SCHEMA_VERSION_UNSUPPORTED,
                "The application request schema version is unsupported.",
                supported=APPLICATION_REQUEST_SCHEMA_VERSION,
            )
        request_id = _nonempty_string(payload.get("request_id"), "request_id")
        assessment = _mapping(payload.get("assessment"), "assessment")
        bundle = ModelBundleReference.from_dict(payload.get("model_bundle_reference"))
        run = _mapping(payload.get("run_config"), "run_config")
        _reject_unknown(run, _RUN_FIELDS, "run_config")
        basis = run.get("reporting_basis")
        if basis not in {"Best Estimate", "Prudent", "Both"}:
            raise public_error(ErrorCode.INVALID_REQUEST, "run_config.reporting_basis is invalid.")
        if type(run.get("simulation_count")) is not int or type(run.get("random_seed")) is not int:
            raise public_error(ErrorCode.INVALID_REQUEST, "Run count and seed must be JSON integers.")
        return cls(
            request_id=request_id,
            assessment=assessment,
            model_bundle_reference=bundle,
            run_config=run,
        )

    @classmethod
    def from_json(cls, payload: str | bytes) -> "AssessmentRunRequest":
        try:
            value = loads(payload)
        except (TypeError, ValueError) as exc:
            raise public_error(ErrorCode.INVALID_REQUEST, "The request body is not valid JSON.") from exc
        return cls.from_dict(value)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "request_id": self.request_id,
            "assessment": json_value(self.assessment),
            "model_bundle_reference": self.model_bundle_reference.to_dict(),
            "run_config": json_value(self.run_config),
        }

    def to_json(self) -> str:
        return dumps(self.to_dict())


@dataclass(frozen=True)
class AssessmentRunResponse:
    request_id: str | None
    status: str
    result: dict[str, Any] | None
    warnings: tuple[str, ...]
    validation: dict[str, Any]
    error: dict[str, Any] | None
    schema_version: str = APPLICATION_RESPONSE_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "request_id": self.request_id,
            "status": self.status,
            "result": json_value(self.result),
            "warnings": list(self.warnings),
            "validation": json_value(self.validation),
            "error": json_value(self.error),
        }

    def to_json(self) -> str:
        return dumps(self.to_dict())


def execute_assessment(request: AssessmentRunRequest | Mapping[str, Any] | str | bytes) -> AssessmentRunResponse:
    """Validate and synchronously execute one stateless CRQ assessment request."""
    total_started = time.perf_counter()
    request_id: str | None = None
    timing: dict[str, float] = {}
    stages: dict[str, str] = {}
    try:
        validation_started = time.perf_counter()
        parsed = _coerce_request(request)
        request_id = parsed.request_id
        assessment = assessment_from_public_payload(parsed.assessment)
        assessment_data = assessment.to_dict()
        identity = assessment_data["assessment"]
        _validate_run_config(parsed.run_config, assessment_data)
        config = RunConfig(
            simulation_count=parsed.run_config["simulation_count"],
            random_seed=parsed.run_config["random_seed"],
            run_whatifs=False,
            run_packages=False,
            run_sensitivity=False,
        )
        timing["validation_ms"] = _elapsed_ms(validation_started)
        stages["request"] = "VALID"
        stages["assessment"] = "VALID"

        bundle_started = time.perf_counter()
        bundle = resolve_approved_bundle(
            parsed.model_bundle_reference.bundle_id,
            parsed.model_bundle_reference.bundle_version,
            identity["domain"],
            identity["sector"],
            identity["asset_type"],
        )
        timing["bundle_resolution_ms"] = _elapsed_ms(bundle_started)
        stages["model_bundle"] = "VALID"

        facade_timing: dict[str, float] = {}
        facade = run_it_assessment if identity["domain"] == "IT" else run_ot_assessment
        result = facade(assessment, bundle, config, diagnostics=facade_timing)
        timing.update(facade_timing)
        stages["execution"] = "COMPLETE"

        result_validation_started = time.perf_counter()
        result_data = result.to_dict()
        _validate_result(result, assessment_data, bundle.to_dict(), config)
        timing["result_validation_ms"] = _elapsed_ms(result_validation_started)
        stages["result"] = "VALID"

        serialization_started = time.perf_counter()
        dumps(result_data)
        timing["serialization_ms"] = _elapsed_ms(serialization_started)
        timing["total_ms"] = _elapsed_ms(total_started)
        response = AssessmentRunResponse(
            request_id=request_id,
            status="SUCCESS",
            result=result_data,
            warnings=tuple(_bundle_warnings(bundle.to_dict())),
            validation={"stages": stages, "timing_ms": timing},
            error=None,
        )
        return response
    except ApplicationError as exc:
        return _error_response(request_id, exc, stages, timing, total_started)
    except (KeyError, TypeError, ValueError):
        error = public_error(ErrorCode.VALIDATION_FAILED, "The request failed application validation.")
        return _error_response(request_id, error, stages, timing, total_started)
    except Exception:
        error = public_error(ErrorCode.EXECUTION_FAILED, "The assessment could not be executed.")
        return _error_response(request_id, error, stages, timing, total_started)


def validate_response_payload(value: Mapping[str, Any]) -> None:
    """Enforce the application response invariants represented by its JSON Schema."""
    payload = _mapping(value, "response")
    required = {"schema_version", "request_id", "status", "result", "warnings", "validation", "error"}
    _reject_unknown(payload, required, "response")
    if set(payload) != required or payload.get("schema_version") != APPLICATION_RESPONSE_SCHEMA_VERSION:
        raise public_error(ErrorCode.RESULT_VALIDATION_FAILED, "The application response contract is invalid.")
    if payload.get("status") == "SUCCESS":
        if not isinstance(payload.get("result"), dict) or payload.get("error") is not None:
            raise public_error(ErrorCode.RESULT_VALIDATION_FAILED, "A successful response must contain only a result.")
    elif payload.get("status") == "ERROR":
        if payload.get("result") is not None or not isinstance(payload.get("error"), dict):
            raise public_error(ErrorCode.RESULT_VALIDATION_FAILED, "An error response must contain only an error.")
    else:
        raise public_error(ErrorCode.RESULT_VALIDATION_FAILED, "The application response status is invalid.")
    if not isinstance(payload.get("warnings"), list) or not isinstance(payload.get("validation"), dict):
        raise public_error(ErrorCode.RESULT_VALIDATION_FAILED, "Response warnings or validation are invalid.")
    assert_finite_json(payload)


def _validate_run_config(run: Mapping[str, Any], assessment: Mapping[str, Any]) -> None:
    identity = assessment["assessment"]
    runtime = assessment["runtime"]
    if run["reporting_basis"] != identity["reporting_basis"]:
        raise public_error(ErrorCode.VALIDATION_FAILED, "Run reporting basis must match the assessment.")
    if run["simulation_count"] != runtime["simulation_count"] or run["random_seed"] != runtime["random_seed"]:
        raise public_error(ErrorCode.VALIDATION_FAILED, "Run seed and simulation count must match the assessment.")
    try:
        RunConfig(simulation_count=run["simulation_count"], random_seed=run["random_seed"])
    except ValueError as exc:
        raise public_error(ErrorCode.VALIDATION_FAILED, "Run configuration is outside the permitted range.") from exc


def _validate_result(result: CRQResult, assessment: Mapping[str, Any], bundle: Mapping[str, Any], config: RunConfig) -> None:
    payload = result.to_dict()
    if set(payload) != _RESULT_SECTIONS or payload.get("schema_version") != OUTPUT_SCHEMA_VERSION:
        raise public_error(ErrorCode.RESULT_VALIDATION_FAILED, "The facade result does not conform to CRQResult.")
    provenance = payload.get("provenance") or {}
    run = payload.get("run") or {}
    expected = {
        "assessment_hash": assessment["assessment_hash"],
        "bundle_hash": bundle["bundle_hash"],
        "model_bundle_id": bundle["bundle_id"],
        "model_bundle_version": bundle["model_bundle_version"],
        "sector_pack_id": bundle["sector_pack"]["pack_id"],
        "sector_pack_version": bundle["sector_pack"]["pack_version"],
        "input_schema_version": INPUT_SCHEMA_VERSION,
        "output_schema_version": OUTPUT_SCHEMA_VERSION,
    }
    if any(provenance.get(key) != value for key, value in expected.items()):
        raise public_error(ErrorCode.RESULT_VALIDATION_FAILED, "The result provenance is incompatible with the request.")
    if run.get("simulation_count") != config.simulation_count or run.get("seed") != config.random_seed:
        raise public_error(ErrorCode.RESULT_VALIDATION_FAILED, "The result runtime provenance is incompatible with the request.")
    hash_payload = {**payload, "provenance": {**provenance, "result_hash": ""}}
    try:
        expected_hash = hashlib.sha256(dumps(hash_payload).encode("utf-8")).hexdigest()
    except ValueError as exc:
        raise public_error(ErrorCode.RESULT_VALIDATION_FAILED, "The result contains a non-finite number.") from exc
    if provenance.get("result_hash") != expected_hash:
        raise public_error(ErrorCode.RESULT_VALIDATION_FAILED, "The result integrity hash is invalid.")


def _coerce_request(value: AssessmentRunRequest | Mapping[str, Any] | str | bytes) -> AssessmentRunRequest:
    if isinstance(value, AssessmentRunRequest):
        return AssessmentRunRequest.from_dict(value.to_dict())
    if isinstance(value, (str, bytes)):
        return AssessmentRunRequest.from_json(value)
    return AssessmentRunRequest.from_dict(value)


def _error_response(
    request_id: str | None,
    error: ApplicationError,
    stages: dict[str, str],
    timing: dict[str, float],
    total_started: float,
) -> AssessmentRunResponse:
    timing["total_ms"] = _elapsed_ms(total_started)
    response = AssessmentRunResponse(
        request_id=request_id,
        status="ERROR",
        result=None,
        warnings=(),
        validation={"stages": stages, "timing_ms": timing},
        error=error.public_dict(),
    )
    assert_finite_json(response.to_dict())
    return response


def _bundle_warnings(bundle: Mapping[str, Any]) -> list[str]:
    if bundle["calibration"].get("status") != "Production":
        return [f"Model bundle calibration status: {bundle['calibration'].get('status')}." ]
    return []


def _mapping(value: Any, location: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise public_error(ErrorCode.INVALID_REQUEST, f"{location} must be a JSON object.")
    return dict(value)


def _nonempty_string(value: Any, location: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise public_error(ErrorCode.INVALID_REQUEST, f"{location} must be a non-empty string.")
    return value


def _reject_unknown(value: Mapping[str, Any], allowed: set[str], location: str) -> None:
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise public_error(ErrorCode.INVALID_REQUEST, "Unknown fields are not permitted.", location=location, fields=unknown)


def _elapsed_ms(started: float) -> float:
    return (time.perf_counter() - started) * 1000.0
