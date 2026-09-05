"""Stable runtime-neutral public entry points over unchanged workbook engines."""

from __future__ import annotations

import os
import tempfile
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from crq.application.excel_adapter import materialize_compatibility_workbook
from crq.application.models import CRQAssessment, CRQResult, ModelBundle, RunConfig
from crq.application.result_adapter import normalize_result


def run_it_assessment(
    assessment: CRQAssessment,
    model_bundle: ModelBundle,
    run_config: RunConfig,
    *,
    diagnostics: dict[str, float] | None = None,
) -> CRQResult:
    return _run("IT", assessment, model_bundle, run_config, diagnostics=diagnostics)


def run_ot_assessment(
    assessment: CRQAssessment,
    model_bundle: ModelBundle,
    run_config: RunConfig,
    *,
    diagnostics: dict[str, float] | None = None,
) -> CRQResult:
    return _run("OT", assessment, model_bundle, run_config, diagnostics=diagnostics)


def _run(
    domain: str,
    assessment: CRQAssessment,
    bundle: ModelBundle,
    config: RunConfig,
    *,
    diagnostics: dict[str, float] | None = None,
) -> CRQResult:
    if assessment.domain != domain:
        raise ValueError(f"{domain} facade cannot execute a {assessment.domain} assessment.")
    bundle_data = bundle.to_dict()
    if bundle_data["applicability"]["domain"] != domain or assessment.sector not in bundle_data["applicability"]["sectors"]:
        raise ValueError("ModelBundle is not applicable to the assessment domain/sector.")
    data = assessment.to_dict()
    if data["runtime"]["simulation_count"] != config.simulation_count or data["runtime"]["random_seed"] != config.random_seed:
        raise ValueError("RunConfig seed/count must match the validated assessment during the compatibility phase.")
    root = Path(__file__).resolve().parents[3]
    template = root / "model" / "Guided_IT_OT_CRQ_Model_v1_0.xlsx"
    started = datetime.now(timezone.utc)
    with tempfile.TemporaryDirectory(prefix=f"crq-{domain.lower()}-") as temp:
        work = Path(temp)
        source = work / "assessment.xlsx"
        output = work / "result.xlsx"
        materialization_started = time.perf_counter()
        materialize_compatibility_workbook(assessment, template, source)
        materialization_elapsed = time.perf_counter() - materialization_started
        from it_ot_crq.router import run_combined
        with _runtime_flags(config):
            engine_started = time.perf_counter()
            result = run_combined(
                source,
                output=output,
                sector_pack_dir=root / "sector_packs",
                work_dir=work / "engine-work",
                run_whatifs=config.run_whatifs,
            )
            engine_elapsed = time.perf_counter() - engine_started
        normalization_started = time.perf_counter()
        normalized = normalize_result(result, assessment, bundle, config, started)
        if diagnostics is not None:
            diagnostics["workbook_materialization_ms"] = materialization_elapsed * 1000.0
            diagnostics["engine_execution_ms"] = engine_elapsed * 1000.0
            diagnostics["result_normalization_ms"] = (time.perf_counter() - normalization_started) * 1000.0
        return normalized


@contextmanager
def _runtime_flags(config: RunConfig) -> Iterator[None]:
    names = {"CRQ_RUN_PACKAGES": "1" if config.run_packages else None, "CRQ_RUN_SENSITIVITY": "1" if config.run_sensitivity else None, "OT_CRQ_USE_XLSX_BACKEND": "1"}
    previous = {name: os.environ.get(name) for name in names}
    try:
        for name, value in names.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        yield
    finally:
        for name, value in previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
