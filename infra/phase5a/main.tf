data "aws_caller_identity" "current" {}

locals {
  bucket_name = "${var.resource_prefix}-${data.aws_caller_identity.current.account_id}-${var.aws_region}"
}

data "aws_iam_policy_document" "lambda_assume" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_s3_bucket" "product" {
  bucket        = local.bucket_name
  force_destroy = true
}

resource "aws_s3_bucket_public_access_block" "product" {
  bucket                  = aws_s3_bucket.product.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_ownership_controls" "product" {
  bucket = aws_s3_bucket.product.id
  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "product" {
  bucket = aws_s3_bucket.product.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_versioning" "product" {
  bucket = aws_s3_bucket.product.id
  versioning_configuration {
    status = "Enabled"
  }
}

data "aws_iam_policy_document" "product_bucket" {
  statement {
    sid     = "DenyInsecureTransport"
    effect  = "Deny"
    actions = ["s3:*"]
    resources = [
      aws_s3_bucket.product.arn,
      "${aws_s3_bucket.product.arn}/*",
    ]
    principals {
      type        = "*"
      identifiers = ["*"]
    }
    condition {
      test     = "Bool"
      variable = "aws:SecureTransport"
      values   = ["false"]
    }
  }
}

resource "aws_s3_bucket_policy" "product" {
  bucket     = aws_s3_bucket.product.id
  policy     = data.aws_iam_policy_document.product_bucket.json
  depends_on = [aws_s3_bucket_public_access_block.product]
}

resource "aws_sqs_queue" "dead_letter" {
  name                      = "${var.resource_prefix}-dlq"
  sqs_managed_sse_enabled   = true
  message_retention_seconds = 1209600
}

resource "aws_sqs_queue" "jobs" {
  name                       = "${var.resource_prefix}-jobs"
  sqs_managed_sse_enabled    = true
  visibility_timeout_seconds = 960
  receive_wait_time_seconds  = 20
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dead_letter.arn
    maxReceiveCount     = 3
  })
}

resource "aws_cognito_user_pool" "users" {
  name                     = "${var.resource_prefix}-users"
  username_attributes      = ["email"]
  auto_verified_attributes = ["email"]
  mfa_configuration        = "OFF"
  deletion_protection      = "INACTIVE"

  admin_create_user_config {
    allow_admin_create_user_only = true
  }

  password_policy {
    minimum_length                   = 12
    require_lowercase                = true
    require_numbers                  = true
    require_symbols                  = true
    require_uppercase                = true
    temporary_password_validity_days = 7
  }

  schema {
    attribute_data_type = "String"
    mutable             = true
    name                = "tenant_id"
    required            = false
    string_attribute_constraints {
      min_length = 1
      max_length = 64
    }
  }
}

resource "aws_cognito_user_pool_client" "frontend" {
  name                                 = "${var.resource_prefix}-react"
  user_pool_id                         = aws_cognito_user_pool.users.id
  generate_secret                      = false
  prevent_user_existence_errors        = "ENABLED"
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_flows                  = ["code"]
  allowed_oauth_scopes                 = ["openid", "email", "profile"]
  callback_urls                        = var.frontend_callback_urls
  logout_urls                          = var.frontend_logout_urls
  supported_identity_providers         = ["COGNITO"]
  explicit_auth_flows                  = ["ALLOW_USER_PASSWORD_AUTH", "ALLOW_REFRESH_TOKEN_AUTH"]
  access_token_validity                = 60
  id_token_validity                    = 60
  refresh_token_validity               = 1

  token_validity_units {
    access_token  = "minutes"
    id_token      = "minutes"
    refresh_token = "days"
  }
}

resource "aws_cognito_user_pool_domain" "frontend" {
  domain       = "${var.resource_prefix}-${data.aws_caller_identity.current.account_id}"
  user_pool_id = aws_cognito_user_pool.users.id
}

resource "aws_iam_role" "api" {
  name               = "${var.resource_prefix}-api-execution"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
}

resource "aws_iam_role" "worker" {
  name               = "${var.resource_prefix}-worker-execution"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
}

resource "aws_cloudwatch_log_group" "api" {
  name              = "/aws/lambda/${var.resource_prefix}-api"
  retention_in_days = var.log_retention_days
}

resource "aws_cloudwatch_log_group" "worker" {
  name              = "/aws/lambda/${var.resource_prefix}-worker"
  retention_in_days = var.log_retention_days
}

