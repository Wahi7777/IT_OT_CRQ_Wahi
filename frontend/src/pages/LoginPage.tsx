import {ArrowRight, LockKeyhole, ShieldCheck} from "lucide-react";
import {useState} from "react";
import {Link, useSearchParams} from "react-router-dom";
import {Button, GlassPanel} from "../components/ui";
import {signIn} from "../auth/CognitoAuth";

export function LoginPage() {
  const [params] = useSearchParams();
  const [error, setError] = useState<string | null>(null);
  const apiMode = import.meta.env.VITE_CRQ_DATA_MODE === "api";
  async function enter() { try { setError(null); await signIn(); } catch (reason) { setError(reason instanceof Error ? reason.message : "Sign-in could not start."); } }
  return <main className="login-page">
    <div className="login-atmosphere" aria-hidden="true" />
    <section className="login-intro"><div className="brand brand--large"><div className="brand-mark"><ShieldCheck /></div><div><strong>CRQ</strong><span>Quantitative risk intelligence</span></div></div>
      <div className="login-statement"><span className="overline">Governed decision intelligence</span><h1>Make cyber risk<br /><em>financially legible.</em></h1><p>A controlled workspace for IT and operational technology risk quantification—built on approved models, traceable evidence and reproducible results.</p></div>
      <div className="trust-line"><span><ShieldCheck />Model governed</span><span><LockKeyhole />Evidence controlled</span></div>
    </section>
    <GlassPanel className="login-card">
      <div><span className="overline">Workspace access</span><h2>Welcome back</h2><p>{apiMode ? "Continue to the controlled Cognito sign-in flow." : "Demo mode uses approved repository artifacts and transmits no credentials."}</p></div>
      {params.get("expired") && <div className="error-banner" role="alert">Your session expired. Sign in again to continue.</div>}
      {error && <div className="error-banner" role="alert">{error}</div>}
      {apiMode ? <Button className="full-button" onClick={enter}>Sign in securely <ArrowRight /></Button> : <Link to="/assessments"><Button className="full-button">Enter governed workspace <ArrowRight /></Button></Link>}
      <div className="login-notice"><LockKeyhole />{apiMode ? "Authorization code flow with PKCE" : "Approved demo mode"}</div>
    </GlassPanel>
  </main>;
}
