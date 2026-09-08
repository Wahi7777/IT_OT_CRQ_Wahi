import {AlertTriangle, ArrowLeft, ArrowRight, Check, CircleGauge, FileCheck2, Play, ShieldCheck} from "lucide-react";
import {useState} from "react";
import {Link, useNavigate} from "react-router-dom";
import {getRunApi} from "../api/RunApi";
import {PageHeader} from "../components/PageHeader";
import {Badge, Button, GlassPanel, ProvenanceStamp} from "../components/ui";
import {fieldInventory, sectorPacks} from "../contracts/governedData";
import {validateRunRequest} from "../contracts/validation";
import {AssessmentShell, getSteps} from "../features/assessment/AssessmentShell";
import {useAssessment} from "../features/assessment/AssessmentContext";

export function ReviewRunPage() {
  const {domain, request, dataMode} = useAssessment();
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();
  const applicable = fieldInventory.filter((item) => item.domain === "common" || item.domain === domain);
  const required = applicable.filter((item) => item.required && !item.inert && !["DISPLAY_ONLY", "INACTIVE_LEGACY"].includes(item.classification));
  const optional = applicable.filter((item) => !item.required && !item.inert && !["DISPLAY_ONLY", "INACTIVE_LEGACY"].includes(item.classification));
  const evidence = applicable.filter((item) => item.classification === "EVIDENCE_ONLY");
  const validationIssues = validateRunRequest(request);
  const approvedDemoPack = domain === "IT" ? "FS-v1.1.1" : "PG-v1.6";
  if (dataMode === "demo" && request.model_bundle_reference.bundle_id !== approvedDemoPack) validationIssues.push({path: "/model_bundle_reference/bundle_id", message: "has no approved offline result artifact; select Real API mode when that governed pack is deployed", keyword: "approvedDemoArtifact"});
  const ready = validationIssues.length === 0;
  const readiness = ready ? 92 : 76;
  const selectedPack = sectorPacks.find((pack) => pack.pack_id === request.model_bundle_reference.bundle_id);

  async function run() {
    if (!ready) return;
    setSubmitting(true); setError(null);
    try {
      const accepted = await getRunApi(dataMode).submit(request, crypto.randomUUID());
      navigate(`/runs/${accepted.run_id}?domain=${domain}`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "The run could not be submitted.");
      setSubmitting(false);
    }
  }

  return <AssessmentShell>
    <PageHeader eyebrow={`${domain} · Final review`} title="Review & Run" description="Confirm readiness and resolved model identity before creating an immutable quantitative run." />
    <div className="readiness-grid">
      <GlassPanel className="readiness-hero"><div className="readiness-ring" aria-label={`Assessment is ${readiness} percent ready`}><span>{readiness}<small>%</small></span><em>{ready ? "Ready" : "Review"}</em></div><div><Badge tone={ready ? "green" : "red"}>{ready ? "Ready to quantify" : "Validation required"}</Badge><h2>{ready ? "Assessment controls passed" : "Canonical contract errors remain"}</h2><p>{ready ? "The approved example satisfies the canonical request contract. Two evidence warnings remain non-blocking." : `${validationIssues.length} blocking contract issue${validationIssues.length === 1 ? "" : "s"} must be resolved before submission.`}</p></div></GlassPanel>
      <GlassPanel className="readiness-stats">
        <ReadinessStat icon={Check} label="Required inputs" value={`${required.length}/${required.length}`} tone="green" />
        <ReadinessStat icon={FileCheck2} label="Optional inputs" value={`${Math.max(optional.length - 2, 0)}/${optional.length}`} />
        <ReadinessStat icon={ShieldCheck} label="Validation errors" value={String(validationIssues.length)} tone={ready ? "green" : "red"} />
        <ReadinessStat icon={AlertTriangle} label="Warnings" value="2" tone="amber" pulse />
        <ReadinessStat icon={CircleGauge} label="Evidence coverage" value={`${Math.round((Math.max(evidence.length - 1, 0) / Math.max(evidence.length, 1)) * 100)}%`} />
      </GlassPanel>
    </div>
    <GlassPanel className="run-identity">
      <div className="panel-title-row"><div><span className="overline">Resolved execution identity</span><h2>Governed run configuration</h2></div><ProvenanceStamp>Immutable at submission</ProvenanceStamp></div>
      <dl>
        <Identity label="Domain" value={domain} />
        <Identity label="Sector pack" value={`${selectedPack?.pack_id ?? request.model_bundle_reference.bundle_id} · ${selectedPack?.pack_version ?? "Unresolved"}`} />
        <Identity label="Model bundle reference" value={`${request.model_bundle_reference.bundle_id} · ${request.model_bundle_reference.bundle_version}`} />
        <Identity label="Engine version" value={String(selectedPack?.minimum_engine_version ?? "Resolved by worker")} />
        <Identity label="Methodology version" value="unified-balbix-impact/1.0" />
        <Identity label="Simulation count" value={request.run_config.simulation_count.toLocaleString()} />
        <Identity label="Random seed" value={String(request.run_config.random_seed)} />
        <Identity label="Reporting basis" value={request.run_config.reporting_basis} />
        <Identity label="Data mode" value={dataMode === "demo" ? "Approved demo artifacts" : "Governed API"} />
      </dl>
    </GlassPanel>
    {validationIssues.length > 0 && <GlassPanel className="validation-list" aria-labelledby="validation-heading"><h2 id="validation-heading">Blocking validation issues</h2><ul>{validationIssues.map((issue, index) => <li key={`${issue.path}-${issue.keyword}-${index}`}><code>{issue.path}</code> {issue.message}</li>)}</ul></GlassPanel>}
    <GlassPanel className="warning-list"><div><AlertTriangle className="amber-text" /><div><strong>Evidence review recommended</strong><p>One evidence-only group has incomplete provenance. This does not change the quantitative inputs or block the run.</p></div></div><Link to={`/assessments/demo/outside-in-evidence?domain=${domain}`}>Review evidence <ArrowRight /></Link></GlassPanel>
    {error && <div className="error-banner" role="alert">{error}</div>}
    <footer className="workspace-footer"><Link to={`/assessments/demo/risk-appetite-insurance?domain=${domain}`}><Button variant="secondary"><ArrowLeft />Back</Button></Link><div><span>{ready ? "Creates a new immutable run" : "Resolve contract errors before running"}</span><Button onClick={run} disabled={submitting || !ready}>{submitting ? <><span className="spinner" />Submitting</> : <><Play />Run CRQ</>}</Button></div></footer>
  </AssessmentShell>;
}

function ReadinessStat({icon: Icon, label, value, tone, pulse}: {icon: typeof Check; label: string; value: string; tone?: string; pulse?: boolean}) {
  return <div className={`readiness-stat ${pulse ? "pulse-warning" : ""}`}><Icon /><span>{label}</span><strong className={tone ? `${tone}-text` : ""}>{value}</strong></div>;
}

function Identity({label, value}: {label: string; value: string}) { return <div><dt>{label}</dt><dd>{value}</dd></div>; }
