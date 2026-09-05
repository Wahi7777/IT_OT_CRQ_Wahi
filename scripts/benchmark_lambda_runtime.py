"""Benchmark unchanged production CRQ runs for an initial Lambda decision.

Results are printed to stdout unless --output is supplied. Temporary assessment
and output workbooks are created under a temporary directory and deleted. The
script never reads from or writes to approved baseline directories.
"""

from __future__ import annotations

import argparse
import json
import os
import resource
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CASES = {
    "it-fs": ("Financial Services", "Organisation", True),
    "ot-pg": ("Power Generation", "CCGT", False),
    "ot-ea": ("Energy Assets", "Upstream Onshore", False),
    "ot-mf": ("Manufacturing", "Process Manufacturing", False),
}


def _directory_size(path: Path) -> int:
    return sum(p.stat().st_size for p in path.rglob("*") if p.is_file())


def _json_size(value) -> int:
    def default(obj):
        if hasattr(obj, "tolist"):
            return obj.tolist()
        if hasattr(obj, "item"):
            return obj.item()
        return str(obj)

    return len(json.dumps(value, default=default, separators=(",", ":")).encode())


def _peak_rss_bytes() -> int:
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(value if sys.platform == "darwin" else value * 1024)


def run_worker(case_name: str) -> dict:
    process_start = time.perf_counter()
    cpu_start = time.process_time()
    sys.path.insert(0, str(ROOT / "src"))
    sys.path.insert(0, str(ROOT))
    os.environ.setdefault("OT_CRQ_USE_XLSX_BACKEND", "1")

    import openpyxl
    from tests.helpers import configure_run
    from tests.paths import COMBINED
    import it_crq.engine as it_engine
    import ot_crq.engine as ot_engine
    import it_ot_crq.router as router

    import_seconds = time.perf_counter() - process_start
    sector, asset, is_it = CASES[case_name]
    inner = {"seconds": None}
    original = it_engine.refresh if is_it else ot_engine.refresh

    def timed_refresh(*args, **kwargs):
        started = time.perf_counter()
        try:
            return original(*args, **kwargs)
        finally:
            inner["seconds"] = time.perf_counter() - started

    if is_it:
        it_engine.refresh = timed_refresh
    else:
        ot_engine.refresh = timed_refresh

    with tempfile.TemporaryDirectory(prefix=f"crq-bench-{case_name}-") as tmp_name:
        tmp = Path(tmp_name)
        source = tmp / "assessment.xlsx"
        output = tmp / "result.xlsx"
        shutil.copy2(COMBINED, source)
        setup_start = time.perf_counter()
        wb = openpyxl.load_workbook(source)
        configure_run(wb, sector, asset)
        if is_it:
            wb["IT 03 - Organisation Inputs"]["C30"] = 500_000
        wb.save(source)
        wb.close()
        setup_seconds = time.perf_counter() - setup_start
        input_size = source.stat().st_size

        peak_temp = {"bytes": _directory_size(tmp), "stop": False}

        def monitor():
            while not peak_temp["stop"]:
                peak_temp["bytes"] = max(peak_temp["bytes"], _directory_size(tmp))
                time.sleep(0.05)

        thread = threading.Thread(target=monitor, daemon=True)
        thread.start()
        run_start = time.perf_counter()
        result = router.run_combined(
            source,
            output=output,
            sector_pack_dir=ROOT / "sector_packs",
            work_dir=tmp / "work",
            run_whatifs=False,
        )
        total_run_seconds = time.perf_counter() - run_start
        peak_temp["stop"] = True
        thread.join(timeout=1)
        peak_temp["bytes"] = max(peak_temp["bytes"], _directory_size(tmp))
        engine_seconds = float(inner["seconds"] or total_run_seconds)
        output_size = output.stat().st_size
        result_size = _json_size(result["engine_result"])
        cpu_seconds = time.process_time() - cpu_start
        wall_seconds = time.perf_counter() - process_start
        return {
            "case": case_name,
            "sector": sector,
            "asset_type": asset,
            "simulation_count": result["engine_result"].get("simulation_years"),
            "seed": result["engine_result"].get("random_seed"),
            "validation": result.get("validation"),
            "cold_import_seconds": import_seconds,
            "assessment_prepare_and_save_seconds": setup_seconds,
            "total_router_run_seconds": total_run_seconds,
            "engine_refresh_seconds_including_engine_workbook_io": engine_seconds,
            "router_and_report_workbook_overhead_seconds": max(0.0, total_run_seconds - engine_seconds),
            "process_wall_seconds": wall_seconds,
            "process_cpu_seconds": cpu_seconds,
            "cpu_utilisation_one_core_percent": 100.0 * cpu_seconds / max(wall_seconds, 1e-9),
            "peak_rss_bytes": _peak_rss_bytes(),
            "input_workbook_bytes": input_size,
            "output_workbook_bytes": output_size,
            "structured_engine_result_json_bytes": result_size,
            "peak_temporary_disk_bytes": peak_temp["bytes"],
            "measurement_note": "Current engine refresh includes native workbook I/O; router/report overhead is measured separately. Pure calculation time cannot be isolated without prohibited engine instrumentation/refactoring."
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", nargs="+", choices=sorted(CASES), default=["it-fs", "ot-pg", "ot-ea"])
    parser.add_argument("--output", type=Path)
    parser.add_argument("--worker", choices=sorted(CASES))
    args = parser.parse_args()
    if args.worker:
        print(json.dumps(run_worker(args.worker), sort_keys=True))
        return 0

    results = []
    for case in args.cases:
        proc = subprocess.run(
            [sys.executable, str(Path(__file__).resolve()), "--worker", case],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=True,
        )
        results.append(json.loads(proc.stdout.strip().splitlines()[-1]))
    report = {
        "benchmark_schema_version": "1.0.0",
        "captured_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "python": sys.version,
        "platform": sys.platform,
        "cases": results,
    }
    encoded = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded)
    print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

