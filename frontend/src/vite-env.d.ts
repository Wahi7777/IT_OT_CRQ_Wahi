/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_CRQ_DATA_MODE?: "demo" | "api";
  readonly VITE_CRQ_API_BASE_URL?: string;
  readonly VITE_COGNITO_DOMAIN?: string;
  readonly VITE_COGNITO_CLIENT_ID?: string;
  readonly VITE_COGNITO_REDIRECT_URI?: string;
  readonly VITE_COGNITO_LOGOUT_URI?: string;
}
