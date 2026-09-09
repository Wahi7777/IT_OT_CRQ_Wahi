import {ShieldCheck} from "lucide-react";
import type {ReactNode} from "react";
import {NavLink, useLocation, useParams} from "react-router-dom";
import {PageHeader} from "../../components/PageHeader";
import {Badge} from "../../components/ui";
import type {CRQResult, Domain} from "../../contracts/types";
import {CopilotPanel} from "../assessment/CopilotPanel";

const tabs = [
  ["overview", "Overview"], ["risk-drivers", "Risk Drivers"], ["scenarios", "Scenarios"],
  ["attack-paths", "Attack Paths"], ["business-impact", "Business Impact"], ["treatment", "Treatment"],
  ["insurance", "Insurance"], ["evidence", "Evidence"]
];

export function ResultsShell({result, domain, currency, selectedEntity = null, children}: {result: CRQResult; domain: Domain; currency?: string | null; selectedEntity?: {entity_type: string; entity_id: string} | null; children: ReactNode}) {
  const {runId = "demo"} = useParams();
  const resultPage = useLocation().pathname.split("/").at(-1) ?? "overview";
  return <div className="result-experience">
    <CopilotPanel screenId={`results-${resultPage}`} subtitle="Interpreting your assessment results" runId={runId} selectedEntity={selectedEntity} />
    <section className="results-workspace">
      <div className="results-heading">
        <PageHeader eyebrow={`${domain} cyber risk assessment`} title="Assessment results" description={`Modelled insights to help you understand, quantify and reduce cyber risk · ${new Date(result.run.completed_at).toLocaleDateString("en-AE", {day: "2-digit", month: "short", year: "numeric"})}`} />
        <div className="result-governance"><Badge tone="green"><ShieldCheck />Completed</Badge><span>Prudent reporting basis</span><span>Currency {currency ?? "not specified"}</span></div>
      </div>
      <nav className="result-tabs" aria-label="Result sections">{tabs.map(([path, label]) => <NavLink key={path} to={`/results/${runId}/${path}`}>{label}</NavLink>)}</nav>
      <div className="result-content">{children}</div>
    </section>
  </div>;
}