data "aws_iam_policy_document" "api" {
  statement {
    sid       = "ProductObjects"
    effect    = "Allow"
    actions   = ["s3:GetObject", "s3:PutObject"]
    resources = ["${aws_s3_bucket.product.arn}/assessments/*", "${aws_s3_bucket.product.arn}/runs/*"]
  }
  statement {
    sid       = "SendJobs"
    effect    = "Allow"
    actions   = ["sqs:SendMessage"]
    resources = [aws_sqs_queue.jobs.arn]
  }
  statement {
    sid       = "WriteLogs"
    effect    = "Allow"
    actions   = ["logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["${aws_cloudwatch_log_group.api.arn}:*"]
  }
}

data "aws_iam_policy_document" "worker" {
  statement {
    sid       = "ProductObjects"
    effect    = "Allow"
    actions   = ["s3:GetObject", "s3:PutObject"]
    resources = ["${aws_s3_bucket.product.arn}/assessments/*", "${aws_s3_bucket.product.arn}/runs/*"]
  }
  statement {
    sid       = "ConsumeJobs"
    effect    = "Allow"
    actions   = ["sqs:ReceiveMessage", "sqs:DeleteMessage", "sqs:GetQueueAttributes"]
    resources = [aws_sqs_queue.jobs.arn]
  }
  statement {
    sid       = "WriteLogs"
    effect    = "Allow"
    actions   = ["logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["${aws_cloudwatch_log_group.worker.arn}:*"]
  }
}

resource "aws_iam_role_policy" "api" {
  name   = "phase5a-minimum"
  role   = aws_iam_role.api.id
  policy = data.aws_iam_policy_document.api.json
}

resource "aws_iam_role_policy" "worker" {
  name   = "phase5a-minimum"
  role   = aws_iam_role.worker.id
  policy = data.aws_iam_policy_document.worker.json
}

resource "aws_lambda_function" "api" {
  function_name    = "${var.resource_prefix}-api"
  description      = "Phase 5A authenticated API and persistence boundary"
  role             = aws_iam_role.api.arn
  runtime          = "python3.12"
  architectures    = ["arm64"]
  handler          = "crq.product.api_lambda.handler"
  filename         = var.lambda_package_path
  source_code_hash = var.lambda_package_base64sha256
  memory_size      = 1024
  timeout          = 30
  environment {
    variables = {
      PYTHONPATH            = "/var/task/src"
      CRQ_BUCKET            = aws_s3_bucket.product.id
      CRQ_QUEUE_URL         = aws_sqs_queue.jobs.id
      CRQ_DEFAULT_TENANT_ID = var.default_tenant_id
    }
  }
  depends_on = [aws_cloudwatch_log_group.api, aws_iam_role_policy.api]
}

resource "aws_lambda_function" "worker" {
  function_name    = "${var.resource_prefix}-worker"
  description      = "Phase 5A SQS worker over the governed CRQ application service"
  role             = aws_iam_role.worker.arn
  runtime          = "python3.12"
  architectures    = ["arm64"]
  handler          = "crq.product.worker_lambda.handler"
  filename         = var.lambda_package_path
  source_code_hash = var.lambda_package_base64sha256
  memory_size      = 2048
  timeout          = 900
  ephemeral_storage { size = 2048 }
  environment {
    variables = {
      PYTHONPATH = "/var/task/src"
      TMPDIR     = "/tmp"
      CRQ_BUCKET = aws_s3_bucket.product.id
    }
  }
  depends_on = [aws_cloudwatch_log_group.worker, aws_iam_role_policy.worker]
}

resource "aws_lambda_event_source_mapping" "worker" {
  event_source_arn                   = aws_sqs_queue.jobs.arn
  function_name                      = aws_lambda_function.worker.arn
  batch_size                         = 1
  maximum_batching_window_in_seconds = 0
  function_response_types            = ["ReportBatchItemFailures"]
}

resource "aws_apigatewayv2_api" "product" {
  name          = "${var.resource_prefix}-http"
  protocol_type = "HTTP"
  cors_configuration {
    allow_headers = ["authorization", "content-type", "idempotency-key"]
    allow_methods = ["GET", "POST", "OPTIONS"]
    allow_origins = var.cors_allowed_origins
    max_age       = 300
  }
}

resource "aws_apigatewayv2_authorizer" "jwt" {
  api_id           = aws_apigatewayv2_api.product.id
  authorizer_type  = "JWT"
  identity_sources = ["$request.header.Authorization"]
  name             = "${var.resource_prefix}-cognito"
  jwt_configuration {
    audience = [aws_cognito_user_pool_client.frontend.id]
    issuer   = "https://${aws_cognito_user_pool.users.endpoint}"
  }
}

resource "aws_apigatewayv2_integration" "api" {
  api_id                 = aws_apigatewayv2_api.product.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.api.invoke_arn
  payload_format_version = "2.0"
  timeout_milliseconds   = 30000
}

locals {
  protected_routes = toset([
    "POST /v1/assessments",
    "GET /v1/assessments/{assessment_id}",
    "POST /v1/assessments/{assessment_id}/run",
    "GET /v1/runs/{run_id}",
    "GET /v1/runs/{run_id}/result",
  ])
}

resource "aws_apigatewayv2_route" "health" {
  api_id    = aws_apigatewayv2_api.product.id
  route_key = "GET /health"
  target    = "integrations/${aws_apigatewayv2_integration.api.id}"
}

resource "aws_apigatewayv2_route" "protected" {
  for_each           = local.protected_routes
  api_id             = aws_apigatewayv2_api.product.id
  route_key          = each.value
  target             = "integrations/${aws_apigatewayv2_integration.api.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.jwt.id
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.product.id
  name        = "$default"
  auto_deploy = true
}

resource "aws_lambda_permission" "api_gateway" {
  statement_id  = "AllowPhase5aHttpApiInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.api.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.product.execution_arn}/*/*"
}
