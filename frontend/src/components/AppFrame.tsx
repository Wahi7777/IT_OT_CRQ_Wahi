import {Bell, ChevronDown, LogOut, Search, Shield} from "lucide-react";
import type {ReactNode} from "react";
import {Link, useLocation} from "react-router-dom";
import {signOut} from "../auth/CognitoAuth";

export function AppFrame({children}: {children: ReactNode}) {
  const location = useLocation();
  const inAssessment = location.pathname.includes("/assessments/") && location.pathname !== "/assessments/new";
  return <div className="app-shell">
    <a className="skip-link" href="#main">Skip to main content</a>
    <header className="product-header">
      <Link className="product-brand" to="/assessments"><span className="product-mark"><Shield /></span><strong>CRQ</strong></Link>
      <span className={`workspace-status ${inAssessment ? "is-active" : ""}`}><i />{inAssessment ? "In progress" : "Risk workspace"}</span>
      <div className="header-actions"><button className="header-icon" aria-label="Search"><Search /></button><button className="header-icon notification-button" aria-label="Notifications"><Bell /><i /></button><button className="profile-menu" type="button"><span>SS</span><span><strong>Sid Sharma</strong><small>Executive</small></span><ChevronDown /></button><button className="header-icon signout-button" onClick={signOut} aria-label="Sign out"><LogOut /></button></div>
    </header>
    <main id="main" className="page-content">{children}</main>
  </div>;
}
