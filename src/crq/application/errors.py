"""Safe public error taxonomy for the framework-neutral application service."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class ErrorCode(StrEnum):
    INVALID_REQUEST = "INVALID_REQUEST"
    INVALID_ASSESSMENT = "INVALID_ASSESSMENT"
    UNSUPPORTED_DOMAIN = "UNSUPPORTED_DOMAIN"
    UNSUPPORTED_SECTOR = "UNSUPPORTED_SECTOR"
    MODEL_BUNDLE_NOT_FOUND = "MODEL_BUNDLE_NOT_FOUND"
    MODEL_BUNDLE_INCOMPATIBLE = "MODEL_BUNDLE_INCOMPATIBLE"
    SCHEMA_VERSION_UNSUPPORTED = "SCHEMA_VERSION_UNSUPPORTED"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    EXECUTION_FAILED = "EXECUTION_FAILED"
    RESULT_VALIDATION_FAILED = "RESULT_VALIDATION_FAILED"


@dataclass(frozen=True)
class ApplicationError(Exception):
    code: ErrorCode
    message: str
    details: dict[str, Any] | None = None

    def public_dict(self) -> dict[str, Any]:
        return {"code": self.code.value, "message": self.message, "details": self.details or {}}


def public_error(code: ErrorCode, message: str, **details: Any) -> ApplicationError:
    return ApplicationError(code, message, details or None)
