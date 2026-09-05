#!/usr/bin/env python3
"""Deliberately regenerate non-authoritative Phase 3A request/response examples.

This command never reads from or writes to tests/baselines/approved.
"""

from __future__ import annotations

import argparse
import shutil
import tempfile
from pathlib import Path

import openpyxl

from crq.application import execute_assessment, extract_assessment, public_assessment_payload
from crq.application.serialization import dumps
from tests.helpers import configure_run
from tests.paths import COMBINED, ROOT


CASES = {
    "it-fs": ("Financial Services", "Organisation", "FS-v1.1.1"),
    "ot-pg": ("Power Generation", "CCGT", "PG-v1.6"),
}


def build_request(case_id: str, work: Path) -> dict:
    sector, asset, bundle_id = CASES[case_id]
    source = work / f"{case_id}.xlsx"
    shutil.copy2(COMBINED, source)
    wb = openpyxl.load_workbook(source)
    try:
        configure_run(wb, sector, asset, basis="Prudent", outside_in="No")
        wb.save(source)
    finally:
        wb.close()
    assessment = public_assessment_payload(extract_assessment(source, run_whatifs=False))
    runtime = assessment["runtime"]
    return {
        "schema_version": "1.0.0",
        "request_id": f"example-{case_id}-500k",
        "assessment": assessment,
        "model_bundle_reference": {"bundle_id": bundle_id, "bundle_version": "1.0.0"},
        "run_config": {
            "reporting_basis": "Prudent",
            "simulation_count": runtime["simulation_count"],
            "random_seed": runtime["random_seed"],
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", choices=[*CASES, "all"], default="all")
    args = parser.parse_args()
    selected = CASES if args.case == "all" else {args.case: CASES[args.case]}
    destination = ROOT / "contracts" / "examples"
    with tempfile.TemporaryDirectory(prefix="crq-application-examples-") as temp:
        for case_id in selected:
            request = build_request(case_id, Path(temp))
            response = execute_assessment(request)
            if response.status != "SUCCESS":
                raise RuntimeError(f"Example execution failed: {response.error}")
            (destination / f"assessment-run-request-{case_id}.json").write_text(dumps(request) + "\n", encoding="utf-8")
            (destination / f"assessment-run-response-{case_id}.json").write_text(response.to_json() + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
