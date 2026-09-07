import {ArrowRight, Check, Factory, Landmark, ShieldCheck} from "lucide-react";
import {useNavigate} from "react-router-dom";
import {PageHeader} from "../components/PageHeader";
import {Badge, Button, GlassPanel, LockedBanner} from "../components/ui";
import type {Domain} from "../contracts/types";
import {sectorPacks} from "../contracts/governedData";
import {useAssessment} from "../features/assessment/AssessmentContext";

export function CreateAssessmentPage() {
  const {domain, setDomain, setValue, request, dataMode} = useAssessment();
  const navigate = useNavigate();
  const choose = (next: Domain) => setDomain(next);
  const packs = sectorPacks.filter((pack) => pack.domain === domain);
  return <>
    <PageHeader eyebrow="New" title="Create an assessment" description="Choose the quantitative domain. Only compatible approved model bundles are available." />
    <div className="create-grid">
      <button className={`domain-card glass-panel ${domain === "IT" ? "selected" : ""}`} onClick={() => choose("IT")} aria-pressed={domain === "IT"}>
        <span className="domain-icon"><Landmark /></span><Badge tone="indigo">IT</Badge><h2>Enterprise technology</h2><p>Quantify cyber events affecting digital services, records, endpoints and financial operations.</p><ul><li><Check />Financial Services pack</li><li><Check />Six governed attack routes</li><li><Check />Control and treatment analysis</li></ul>
      </button>
      <button className={`domain-card glass-panel ${domain === "OT" ? "selected" : ""}`} onClick={() => choose("OT")} aria-pressed={domain === "OT"}>
        <span className="domain-icon"><Factory /></span><Badge tone="amber">OT</Badge><h2>Operational technology</h2><p>Quantify operational disruption across topology, S1–S5 progression, downtime and capacity.</p><ul><li><Check />Power, energy and manufacturing packs</li><li><Check />Topology and TTP pathways</li><li><Check />BI and non-BI loss drivers</li></ul>
      </button>
    </div>
    <GlassPanel className="selection-summary"><div><ShieldCheck /><div><label htmlFor="sector-pack">Governed sector pack</label><select id="sector-pack" value={request.model_bundle_reference.bundle_id} onChange={(event) => {const pack = packs.find((candidate) => candidate.pack_id === event.target.value); if (pack) setValue(["assessment", "assessment", "sector"], pack.sector);}}>{packs.map((pack) => <option value={pack.pack_id} key={pack.pack_id}>{pack.sector} · {pack.pack_id}</option>)}</select><small>{packs.find((pack) => pack.pack_id === request.model_bundle_reference.bundle_id)?.pack_status}</small></div></div><LockedBanner>Bundle assumptions remain locked throughout the assessment</LockedBanner><div><Button onClick={() => navigate(`/assessments/demo/setup?domain=${domain}`)}>Continue with {domain}<ArrowRight /></Button>{dataMode === "demo" && !["FS-v1.1.1", "PG-v1.6"].includes(request.model_bundle_reference.bundle_id) && <small className="amber-text">Input workflow available; a deployed real API is required to run this pack.</small>}</div></GlassPanel>
  </>;
}
