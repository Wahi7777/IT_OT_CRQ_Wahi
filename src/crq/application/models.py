"""Immutable value objects used at the application/quantitative boundary."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date, datetime
from types import MappingProxyType
from typing import Any, Mapping


def json_value(value: Any) -> Any:
    """Convert workbook/NumPy values into deterministic JSON-compatible values."""
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if hasattr(value, "item"):
        return json_value(value.item())
    if isinstance(value, Mapping):
        return {str(k): json_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_value(v) for v in value]
    return str(value)


def canonical_hash(value: Any) -> str:
    payload = json.dumps(json_value(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({str(k): _freeze(v) for k, v in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(v) for v in value)
    if isinstance(value, tuple):
        return tuple(_freeze(v) for v in value)
    return value


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(k): _thaw(v) for k, v in value.items()}
    if isinstance(value, tuple):
        return [_thaw(v) for v in value]
    return json_value(value)


@dataclass(frozen=True)
class RunConfig:
    simulation_count: int
    random_seed: int
    run_whatifs: bool = False
    run_packages: bool = False
    run_sensitivity: bool = False

    def __post_init__(self) -> None:
        if not 10_000 <= int(self.simulation_count) <= 2_000_000:
            raise ValueError("simulation_count must be between 10,000 and 2,000,000.")
        if int(self.random_seed) < 0:
            raise ValueError("random_seed must be non-negative.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "simulation_count": int(self.simulation_count),
            "random_seed": int(self.random_seed),
            "run_whatifs": bool(self.run_whatifs),
            "run_packages": bool(self.run_packages),
            "run_sensitivity": bool(self.run_sensitivity),
        }


@dataclass(frozen=True)
class CRQAssessment:
    _data: Mapping[str, Any]

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "CRQAssessment":
        payload = json_value(data)
        _validate_assessment(payload)
        payload["assessment_hash"] = canonical_hash({k: v for k, v in payload.items() if k != "assessment_hash"})
        return cls(_freeze(payload))

    def to_dict(self) -> dict[str, Any]:
        return _thaw(self._data)

    def __getitem__(self, key: str) -> Any:
        return self._data[key]

    @property
    def domain(self) -> str:
        return str(self._data["assessment"]["domain"])

    @property
    def sector(self) -> str:
        return str(self._data["assessment"]["sector"])


@dataclass(frozen=True)
class ModelBundle:
    _data: Mapping[str, Any]

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ModelBundle":
        payload = json_value(data)
        expected = payload.pop("bundle_hash", None)
        calculated = canonical_hash(payload)
        if expected not in (None, calculated):
            raise ValueError("ModelBundle hash does not match its governed content.")
        payload["bundle_hash"] = calculated
        return cls(_freeze(payload))

    def to_dict(self) -> dict[str, Any]:
        return _thaw(self._data)

    def __getitem__(self, key: str) -> Any:
        return self._data[key]


@dataclass(frozen=True)
class CRQResult:
    _data: Mapping[str, Any]

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "CRQResult":
        return cls(_freeze(json_value(data)))

    def to_dict(self) -> dict[str, Any]:
        return _thaw(self._data)

    def __getitem__(self, key: str) -> Any:
        return self._data[key]


def _validate_assessment(data: Mapping[str, Any]) -> None:
    if data.get("schema_version") != "1.0.0-draft":
        raise ValueError("Unsupported CRQAssessment schema_version.")
    identity = data.get("assessment") or {}
    domain = identity.get("domain")
    sector = identity.get("sector")
    allowed = {
        "IT": {"Financial Services"},
        "OT": {"Power Generation", "Energy Assets", "Manufacturing"},
    }
    if domain not in allowed or sector not in allowed[domain]:
        raise ValueError(f"Sector {sector!r} is not valid for domain {domain!r}.")
    basis = identity.get("reporting_basis")
    if basis not in {"Best Estimate", "Prudent", "Both"}:
        raise ValueError("reporting_basis must be Best Estimate, Prudent, or Both.")
    runtime = data.get("runtime") or {}
    RunConfig(
        simulation_count=int(runtime.get("simulation_count")),
        random_seed=int(runtime.get("random_seed")),
        run_whatifs=bool(runtime.get("run_whatifs", False)),
        run_packages=bool(runtime.get("run_packages", False)),
        run_sensitivity=bool(runtime.get("run_sensitivity", False)),
    )
    cells = (data.get("compatibility") or {}).get("workbook_cells") or []
    allowed_classes = {"USER_INPUT", "PERMITTED_OVERRIDE", "EVIDENCE_ONLY", "INACTIVE_LEGACY"}
    for cell in cells:
        if cell.get("classification") not in allowed_classes:
            raise ValueError(f"Assessment contains non-client-owned cell {cell!r}.")
