variable "aws_region" {
  description = "AWS region for the Phase 3B endpoint."
  type        = string
  default     = "eu-west-1"
}

variable "function_name" {
  description = "Lambda function and log group base name."
  type        = string
  default     = "crq-assessment-v1"
}

variable "lambda_package_path" {
  description = "Path to the reproducible arm64 ZIP produced by scripts/build_lambda_package.py."
  type        = string
}

variable "lambda_package_base64sha256" {
  description = "Base64 SHA-256 from the package build report."
  type        = string
}

variable "cors_allowed_origins" {
  description = "Explicit development frontend origins; authentication is not present in Phase 3B."
  type        = list(string)
  default     = ["http://localhost:3000"]
}

variable "log_retention_days" {
  description = "Retention for safe operational Lambda logs."
  type        = number
  default     = 30
}
