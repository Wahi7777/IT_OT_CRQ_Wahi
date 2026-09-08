import {useEffect, useState} from "react";
import {useNavigate} from "react-router-dom";
import {completeSignIn} from "../auth/CognitoAuth";

export function AuthCallbackPage() {
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { completeSignIn(window.location.search).then(() => navigate("/assessments", {replace: true})).catch((reason) => setError(reason instanceof Error ? reason.message : "Sign-in failed.")); }, [navigate]);
  return <main className="login-page"><section className="login-card glass-panel" aria-live="polite"><span className="overline">Secure workspace</span><h1>{error ? "Sign-in needs attention" : "Completing sign-in"}</h1>{error ? <div className="error-banner" role="alert">{error}</div> : <p><span className="spinner" /> Verifying your Cognito session…</p>}</section></main>;
}
