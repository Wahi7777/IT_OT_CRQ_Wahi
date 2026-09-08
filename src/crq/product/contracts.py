"""Small versioned contracts for the asynchronous product boundary."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping

from crq.application.models import json_value


JOB_SCHEMA_VERSION = "1.0"
PRODUCT_OBJECT_SCHEMA_VERSION = "1.0"
_SAFE_ID = re.compile(r"^[A-Za-z0-9_.:-]{1,128}$")


def safe_identifier(value: Any, name: str) -> str:
    if not isinstance(value, str) or not _SAFE_ID.fullmatch(value):
        raise ValueError(f"{name} is invalid")
    return value


@dataclass(frozen=True)
class ProductJob:
    run_id: str
    assessment_id: str
    tenant_id: str
    bundle_id: str
    run_config: dict[str, Any]
    job_schema_version: str = JOB_SCHEMA_VERSION

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ProductJob":
        payload = json_value(value)
        expected = {"job_schema_version", "run_id", "assessment_id", "tenant_id", "bundle_id", "run_config"}
        if not isinstance(payload, dict) or set(payload) != expected or payload.get("job_schema_version") != JOB_SCHEMA_VERSION:
            raise ValueError("job contract is invalid")
        run_config = payload.get("run_config")
        if not isinstance(run_config, dict) or set(run_config) != {"simulation_count", "random_seed", "reporting_basis"}:
            raise ValueError("job run_config is invalid")
        if type(run_config.get("simulation_count")) is not int or not 10_000 <= run_config["simulation_count"] <= 2_000_000:
            raise ValueError("job simulation_count is invalid")
        if type(run_config.get("random_seed")) is not int or run_config["random_seed"] < 0:
            raise ValueError("job random_seed is invalid")
        if run_config.get("reporting_basis") not in {"Best Estimate", "Prudent", "Both"}:
            raise ValueError("job reporting_basis is invalid")
        return cls(
            run_id=safe_identifier(payload.get("run_id"), "run_id"),
            assessment_id=safe_identifier(payload.get("assessment_id"), "assessment_id"),
            tenant_id=safe_identifier(payload.get("tenant_id"), "tenant_id"),
            bundle_id=safe_identifier(payload.get("bundle_id"), "bundle_id"),
            run_config=dict(run_config),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_schema_version": self.job_schema_version,
            "run_id": self.run_id,
            "assessment_id": self.assessment_id,
            "tenant_id": self.tenant_id,
            "bundle_id": self.bundle_id,
            "run_config": json_value(self.run_config),
        }


def assessment_key(tenant_id: str, assessment_id: str, name: str) -> str:
    return f"assessments/{safe_identifier(tenant_id, 'tenant_id')}/{safe_identifier(assessment_id, 'assessment_id')}/{name}"


def run_key(tenant_id: str, run_id: str, name: str) -> str:
    return f"runs/{safe_identifier(tenant_id, 'tenant_id')}/{safe_identifier(run_id, 'run_id')}/{name}"
