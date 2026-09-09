variable "aws_region" {
  description = "Controlled Phase 5A development region."
  type        = string
  default     = "us-east-1"
}

variable "resource_prefix" {
  description = "Prefix applied to Phase 5A development resources."
  type        = string
  default     = "crq-phase5a-dev"
}

variable "lambda_package_path" {
  description = "Reproducible arm64 Lambda ZIP."
  type        = string
}

variable "lambda_package_base64sha256" {
  description = "Base64 SHA-256 from the package report."
  type        = string
}

variable "api_lambda_package_path" {
  description = "Optional API-only package path, allowing an interpretation release without replacing the quantitative worker package."
  type        = string
  default     = null
}

variable "api_lambda_package_base64sha256" {
  description = "Base64 SHA-256 for the optional API-only package."
  type        = string
  default     = null
}

variable "cors_allowed_origins" {
  description = "Explicit development frontend origins."
  type        = list(string)
  default     = ["http://localhost:4173", "http://127.0.0.1:4173"]
}

variable "frontend_callback_urls" {
  description = "Allowed Cognito authorization-code callback URLs."
  type        = list(string)
  default     = ["http://localhost:4173/auth/callback", "http://127.0.0.1:4173/auth/callback"]
}

variable "frontend_logout_urls" {
  description = "Allowed Cognito logout return URLs."
  type        = list(string)
  default     = ["http://localhost:4173/login", "http://127.0.0.1:4173/login"]
}

variable "default_tenant_id" {
  description = "Controlled server-side tenant used only when the dev user lacks a custom tenant claim."
  type        = string
  default     = "crq-dev"
}

variable "log_retention_days" {
  description = "Retention for safe operational logs."
  type        = number
  default     = 30
}

variable "bedrock_model_id" {
  description = "Bedrock model used only for verified Phase 6A Copilot interpretation."
  type        = string
  default     = "amazon.nova-pro-v1:0"
}
