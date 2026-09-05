#!/usr/bin/env python3
"""Benchmark the synchronous Phase 3A service in isolated child processes."""

from __future__ import annotations

import argparse
import json
import os
import platform
import resource
import subprocess  # nosec B404
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = {
    "IT Financial Services 500k": ROOT / "contracts/examples/assessment-run-request-it-fs.json",
    "OT Power Generation 500k": ROOT / "contracts/examples/assessment-run-request-ot-pg.json",
}
MARKER = "CRQ_BENCHMARK_RESULT="


def _memory_mb(raw: int) -> float:
    # macOS reports bytes; Linux reports KiB.
    return raw / (1024 * 1024) if sys.platform == "darwin" else raw / 1024


def worker(request_path: Path) -> int:
    import_started = time.perf_counter()
    from crq.application.service import execute_assessment
    from crq.application.serialization import loads
    import_ms = (time.perf_counter() - import_started) * 1000.0
    raw = request_path.read_bytes()
    request = loads(raw)
    response = execute_assessment(request)
    serialized = response.to_json().encode("utf-8")
    if response.status != "SUCCESS":
        raise RuntimeError(response.error)
    timing = response.validation["timing_ms"]
    application_ms = sum(timing.get(key, 0.0) for key in ("validation_ms", "bundle_resolution_ms", "result_validation_ms", "serialization_ms"))
    result = {
        "application_import_ms": import_ms,
        "timing_ms": timing,
        "application_boundary_ms": application_ms,
        "application_boundary_percent_of_engine": application_ms / timing["engine_execution_ms"] * 100.0,
        "input_bytes": len(raw),
        "output_bytes": len(serialized),
        "peak_process_memory_mb": _memory_mb(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss),
        "status": response.status,
        "result_hash": response.result["provenance"]["result_hash"],
    }
    print(MARKER + json.dumps(result, sort_keys=True))
    return 0


def parent(output: Path) -> int:
    cases = {}
    for name, request_path in EXAMPLES.items():
        env = dict(os.environ)
        env["PYTHONPATH"] = os.pathsep.join((str(ROOT / "src"), str(ROOT)))
        completed = subprocess.run(  # nosec B603
            [sys.executable, __file__, "--worker", str(request_path)],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        line = next(row for row in completed.stdout.splitlines() if row.startswith(MARKER))
        cases[name] = json.loads(line.removeprefix(MARKER))
    report = {
        "benchmark_schema_version": "1.0.0",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "host": {"platform": platform.platform(), "python": platform.python_version(), "processor": platform.processor()},
        "method": "One clean child process per case; resource.getrusage peak RSS; application service internal stage timers.",
        "cases": cases,
        "conclusion": "MEASURED_NOT_DEPLOYMENT_BENCHMARK",
        "limitations": [
            "Local workstation measurements are not Lambda measurements.",
            "Peak RSS includes Python, OpenPyXL, NumPy, governed bundle loading, workbook compatibility materialisation, and the engine.",
        ],
    }
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(output)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker", type=Path)
    parser.add_argument("--output", type=Path, default=ROOT / "docs/productisation/application-service-benchmark.json")
    args = parser.parse_args()
    return worker(args.worker) if args.worker else parent(args.output)


if __name__ == "__main__":
    raise SystemExit(main())
