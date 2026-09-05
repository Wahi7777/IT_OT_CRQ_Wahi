"""Read-only helpers for executing approved production baselines."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import openpyxl

from crq.io_safety import sha256_file
from tests.helpers import configure_run
from tests.paths import COMBINED, ROOT

REGISTRY = ROOT / "tests" / "baselines" / "approved" / "registry.json"

EXACT_FIELDS = (
    "domain", "sector", "asset_type", "engine_version", "pack_id", "seed",
    "simulation_years", "validation", "outside_in_applied",
)
PROBABILITY_FIELDS = ("best_pany", "prudent_pany")
CONTINUOUS_FIELDS = (
    "best_aal", "prudent_aal", "best_var95", "prudent_var95",
    "best_tvar95", "prudent_tvar95", "best_var99", "prudent_var99",
    "best_tvar99", "prudent_tvar99", "best_attempt_frequency",
    "prudent_attempt_frequency", "best_event_frequency",
    "prudent_event_frequency", "attempt_frequency", "event_frequency",
)


def load_registry() -> dict:
    return json.loads(REGISTRY.read_text())


def semantic_input_hash(recipe: dict) -> str:
    encoded = json.dumps(recipe, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def execute_case(case: dict, tmp_path: Path) -> dict:
    source = tmp_path / "assessment.xlsx"
    output = tmp_path / "result.xlsx"
    shutil.copy2(COMBINED, source)
    wb = openpyxl.load_workbook(source)
    recipe = case["input_recipe"]
    configure_run(
        wb,
        recipe["sector"],
        recipe["asset_type"],
        recipe["reporting_basis"],
        recipe["outside_in"],
    )
    for cell_path, value in recipe.get("patches", {}).items():
        sheet, cell = cell_path.split("!", 1)
        wb[sheet][cell] = value
    wb.save(source)
    wb.close()

    from it_ot_crq.router import run_combined

    return run_combined(
        source,
        output=output,
        sector_pack_dir=ROOT / "sector_packs",
        work_dir=tmp_path / "work",
        run_whatifs=False,
    )


def assert_source_integrity(case: dict, registry: dict) -> None:
    assert sha256_file(ROOT / registry["template"]["path"]) == registry["template"]["sha256"]
    assert sha256_file(ROOT / case["pack_path"]) == case["pack_hash"]
    assert sha256_file(ROOT / case["accepted_result"]) == case["accepted_result_hash"]
    assert semantic_input_hash(case["input_recipe"]) == case["semantic_input_hash"]


def compare_engine_result(case: dict, run_result: dict) -> None:
    expected = json.loads((ROOT / case["accepted_result"]).read_text())
    actual = dict(run_result["engine_result"])
    actual.update({"domain": run_result["domain"], "sector": run_result["sector"], "pack_id": run_result["pack_id"]})
    actual["asset_type"] = actual.get("asset_type") or case["input_recipe"]["asset_type"]
    actual["outside_in_applied"] = run_result.get("outside_in_applied")
    actual["seed"] = actual.get("random_seed")

    drifts = []
    for field in EXACT_FIELDS:
        if field in expected:
            if actual.get(field) != expected[field]:
                drifts.append(f"exact drift: {field}: actual={actual.get(field)!r} expected={expected[field]!r}")
    for field in CONTINUOUS_FIELDS:
        if field in expected:
            # Fixed-seed calculations are deterministic. This only accommodates
            # last-bit platform/library floating-point variation, not sampling drift.
            tolerance = max(1e-8, abs(float(expected[field])) * 1e-10)
            if abs(float(actual[field]) - float(expected[field])) > tolerance:
                drifts.append(
                    f"numeric drift: {field}: actual={actual[field]!r} expected={expected[field]!r} "
                    f"tolerance={tolerance!r}"
                )
    for field in PROBABILITY_FIELDS:
        if field in expected:
            if abs(float(actual[field]) - float(expected[field])) > 1e-12:
                drifts.append(f"probability drift: {field}: actual={actual[field]!r} expected={expected[field]!r}")
    for group in ("actor_aal", "scenario_aal"):
        if set(actual[group]) != set(expected[group]):
            drifts.append(f"categorical drift: {group} keys")
            continue
        for key, expected_value in expected[group].items():
            tolerance = max(1e-8, abs(float(expected_value)) * 1e-10)
            if abs(float(actual[group][key]) - float(expected_value)) > tolerance:
                drifts.append(
                    f"numeric drift: {group}/{key}: actual={actual[group][key]!r} "
                    f"expected={expected_value!r} tolerance={tolerance!r}"
                )
    assert not drifts, "\n" + "\n".join(drifts)
