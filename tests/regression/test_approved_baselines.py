"""Execute current engines and compare them with immutable approved baselines."""

from __future__ import annotations

import hashlib
from pathlib import Path
import pytest

from tests.regression.baseline_support import (
    assert_source_integrity,
    compare_engine_result,
    execute_case,
    load_registry,
)

REGISTRY = load_registry()
CASES = REGISTRY["cases"]


def test_approved_registry_matches_signed_checksum():
    registry_path = Path(__file__).resolve().parents[1] / "baselines" / "approved" / "registry.json"
    approval_path = registry_path.with_name("APPROVAL.sha256")
    approved_hash = approval_path.read_text().split()[0]
    assert hashlib.sha256(registry_path.read_bytes()).hexdigest() == approved_hash
    correction = REGISTRY["approval"].get("ot_var_correction_record")
    if correction:
        correction_path = Path(__file__).resolve().parents[2] / correction
        assert hashlib.sha256(correction_path.read_bytes()).hexdigest() == REGISTRY["approval"]["ot_var_correction_record_hash"]


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["baseline_id"])
def test_approved_baseline_artifacts_are_unchanged(case):
    assert_source_integrity(case, REGISTRY)


@pytest.mark.production
@pytest.mark.parametrize("case", CASES, ids=lambda case: case["baseline_id"])
def test_current_engine_matches_approved_baseline(case, tmp_path, monkeypatch):
    monkeypatch.setenv("OT_CRQ_USE_XLSX_BACKEND", "1")
    result = execute_case(case, tmp_path)
    compare_engine_result(case, result)
