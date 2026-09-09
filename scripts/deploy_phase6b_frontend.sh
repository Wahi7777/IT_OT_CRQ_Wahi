#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
terraform_dir="${repo_root}/infra/phase5a"
frontend_dir="${repo_root}/frontend"
deployment_dir="$(mktemp -d)"
trap 'rm -rf "${deployment_dir}"' EXIT

terraform_output="$(terraform -chdir="${terraform_dir}" output -json)"
api_base_url="$(jq -r '.api_endpoint.value' <<<"${terraform_output}")"
cognito_domain="$(jq -r '.cognito_domain.value' <<<"${terraform_output}")"
cognito_client_id="$(jq -r '.cognito_user_pool_client_id.value' <<<"${terraform_output}")"
frontend_url="$(jq -r '.frontend_url.value' <<<"${terraform_output}")"
amplify_app_id="$(jq -r '.frontend_amplify_app_id.value' <<<"${terraform_output}")"
amplify_branch="$(jq -r '.frontend_amplify_branch.value' <<<"${terraform_output}")"

(
  cd "${frontend_dir}"
  VITE_CRQ_DATA_MODE=api \
  VITE_CRQ_API_BASE_URL="${api_base_url}" \
  VITE_COGNITO_DOMAIN="${cognito_domain}" \
  VITE_COGNITO_CLIENT_ID="${cognito_client_id}" \
  VITE_COGNITO_REDIRECT_URI="${frontend_url}/auth/callback" \
  VITE_COGNITO_LOGOUT_URI="${frontend_url}/login" \
  npm run build
  cd dist
  zip -qr "${deployment_dir}/frontend.zip" .
)

deployment="$(AWS_PROFILE="${AWS_PROFILE:-aiengineer}" AWS_REGION="${AWS_REGION:-us-east-1}" \
  aws amplify create-deployment --app-id "${amplify_app_id}" --branch-name "${amplify_branch}")"
job_id="$(jq -r '.jobId' <<<"${deployment}")"
upload_url="$(jq -r '.zipUploadUrl' <<<"${deployment}")"
curl --fail --silent --show-error -T "${deployment_dir}/frontend.zip" "${upload_url}" >/dev/null

AWS_PROFILE="${AWS_PROFILE:-aiengineer}" AWS_REGION="${AWS_REGION:-us-east-1}" \
  aws amplify start-deployment --app-id "${amplify_app_id}" --branch-name "${amplify_branch}" --job-id "${job_id}" >/dev/null

for _ in $(seq 1 60); do
  status="$(AWS_PROFILE="${AWS_PROFILE:-aiengineer}" AWS_REGION="${AWS_REGION:-us-east-1}" \
    aws amplify get-job --app-id "${amplify_app_id}" --branch-name "${amplify_branch}" --job-id "${job_id}" \
    --query 'job.summary.status' --output text)"
  case "${status}" in
    SUCCEED)
      printf '%s\n' "Deployment ${job_id} succeeded: ${frontend_url}"
      exit 0
      ;;
    FAILED|CANCELLED)
      printf '%s\n' "Deployment ${job_id} ended with status ${status}" >&2
      exit 1
      ;;
  esac
  sleep 5
done

printf '%s\n' "Deployment ${job_id} did not complete within five minutes." >&2
exit 1
