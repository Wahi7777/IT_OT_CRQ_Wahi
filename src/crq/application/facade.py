"""Stable runtime-neutral public entry points over unchanged workbook engines."""

from __future__ import annotations

import os
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from crq.application.excel_adapter import materialize_compatibility_workbook
from crq.application.models import CRQAssessment, CRQResult, ModelBundle, RunConfig
from crq.application.result_adapter import normalize_result


def run_it_assessment(assessment: CRQAssessment, model_bundle: ModelBundle, run_config: RunConfig) -> CRQResult:
    return _run("IT", assessment, model_bundle, run_config)


def run_ot_assessment(assessment: CRQAssessment, model_bundle: ModelBundle, run_config: RunConfig) -> CRQResult:
    return _run("OT", assessment, model_bundle, run_config)


def _run(domain: str, assessment: CRQAssessment, bundle: ModelBundle, config: RunConfig) -> CRQResult:
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
        materialize_compatibility_workbook(assessment, template, source)
        from it_ot_crq.router import run_combined
        with _runtime_flags(config):
            result = run_combined(
                source,
                output=output,
                sector_pack_dir=root / "sector_packs",
                work_dir=work / "engine-work",
                run_whatifs=config.run_whatifs,
            )
        return normalize_result(result, assessment, bundle, config, started)


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
