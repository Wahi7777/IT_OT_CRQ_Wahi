import {Download, FileText, ShieldCheck} from "lucide-react";
import type {ReactNode} from "react";
import {NavLink, useParams} from "react-router-dom";
import {PageHeader} from "../../components/PageHeader";
import {Badge, Button, ProvenanceStamp} from "../../components/ui";
import type {CRQResult, Domain} from "../../contracts/types";

const tabs = [
  ["overview", "Overview"], ["risk-drivers", "Risk Drivers"], ["scenarios", "Scenarios"],
  ["attack-paths", "Attack Paths"], ["business-impact", "Business Impact"], ["treatment", "Treatment"],
  ["insurance", "Insurance"], ["uncertainty", "Uncertainty"], ["evidence", "Evidence"]
];

export function ResultsShell({result, domain, currency, children}: {result: CRQResult; domain: Domain; currency?: string | null; children: ReactNode}) {
  const {runId = "demo"} = useParams();
  return <>
    <PageHeader eyebrow={`${domain} result · ${result.run.assessment_id}`} title="Quantitative risk result" description={`Completed ${new Date(result.run.completed_at).toLocaleDateString("en-AE", {day: "2-digit", month: "short", year: "numeric"})} · ${Number(result.run.simulation_count).toLocaleString()} simulations`} actions={<><ProvenanceStamp>{result.provenance.model_bundle_id}</ProvenanceStamp><Button variant="secondary"><FileText />Report</Button><Button><Download />Export</Button></>} />
    <div className="result-governance"><Badge tone="green"><ShieldCheck />Canonical result</Badge><span>Engine {result.provenance.engine_version}</span><span>Methodology {result.provenance.methodology_version}</span><span>Currency {currency ?? "not specified"}</span><code>{String(result.provenance.result_hash).slice(0, 13)}…</code></div>
    <nav className="result-tabs" aria-label="Result sections">{tabs.map(([path, label]) => <NavLink key={path} to={`/results/${runId}/${path}`}>{label}</NavLink>)}</nav>
    <div className="result-content">{children}</div>
  </>;
}
