import {afterEach, describe, expect, it, vi} from "vitest";
import {clearSession, completeSignIn, getIdToken} from "../auth/CognitoAuth";

describe("Cognito PKCE session", () => {
  afterEach(() => { clearSession(); sessionStorage.clear(); vi.restoreAllMocks(); });

  it("rejects a callback whose state does not match the browser-held verifier", async () => {
    sessionStorage.setItem("crq.pkce", JSON.stringify({state: "trusted-state", verifier: "verifier"}));
    await expect(completeSignIn("?code=code&state=attacker-state")).rejects.toThrow(/could not be verified/i);
    expect(getIdToken()).toBeNull();
  });

  it("keeps issued tokens in memory and returns the ID token for API authorization", async () => {
    sessionStorage.setItem("crq.pkce", JSON.stringify({state: "trusted-state", verifier: "verifier"}));
    const payload = btoa(JSON.stringify({sub: "user-a", "custom:tenant_id": "tenant-a"})).replaceAll("=", "");
    const idToken = `header.${payload}.signature`;
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({id_token: idToken, access_token: "access", expires_in: 3600, token_type: "Bearer"}), {status: 200}));
    await completeSignIn("?code=authorization-code&state=trusted-state");
    expect(getIdToken()).toBe(idToken);
    expect(sessionStorage.getItem("crq.pkce")).toBeNull();
    expect(sessionStorage.getItem("crq.token")).toBeNull();
  });
});
