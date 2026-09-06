output "api_endpoint" {
  description = "Unauthenticated Phase 3B endpoint; not production-public-ready."
  value       = aws_apigatewayv2_api.assessment.api_endpoint
}

output "lambda_function_name" {
  value = aws_lambda_function.assessment.function_name
}
