type TokenResponse = {access_token: string; id_token: string; expires_in: number; token_type: string};

export interface AuthSession {
  idToken: string;
  accessToken: string;
  expiresAt: number;
  claims: Record<string, unknown>;
}

let session: AuthSession | null = null;
const listeners = new Set<() => void>();

function config() {
  return {
    domain: import.meta.env.VITE_COGNITO_DOMAIN?.replace(/\/$/, "") ?? "",
    clientId: import.meta.env.VITE_COGNITO_CLIENT_ID ?? "",
    redirectUri: import.meta.env.VITE_COGNITO_REDIRECT_URI ?? `${window.location.origin}/auth/callback`,
    logoutUri: import.meta.env.VITE_COGNITO_LOGOUT_URI ?? `${window.location.origin}/login`
  };
}

function emit() { listeners.forEach((listener) => listener()); }
function base64Url(bytes: Uint8Array) {
  return btoa(String.fromCharCode(...bytes)).replaceAll("+", "-").replaceAll("/", "_").replace(/=+$/, "");
}
async function sha256(value: string) {
  return base64Url(new Uint8Array(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(value))));
}
function decodeClaims(token: string): Record<string, unknown> {
  try { return JSON.parse(atob(token.split(".")[1].replaceAll("-", "+").replaceAll("_", "/"))); }
  catch { return {}; }
}

export function authConfigured() {
  const current = config();
  return Boolean(current.domain && current.clientId);
}

export async function signIn() {
  const current = config();
  if (!authConfigured()) throw new Error("Cognito is not configured for this environment.");
  const verifier = base64Url(crypto.getRandomValues(new Uint8Array(48)));
  const state = base64Url(crypto.getRandomValues(new Uint8Array(24)));
  sessionStorage.setItem("crq.pkce", JSON.stringify({verifier, state}));
  const query = new URLSearchParams({client_id: current.clientId, response_type: "code", scope: "openid email", redirect_uri: current.redirectUri, state, code_challenge_method: "S256", code_challenge: await sha256(verifier)});
  window.location.assign(`${current.domain}/oauth2/authorize?${query}`);
}

export async function completeSignIn(search: string) {
  const current = config();
  const params = new URLSearchParams(search);
  const saved = JSON.parse(sessionStorage.getItem("crq.pkce") ?? "null") as {verifier: string; state: string} | null;
  if (!saved || params.get("state") !== saved.state || !params.get("code")) throw new Error("The sign-in response could not be verified.");
  const response = await fetch(`${current.domain}/oauth2/token`, {method: "POST", headers: {"Content-Type": "application/x-www-form-urlencoded"}, body: new URLSearchParams({grant_type: "authorization_code", client_id: current.clientId, code: params.get("code")!, redirect_uri: current.redirectUri, code_verifier: saved.verifier})});
  if (!response.ok) throw new Error("Cognito did not issue a valid session.");
  const tokens = await response.json() as TokenResponse;
  sessionStorage.removeItem("crq.pkce");
  session = {idToken: tokens.id_token, accessToken: tokens.access_token, expiresAt: Date.now() + tokens.expires_in * 1000, claims: decodeClaims(tokens.id_token)};
  emit();
}

export function getIdToken() {
  if (!session || session.expiresAt <= Date.now() + 5_000) { clearSession(); return null; }
  return session.idToken;
}
export function getSession() { getIdToken(); return session; }
export function clearSession() { if (session) { session = null; emit(); } }
export function subscribeAuth(listener: () => void) { listeners.add(listener); return () => listeners.delete(listener); }
export function signOut() {
  clearSession();
  const current = config();
  if (!authConfigured()) { window.location.assign("/login"); return; }
  const query = new URLSearchParams({client_id: current.clientId, logout_uri: current.logoutUri});
  window.location.assign(`${current.domain}/logout?${query}`);
}
