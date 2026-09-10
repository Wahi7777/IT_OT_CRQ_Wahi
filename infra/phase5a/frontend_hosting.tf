resource "aws_amplify_app" "frontend" {
  name                     = "${var.resource_prefix}-frontend"
  description              = "Phase 6B controlled internal-pilot frontend"
  platform                 = "WEB"
  enable_branch_auto_build = false

  custom_rule {
    source = "</^[^.]+$|\\.(?!(css|gif|ico|jpg|jpeg|js|map|png|svg|ttf|txt|webp|woff|woff2)$)([^.]+$)/>"
    target = "/index.html"
    status = "200"
  }

  tags = {
    Environment = "dev"
    Phase       = "6B"
    Product     = "CRQ"
  }
}

resource "aws_amplify_branch" "frontend" {
  app_id                  = aws_amplify_app.frontend.id
  branch_name             = var.frontend_branch_name
  description             = "Controlled dev deployment from origin/main"
  display_name            = var.frontend_branch_name
  enable_auto_build       = false
  enable_basic_auth       = false
  enable_performance_mode = false
  framework               = "React"
  stage                   = "DEVELOPMENT"

  environment_variables = {
    VITE_CRQ_DATA_MODE        = "api"
    VITE_CRQ_API_BASE_URL     = aws_apigatewayv2_api.product.api_endpoint
    VITE_COGNITO_DOMAIN       = "https://${aws_cognito_user_pool_domain.frontend.domain}.auth.${var.aws_region}.amazoncognito.com"
    VITE_COGNITO_CLIENT_ID    = aws_cognito_user_pool_client.frontend.id
    VITE_COGNITO_REDIRECT_URI = "${local.hosted_frontend_origin}/auth/callback"
    VITE_COGNITO_LOGOUT_URI   = "${local.hosted_frontend_origin}/login"
  }

  tags = {
    Environment = "dev"
    Phase       = "6B"
    Product     = "CRQ"
  }
}
