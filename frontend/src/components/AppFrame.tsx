import {BarChart3, Blocks, ChevronDown, FileCheck2, Gauge, LayoutDashboard, LogOut, Menu, Settings2, Shield, X} from "lucide-react";
import {useState, type ReactNode} from "react";
import {NavLink, useLocation} from "react-router-dom";
import {useAssessment} from "../features/assessment/AssessmentContext";
import {Badge, Button} from "./ui";
import {signOut} from "../auth/CognitoAuth";

export function AppFrame({children}: {children: ReactNode}) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const {dataMode, setDataMode} = useAssessment();
  const location = useLocation();
  const inResults = location.pathname.startsWith("/results");

  return <div className="app-frame">
    <a className="skip-link" href="#main">Skip to main content</a>
    <aside className={`sidebar ${mobileOpen ? "is-open" : ""}`} aria-label="Primary navigation">
      <div className="brand"><div className="brand-mark"><Shield size={21} /></div><div><strong>CRQ</strong><span>Risk quantification</span></div></div>
      <button className="mobile-close" onClick={() => setMobileOpen(false)} aria-label="Close navigation"><X /></button>
      <nav>
        <NavLink to="/assessments"><LayoutDashboard />Assessments</NavLink>
        <NavLink to="/assessments/new"><Blocks />New assessment</NavLink>
        <NavLink to="/assessments/demo/setup"><FileCheck2 />Assessment workspace</NavLink>
        <NavLink to="/results/demo/overview" className={inResults ? "active" : ""}><BarChart3 />Results</NavLink>
      </nav>
      <div className="sidebar-spacer" />
      <div className="governance-card">
        <div className="governance-icon"><Gauge size={17} /></div>
        <div><span>Model governance</span><strong>Controls active</strong></div>
        <Badge tone="green">Locked</Badge>
      </div>
      <nav className="sidebar-bottom"><a href="#settings"><Settings2 />Workspace settings</a><button type="button" onClick={signOut}><LogOut />Sign out</button></nav>
    </aside>
    {mobileOpen && <button className="nav-scrim" aria-label="Close navigation" onClick={() => setMobileOpen(false)} />}
    <div className="main-column">
      <header className="topbar">
        <button className="mobile-menu" onClick={() => setMobileOpen(true)} aria-label="Open navigation"><Menu /></button>
        <div className="environment"><span className={`status-dot ${dataMode === "demo" ? "status-dot--amber" : "status-dot--green"}`} />{dataMode === "demo" ? "Approved demo data" : "Contract API"}</div>
        <div className="topbar-actions">
          <label className="mode-switch">Data mode<span className="select-wrap"><select value={dataMode} onChange={(event) => setDataMode(event.target.value as "demo" | "api")} aria-label="Data mode"><option value="demo">Demo</option><option value="api">Real API</option></select><ChevronDown size={14} /></span></label>
          <Button variant="ghost" className="avatar" aria-label="Open user menu">SW</Button>
        </div>
      </header>
      <main id="main" className="page-content">{children}</main>
    </div>
  </div>;
}
