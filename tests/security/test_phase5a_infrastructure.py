from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MAIN = (ROOT / "infra/phase5a/main.tf").read_text()


def test_phase5a_has_no_out_of_scope_state_or_orchestration():
    lowered = MAIN.lower()
    for forbidden in ("aws_db_instance", "aws_rds_", "aws_dynamodb_", "aws_sfn_", "aws_ecs_", "aws_wafv2_"):
        assert forbidden not in lowered


def test_s3_is_private_encrypted_versioned_and_tls_only():
    for required in (
        "block_public_acls       = true",
        "block_public_policy     = true",
        "ignore_public_acls      = true",
        "restrict_public_buckets = true",
        'sse_algorithm = "AES256"',
        'status = "Enabled"',
        'sid     = "DenyInsecureTransport"',
    ):
        assert required in MAIN


def test_queue_contract_is_single_record_zero_window_with_dlq():
    for required in ("batch_size                         = 1", "maximum_batching_window_in_seconds = 0", "maxReceiveCount     = 3", "aws_sqs_queue.dead_letter.arn"):
        assert required in MAIN


def test_only_health_is_unauthenticated():
    protected = MAIN.split('resource "aws_apigatewayv2_route" "protected"', 1)[1].split("}\n", 1)[0]
    assert "for_each" in protected
    assert 'authorization_type = "JWT"' in protected
    for route in ("POST /v1/assessments", "GET /v1/assessments/{assessment_id}", "POST /v1/assessments/{assessment_id}/run", "GET /v1/runs/{run_id}", "GET /v1/runs/{run_id}/result"):
        assert route in MAIN
    health = MAIN.split('resource "aws_apigatewayv2_route" "health"', 1)[1].split("}\n", 1)[0]
    assert "authorization_type" not in health


def test_lambda_roles_are_resource_scoped():
    assert 'resources = ["${aws_s3_bucket.product.arn}/assessments/*", "${aws_s3_bucket.product.arn}/runs/*"]' in MAIN
    assert "aws_sqs_queue.jobs.arn" in MAIN
    assert 'resources = ["*"]' not in MAIN
