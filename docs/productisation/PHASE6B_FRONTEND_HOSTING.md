# Phase 6B — Controlled frontend hosting

## Status

Phase 6B adds only an AWS Amplify Hosting layer to the existing Phase 5A/6A stack. The quantitative engines, contracts, assessment workflow, frontend design, Cognito authentication model, API/Lambda/SQS/worker path, and S3 persistence remain unchanged.

The controlled dev application is hosted at:

**https://main.d2226knnvh46il.amplifyapp.com**

## Hosting decision

AWS Amplify Hosting is used because it supplies a stable managed HTTPS URL and SPA routing without a public S3 website or a separately managed CloudFront distribution. The Amplify app is not repository-connected: connecting GitHub would require a repository access token that is not part of the existing controlled infrastructure. A checked-in deployment script instead builds the committed `main` source and uploads one immutable production artifact through Amplify's deployment API.

## Architecture and runtime configuration

The hosted flow remains:

`Browser → Amplify Hosting → Cognito → API Gateway → API Lambda → SQS → Worker Lambda → CRQ engine → S3`

The Amplify `main` branch records these non-secret build/runtime values:

- `VITE_CRQ_DATA_MODE=api`
- `VITE_CRQ_API_BASE_URL`
- `VITE_COGNITO_DOMAIN`
- `VITE_COGNITO_CLIENT_ID`
- `VITE_COGNITO_REDIRECT_URI`
- `VITE_COGNITO_LOGOUT_URI`

The deployment script passes the same values to Vite at build time from Terraform outputs. Cognito client IDs and hosted origins are public application configuration, not credentials. No access token, password, AWS key, or client secret is embedded in the frontend.

## Authentication and CORS

The Cognito app client retains authorization-code flow with PKCE and no client secret. Terraform adds the exact Amplify HTTPS callback and logout URLs while preserving the two localhost development origins. API Gateway CORS similarly permits only the exact Amplify origin and the existing localhost origins; authenticated routes never use a wildcard origin. Public self-registration remains disabled through `allow_admin_create_user_only = true`.

## SPA navigation

Amplify rewrites extensionless client routes to `/index.html` with HTTP 200 while leaving static file extensions such as `.js` and `.css` untouched. Direct navigation and browser refresh therefore return the React application for `/assessments`, assessment routes, run routes, results routes, and `/auth/callback`, while application assets retain their correct content types.

## Deployment and rollback

- Source: the checked-out, clean `main` branch synchronized with `origin/main`.
- Build command: `npm run build` under `frontend/` with Terraform-derived production variables.
- Output directory: `frontend/dist`.
- Trigger: `AWS_PROFILE=aiengineer AWS_REGION=us-east-1 ./scripts/deploy_phase6b_frontend.sh`.
- Redeployment: rerun the same command from a clean desired commit; built files are never edited manually.
- Rollback: check out the known-good commit, run the same script, and verify the resulting Amplify job succeeds.

## Adding a colleague

An authorized operator provisions each colleague manually; there is no public signup:

```bash
AWS_PROFILE=aiengineer AWS_REGION=us-east-1 aws cognito-idp admin-create-user \
  --user-pool-id "$(terraform -chdir=infra/phase5a output -raw cognito_user_pool_id)" \
  --username colleague@example.com \
  --user-attributes Name=email,Value=colleague@example.com Name=email_verified,Value=true Name=custom:tenant_id,Value=crq-dev \
  --desired-delivery-mediums EMAIL
```

The colleague follows the temporary-password invitation and signs in at the hosted URL. Access should be removed with `admin-disable-user` when no longer required. Only approved internal-pilot data may be entered.

## Cost expectation

Amplify Hosting has no continuously running instance for this static application. At current public pricing, storage beyond the included allowance is $0.023/GB-month and data transfer beyond the included allowance is $0.15/GB; the first 5 GB stored and 15 GB served each month are included. This 3.3 MB application and a small internal pilot should therefore remain approximately $0/month for frontend hosting while inside those allowances. The local-build/manual-upload process consumes no Amplify build minutes. Backend dev resources retain their existing independent costs.

## Validation outcome

- HTTPS root and direct SPA routes returned the deployed React entry point with HTTP 200.
- A post-deployment defect was corrected after Safari exposed a blank page: the original catch-all SPA rule also rewrote `.js` and `.css` requests to `index.html`. The rule now excludes static asset extensions; the deployed JavaScript and stylesheet return their correct content types, and Amplify deployment job 2 completed with five successful verification screenshots.
- Cognito issued a token for an ephemeral invite-only test identity; unauthenticated API access returned HTTP 401; the identity was removed after validation.
- IT Financial Services and OT Power Generation assessments were created, reloaded, submitted, observed through asynchronous states, completed, and retrieved through the real AWS API.
- The prudent headline summaries returned by both hosted-path runs matched their approved contract examples exactly.
- Overview and Attack Paths Copilot requests returned HTTP 200 with `VERIFIED` responses from the deployed Phase 6A baseline.
- S3 public access remains blocked on all four controls.
- Frontend tests, TypeScript, lint, production build, dependency audit, Terraform validation, and the full Python suite passed.
- The hosted page was loaded successfully in the Codex in-app browser at laptop width. Direct automation of installed Chrome and Safari was unavailable in this execution environment, so those two named-browser visual checks remain a manual acceptance item rather than an application blocker.
