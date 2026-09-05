"""Strict deterministic JSON serialization with finite-number enforcement."""

from __future__ import annotations

import json
import math
from typing import Any

from crq.application.models import json_value


def assert_finite_json(value: Any, path: str = "$") -> None:
    normalized = json_value(value)
    if isinstance(normalized, float) and not math.isfinite(normalized):
        raise ValueError(f"Non-finite number at {path}.")
    if isinstance(normalized, dict):
        for key, item in normalized.items():
            assert_finite_json(item, f"{path}.{key}")
    elif isinstance(normalized, list):
        for index, item in enumerate(normalized):
            assert_finite_json(item, f"{path}[{index}]")


def dumps(value: Any) -> str:
    normalized = json_value(value)
    return json.dumps(normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def loads(payload: str | bytes) -> Any:
    def reject_constant(value: str) -> None:
        raise ValueError(f"Invalid JSON numeric constant {value}.")

    return json.loads(payload, parse_constant=reject_constant)
