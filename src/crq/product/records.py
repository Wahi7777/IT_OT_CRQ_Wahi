"""Persistence record helpers; metadata only, never quantitative calculation."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from crq.product.contracts import PRODUCT_OBJECT_SCHEMA_VERSION


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def metadata_record(
    *,
    tenant_id: str,
    user_id: str,
    assessment_id: str,
    assessment_version: int,
    created_at: str,
    domain: str,
    sector: str,
    bundle_id: str | None,
    engine_version: str | None,
    methodology_version: str | None,
    assessment_hash: str | None,
    run_id: str | None = None,
    result_hash: str | None = None,
    status: str | None = None,
    updated_at: str | None = None,
) -> dict[str, Any]:
    return {
        "object_schema_version": PRODUCT_OBJECT_SCHEMA_VERSION,
        "tenant_id": tenant_id,
        "user_id": user_id,
        "assessment_id": assessment_id,
        "assessment_version": assessment_version,
        "run_id": run_id,
        "created_at": created_at,
        "updated_at": updated_at or created_at,
        "created_by": user_id,
        "domain": domain,
        "sector": sector,
        "bundle_id": bundle_id,
        "engine_version": engine_version,
        "methodology_version": methodology_version,
        "assessment_hash": assessment_hash,
        "result_hash": result_hash,
        "status": status,
    }
