import {ArrowRight, Clock3, Factory, FilePlus2, Landmark, MoreHorizontal, RefreshCw, Search} from "lucide-react";
import {Link} from "react-router-dom";
import {PageHeader} from "../components/PageHeader";
import {Badge, Button, GlassPanel} from "../components/ui";
import {approvedRequests, approvedResults, outputMappings} from "../contracts/governedData";

const items = [
  {name: "Financial Services · Group", domain: "IT", icon: Landmark, status: "Completed", tone: "green" as const, updated: "Approved baseline", result: approvedResults.IT, currency: approvedRequests.IT.assessment.assessment.currency, href: "/results/demo/overview"},
  {name: "Power Generation · Facility 01", domain: "OT", icon: Factory, status: "Ready to review", tone: "amber" as const, updated: "Approved baseline", result: approvedResults.OT, currency: approvedRequests.OT.assessment.assessment.currency, href: "/assessments/demo/setup?domain=OT"}
];

export function DashboardPage() {
  return <>
    <PageHeader title="Assessment portfolio" description="Governed risk assessments, readiness and current results." actions={<Link to="/assessments/new"><Button><FilePlus2 />New assessment</Button></Link>} />
    <div className="portfolio-strip">
      <GlassPanel><span>Approved examples</span><strong>{items.length}</strong><small>IT and OT contract artifacts</small></GlassPanel>
      <GlassPanel><span>Simulation scale</span><strong>{Number(approvedResults.IT.run.simulation_count).toLocaleString()}</strong><small>Trials per approved result</small></GlassPanel>
      <GlassPanel><span>Canonical coverage</span><strong>{outputMappings.length}</strong><small>Mapped result families</small></GlassPanel>
      <GlassPanel><span>Governance status</span><strong className="green-text">Current</strong><small>Approved model bundles</small></GlassPanel>
    </div>
    <GlassPanel className="table-panel">
      <div className="table-toolbar"><div><h2>Assessments</h2><p>Results shown from repository-approved artifacts.</p></div><label className="search"><Search /><span className="sr-only">Search assessments</span><input placeholder="Search assessments" /></label></div>
      <div className="assessment-list" role="list">
        {items.map(({name, domain, icon: Icon, status, tone, updated, result, currency, href}) => <article className="assessment-row" role="listitem" key={name}>
          <div className={`assessment-domain assessment-domain--${domain.toLowerCase()}`}><Icon /></div>
          <div className="assessment-name"><strong>{name}</strong><span>{domain} · {result.provenance.sector_pack_id}</span></div>
          <div className="assessment-meta"><span>Status</span><Badge tone={tone}>{status}</Badge></div>
          <div className="assessment-meta"><span>Prudent AAL</span><strong>{money(result.summary.prudent.aal, currency)}</strong></div>
          <div className="assessment-meta"><span>Updated</span><small><Clock3 />{updated}</small></div>
          <Link className="row-link" to={href} aria-label={`Open ${name}`}><ArrowRight /></Link>
          <button className="icon-button" aria-label={`More actions for ${name}`}><MoreHorizontal /></button>
        </article>)}
      </div>
      <div className="table-footer"><span><RefreshCw />Demo data is pinned to approved examples</span><span>{items.length} assessments</span></div>
    </GlassPanel>
  </>;
}

function money(value: number, currency?: string | null) {
  return currency ? new Intl.NumberFormat("en-AE", {style: "currency", currency, notation: "compact", maximumFractionDigits: 2}).format(value) : `${new Intl.NumberFormat("en-AE", {notation: "compact", maximumFractionDigits: 2}).format(value)} units`;
}
