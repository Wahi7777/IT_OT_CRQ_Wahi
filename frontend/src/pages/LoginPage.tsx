import {ArrowRight, LockKeyhole, ShieldCheck} from "lucide-react";
import {Link} from "react-router-dom";
import {Button, GlassPanel} from "../components/ui";

export function LoginPage() {
  return <main className="login-page">
    <div className="login-atmosphere" aria-hidden="true" />
    <section className="login-intro"><div className="brand brand--large"><div className="brand-mark"><ShieldCheck /></div><div><strong>CRQ</strong><span>Quantitative risk intelligence</span></div></div>
      <div className="login-statement"><span className="overline">Governed decision intelligence</span><h1>Make cyber risk<br /><em>financially legible.</em></h1><p>A controlled workspace for IT and operational technology risk quantification—built on approved models, traceable evidence and reproducible results.</p></div>
      <div className="trust-line"><span><ShieldCheck />Model governed</span><span><LockKeyhole />Evidence controlled</span></div>
    </section>
    <GlassPanel className="login-card">
      <div><span className="overline">Workspace access</span><h2>Welcome back</h2><p>Sign-in is a Phase 4B placeholder. Cognito integration remains intentionally deferred.</p></div>
      <label>Email address<input type="email" value="risk.lead@example.com" readOnly /></label>
      <label>Password<input type="password" value="governed-demo" readOnly /></label>
      <Link to="/assessments"><Button className="full-button">Enter governed workspace <ArrowRight /></Button></Link>
      <div className="login-notice"><LockKeyhole />Demo shell only · no credentials are transmitted</div>
    </GlassPanel>
  </main>;
}
