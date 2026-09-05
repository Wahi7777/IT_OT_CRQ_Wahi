"""Server-side resolver for approved governed ModelBundles."""

from __future__ import annotations

import json
from pathlib import Path

from crq.application.errors import ErrorCode, public_error
from crq.application.model_bundle import load_model_bundle
from crq.application.models import ModelBundle
from crq.versions import MODEL_BUNDLE_SCHEMA_VERSION


def resolve_approved_bundle(
    bundle_id: str,
    bundle_version: str,
    domain: str,
    sector: str,
    asset_type: str | None = None,
    *,
    project_root: str | Path | None = None,
) -> ModelBundle:
    root = Path(project_root).resolve() if project_root else Path(__file__).resolve().parents[3]
    registry = json.loads((root / "config" / "approved_model_bundles.json").read_text(encoding="utf-8"))
    rows = [row for row in registry["bundles"] if row["bundle_id"] == bundle_id]
    if not rows:
        raise public_error(ErrorCode.MODEL_BUNDLE_NOT_FOUND, "The requested approved model bundle was not found.", bundle_id=bundle_id)
    row = rows[0]
    if row["status"] != "APPROVED" or row["bundle_version"] != bundle_version:
        raise public_error(ErrorCode.MODEL_BUNDLE_NOT_FOUND, "The requested approved model bundle version was not found.", bundle_id=bundle_id, bundle_version=bundle_version)
    if row["domain"] != domain or row["sector"] != sector:
        raise public_error(ErrorCode.MODEL_BUNDLE_INCOMPATIBLE, "The approved model bundle is incompatible with the assessment domain or sector.", bundle_id=bundle_id, domain=domain, sector=sector)
    bundle = load_model_bundle(domain, sector, project_root=root)
    data = bundle.to_dict()
    if asset_type is not None and asset_type not in data["applicability"]["asset_types"]:
        raise public_error(
            ErrorCode.MODEL_BUNDLE_INCOMPATIBLE,
            "The approved model bundle is incompatible with the assessment asset type.",
            bundle_id=bundle_id,
            asset_type=asset_type,
        )
    checks = {
        "schema_version": (data["schema_version"], MODEL_BUNDLE_SCHEMA_VERSION),
        "engine_version": (data["engine_version"], row["engine_version"]),
        "pack_id": (data["sector_pack"]["pack_id"], row["bundle_id"]),
        "pack_version": (data["sector_pack"]["pack_version"], row["pack_version"]),
        "pack_hash": (data["sector_pack"]["pack_hash"], row["pack_hash"]),
        "bundle_version": (data["model_bundle_version"], row["bundle_version"]),
    }
    failed = [name for name, values in checks.items() if values[0] != values[1]]
    if failed:
        raise public_error(ErrorCode.MODEL_BUNDLE_INCOMPATIBLE, "The governed bundle failed integrity or compatibility validation.", checks=failed)
    return bundle
