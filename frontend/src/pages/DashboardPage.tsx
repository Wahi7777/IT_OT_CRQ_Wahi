import {ArrowRight, Building2, Factory, FilePlus2, Landmark, Search} from "lucide-react";
import {Link} from "react-router-dom";
import {PageHeader} from "../components/PageHeader";
import {Badge, Button, GlassPanel} from "../components/ui";

const assessments = [
  {name: "Financial Services Group", scope: "Enterprise technology", domain: "IT", icon: Landmark, status: "Complete", progress: 100, action: "View results", href: "/results/demo/overview", tone: "green" as const},
  {name: "Power Generation · Facility 01", scope: "Critical production environment", domain: "OT", icon: Factory, status: "In progress", progress: 68, action: "Continue", href: "/assessments/demo/ot-architecture-topology?domain=OT", tone: "indigo" as const}
];

export function DashboardPage() {
  return <div className="portfolio-page">
    <PageHeader eyebrow="Risk workspace" title="Your assessments" description="Continue an assessment or review completed cyber risk results." actions={<Link to="/assessments/new"><Button><FilePlus2 />New assessment</Button></Link>} />
    <div className="portfolio-overview"><GlassPanel><span className="overview-icon"><Building2 /></span><div><strong>2</strong><span>Active assessments</span></div></GlassPanel><GlassPanel><strong>1</strong><span>Ready for decision</span></GlassPanel><GlassPanel><strong>68%</strong><span>Average evidence coverage</span></GlassPanel></div>
    <div className="assessment-toolbar"><div><h2>Assessment portfolio</h2><p>Clear status and next actions across your current work.</p></div><label className="search"><Search /><span className="sr-only">Search assessments</span><input placeholder="Search assessments" /></label></div>
    <div className="assessment-cards">{assessments.map(({name, scope, domain, icon: Icon, status, progress, action, href, tone}) => <GlassPanel as="article" className="assessment-card" key={name}><div className="assessment-card-top"><span className={`assessment-domain assessment-domain--${domain.toLowerCase()}`}><Icon /></span><Badge tone={tone}>{status}</Badge></div><div><span className="assessment-type">{domain} assessment</span><h2>{name}</h2><p>{scope}</p></div><div className="completion-line"><div><span>Completion</span><strong>{progress}%</strong></div><div><i style={{width: `${progress}%`}} /></div></div><div className="assessment-card-foot"><span>Latest activity · Today</span><Link to={href}>{action}<ArrowRight /></Link></div></GlassPanel>)}</div>
  </div>;
}
