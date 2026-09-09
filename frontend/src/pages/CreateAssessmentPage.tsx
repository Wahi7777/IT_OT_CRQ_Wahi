import {ArrowRight, Check, Factory, Landmark} from "lucide-react";
import {useNavigate} from "react-router-dom";
import {PageHeader} from "../components/PageHeader";
import {Badge, Button, GlassPanel} from "../components/ui";
import type {Domain} from "../contracts/types";
import {useAssessment} from "../features/assessment/AssessmentContext";

export function CreateAssessmentPage() {
  const {domain, setDomain} = useAssessment();
  const navigate = useNavigate();
  const choose = (next: Domain) => setDomain(next);
  return <>
    <PageHeader eyebrow="New assessment" title="What would you like to assess?" description="Choose the environment that best represents the risk decision you need to make." />
    <div className="create-grid">
      <button className={`domain-card glass-panel ${domain === "IT" ? "selected" : ""}`} onClick={() => choose("IT")} aria-pressed={domain === "IT"}>
        <span className="domain-icon"><Landmark /></span><Badge tone="indigo">IT</Badge><h2>Enterprise technology</h2><p>Understand cyber risk affecting digital services, sensitive information and financial operations.</p><ul><li><Check />Organization-wide exposure</li><li><Check />Access paths and controls</li><li><Check />Financial impact and treatment</li></ul>
      </button>
      <button className={`domain-card glass-panel ${domain === "OT" ? "selected" : ""}`} onClick={() => choose("OT")} aria-pressed={domain === "OT"}>
        <span className="domain-icon"><Factory /></span><Badge tone="amber">OT</Badge><h2>Operational technology</h2><p>Understand disruption risk across facilities, production systems and critical operations.</p><ul><li><Check />Facility and process scope</li><li><Check />Operational access and safeguards</li><li><Check />Downtime and financial impact</li></ul>
      </button>
    </div>
    <GlassPanel className="selection-summary"><div><span>Selected experience</span><strong>{domain === "IT" ? "Enterprise technology" : "Operational technology"}</strong></div><Button onClick={() => navigate(`/assessments/demo/assessment-setup?domain=${domain}`)}>Start assessment<ArrowRight /></Button></GlassPanel>
  </>;
}
