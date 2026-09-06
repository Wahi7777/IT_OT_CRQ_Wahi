#!/usr/bin/env python3
"""Local-equivalent cold/warm measurements for the Lambda event boundary."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import platform
import resource
import subprocess  # nosec B404
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
CASES = {
    "IT Financial Services 500k": ROOT / "contracts/examples/assessment-run-request-it-fs.json",
    "OT Power Generation 500k": ROOT / "contracts/examples/assessment-run-request-ot-pg.json",
}
MARKER = "CRQ_LAMBDA_BENCHMARK="


def _memory_mb(raw: int) -> float:
    return raw / (1024 * 1024) if sys.platform == "darwin" else raw / 1024


def _invoke(handler, request: dict, suffix: str) -> tuple[dict, float, int]:
    event = {
        "version": "2.0",
        "rawPath": "/v1/assessments/run",
        "headers": {"content-type": "application/json"},
        "requestContext": {"requestId": f"benchmark-{suffix}", "http": {"method": "POST", "path": "/v1/assessments/run"}},
        "isBase64Encoded": False,
        "body": json.dumps(request, separators=(",", ":")),
    }
    started = time.perf_counter()
    http = handler(event, SimpleNamespace(aws_request_id=f"benchmark-{suffix}"))
    elapsed = (time.perf_counter() - started) * 1000.0
    payload = json.loads(http["body"])
    if http["statusCode"] != 200:
        raise RuntimeError(payload["error"])
    return payload, elapsed, len(http["body"].encode("utf-8"))


def _parity_hash(result: dict) -> str:
    from crq.application.serialization import dumps

    payload = copy.deepcopy(result)
    for key in ("run_id", "started_at", "completed_at"):
        payload["run"].pop(key, None)
    payload["provenance"]["result_hash"] = ""
    for key in ("run_id", "timestamp", "input_hash"):
        payload["compatibility"]["router_metadata"].pop(key, None)
    return hashlib.sha256(dumps(payload).encode("utf-8")).hexdigest()


def worker(request_path: Path) -> int:
    import_started = time.perf_counter()
    from crq.lambda_adapter import handler
    import_ms = (time.perf_counter() - import_started) * 1000.0
    request = json.loads(request_path.read_text())
    cold, cold_ms, response_bytes = _invoke(handler, request, "cold")
    warm, warm_ms, _ = _invoke(handler, request, "warm")
    result = {
        "adapter_import_ms": import_ms,
        "cold_total_ms": import_ms + cold_ms,
        "cold_handler_ms": cold_ms,
        "warm_handler_ms": warm_ms,
        "cold_stage_timing_ms": cold["validation"]["timing_ms"],
        "warm_stage_timing_ms": warm["validation"]["timing_ms"],
        "response_bytes": response_bytes,
        "peak_process_memory_mb": _memory_mb(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss),
        "cold_result_hash": cold["result"]["provenance"]["result_hash"],
        "warm_result_hash": warm["result"]["provenance"]["result_hash"],
        "cold_parity_hash": _parity_hash(cold["result"]),
        "warm_parity_hash": _parity_hash(warm["result"]),
    }
    print(MARKER + json.dumps(result, sort_keys=True))
    return 0


def parent(output: Path) -> int:
    cases = {}
    for name, request_path in CASES.items():
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
        "actual_aws_execution": False,
        "host": {"platform": platform.platform(), "python": platform.python_version(), "processor": platform.processor()},
        "cases": cases,
        "lambda_memory_plan": {
            "2048_mb": "REQUIRED_FIRST_AWS_MEASUREMENT",
            "3072_mb": "REQUIRED_AWS_COMPARISON",
            "4096_mb": "REQUIRED_AWS_COMPARISON",
        },
        "deployment_benchmark_plan": [
            "Publish one immutable package/version and invoke each case once cold and at least five times warm at 2048, 3072 and 4096 MB.",
            "Record Lambda REPORT init duration, billed duration, max memory used, service stage timings, response size and result hash.",
            "Compare canonical CRQResult with the Phase 3A example result at every memory setting.",
            "Select the lowest-cost setting that retains timeout and memory headroom; do not alter quantitative code.",
        ],
    }
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(output)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker", type=Path)
    parser.add_argument("--output", type=Path, default=ROOT / "docs/productisation/lambda-boundary-benchmark.json")
    args = parser.parse_args()
    return worker(args.worker) if args.worker else parent(args.output)


if __name__ == "__main__":
    raise SystemExit(main())
