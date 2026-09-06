#!/usr/bin/env python3
"""Build a reproducible Linux arm64 Python 3.12 Lambda ZIP."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import shutil
import subprocess  # nosec B404
import sys
import tempfile
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "_work/lambda/crq-lambda-python312-arm64.zip"
DEFAULT_REPORT = ROOT / "docs/productisation/lambda-package-report.json"
ASSET_DIRS = ("src", "model", "sector_packs", "config")
MAPPING = Path("contracts/mappings/model-bundle-source-map.json")


def _copy_tree(source: Path, destination: Path) -> None:
    shutil.copytree(
        source,
        destination,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store"),
    )


def _zip_tree(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(item for item in source.rglob("*") if item.is_file()):
            relative = path.relative_to(source).as_posix()
            info = zipfile.ZipInfo(relative, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o644 & 0xFFFF) << 16
            archive.writestr(info, path.read_bytes(), compresslevel=9)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="crq-lambda-build-") as temp:
        stage = Path(temp) / "stage"
        stage.mkdir()
        command = [
            sys.executable, "-m", "pip", "install",
            "--target", str(stage),
            "--platform", "manylinux_2_28_aarch64",
            "--implementation", "cp",
            "--python-version", "3.12",
            "--abi", "cp312",
            "--only-binary=:all:",
            "--no-compile",
            "-r", str(ROOT / "requirements.txt"),
        ]
        subprocess.run(command, cwd=ROOT, check=True)  # nosec B603
        for directory in ASSET_DIRS:
            _copy_tree(ROOT / directory, stage / directory)
        mapping_destination = stage / MAPPING
        mapping_destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / MAPPING, mapping_destination)
        _zip_tree(stage, args.output)
        content = args.output.read_bytes()
        digest = hashlib.sha256(content).digest()
        files = [path for path in stage.rglob("*") if path.is_file()]
        report = {
            "package_schema_version": "1.0.0",
            "artifact_type": "Lambda ZIP",
            "runtime": "python3.12",
            "architecture": "arm64",
            "target_platform": "manylinux_2_28_aarch64 (Amazon Linux 2023 compatible)",
            "handler": "crq.lambda_adapter.handler",
            "pythonpath": "/var/task/src",
            "compressed_bytes": len(content),
            "uncompressed_bytes": sum(path.stat().st_size for path in files),
            "file_count": len(files),
            "sha256": digest.hex(),
            "base64sha256": base64.b64encode(digest).decode("ascii"),
            "bundled_assets": list(ASSET_DIRS) + [MAPPING.as_posix()],
            "dependencies": {"numpy": "2.5.2", "openpyxl": "3.1.5", "et-xmlfile": "2.0.0"},
            "reproducibility": "Pinned wheels, fixed ZIP timestamps, sorted entries, normalized file modes.",
            "local_import_note": "Linux arm64 native wheels cannot be imported on the macOS build host; source-equivalent import is measured by the Lambda-boundary benchmark.",
        }
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
