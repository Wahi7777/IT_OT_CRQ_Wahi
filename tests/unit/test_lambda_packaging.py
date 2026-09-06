from __future__ import annotations

import json
import hashlib
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_v1_python_runtime_is_consistent():
    assert (ROOT / ".python-version").read_text().strip() == "3.12"
    assert 'requires-python = ">=3.12,<3.13"' in (ROOT / "pyproject.toml").read_text()
    terraform = (ROOT / "infra/phase3b/main.tf").read_text()
    assert 'runtime          = "python3.12"' in terraform
    assert 'architectures    = ["arm64"]' in terraform
    assert 'PYTHONPATH = "/var/task/src"' in terraform
    assert 'TMPDIR     = "/tmp"' in terraform


def test_package_measurement_fits_zip_limits():
    report = json.loads((ROOT / "docs/productisation/lambda-package-report.json").read_text())
    assert report["artifact_type"] == "Lambda ZIP"
    assert report["runtime"] == "python3.12"
    assert report["architecture"] == "arm64"
    assert report["compressed_bytes"] < 50 * 1024 * 1024
    assert report["uncompressed_bytes"] < 250 * 1024 * 1024
    assert report["dependencies"] == {"numpy": "2.5.2", "openpyxl": "3.1.5", "et-xmlfile": "2.0.0"}
    assert len(report["sha256"]) == 64
    artifact = ROOT / "_work/lambda/crq-lambda-python312-arm64.zip"
    if artifact.exists():
        assert hashlib.sha256(artifact.read_bytes()).hexdigest() == report["sha256"]


def test_terraform_introduces_only_phase3b_resource_types():
    terraform = "\n".join(path.read_text() for path in (ROOT / "infra/phase3b").glob("*.tf"))
    actual = set(re.findall(r'resource\s+"([^"]+)"', terraform))
    assert actual == {
        "aws_iam_role",
        "aws_iam_role_policy",
        "aws_cloudwatch_log_group",
        "aws_lambda_function",
        "aws_apigatewayv2_api",
        "aws_apigatewayv2_integration",
        "aws_apigatewayv2_route",
        "aws_apigatewayv2_stage",
        "aws_lambda_permission",
    }
    for forbidden in ("aws_db_", "aws_cognito_", "aws_sqs_", "aws_sfn_", "aws_ecs_", "aws_secretsmanager_", "aws_vpc"):
        assert forbidden not in terraform
    assert set(re.findall(r'route_key\s*=\s*"([^"]+)"', terraform)) == {
        "GET /health",
        "POST /v1/assessments/run",
    }
    assert set(re.findall(r'"(logs:[A-Za-z]+)"', terraform)) == {
        "logs:CreateLogStream",
        "logs:PutLogEvents",
    }
