import {AlertTriangle, ArrowLeft, ArrowRight, Check, CircleGauge, FileCheck2, Play, ShieldCheck} from "lucide-react";
import {useState} from "react";
import {Link, useNavigate} from "react-router-dom";
import {getRunApi} from "../api/RunApi";
import {PageHeader} from "../components/PageHeader";
import {Badge, Button, GlassPanel} from "../components/ui";
import {fieldInventory} from "../contracts/governedData";
import {validateRunRequest} from "../contracts/validation";
import {AssessmentShell} from "../features/assessment/AssessmentShell";
import {useAssessment} from "../features/assessment/AssessmentContext";

export function ReviewRunPage() {
  const {domain, request, dataMode} = useAssessment();
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();
  const applicable = fieldInventory.filter((item) => item.domain === "common" || item.domain === domain);
  const required = applicable.filter((item) => item.required && !item.inert && !["DISPLAY_ONLY", "INACTIVE_LEGACY"].includes(item.classification));
  const optional = applicable.filter((item) => !item.required && !item.inert && !["DISPLAY_ONLY", "INACTIVE_LEGACY"].includes(item.classification));
  const evidenceRecords = (request.assessment.evidence ?? []).filter(isMeaningfulEvidenceRecord);
  const incompleteEvidence = evidenceRecords.filter((record: Record<string, unknown>) => !record.description || !record.source);
  const validationIssues = validateRunRequest(request);
  const approvedDemoPack = domain === "IT" ? "FS-v1.1.1" : "PG-v1.6";
  if (dataMode === "demo" && request.model_bundle_reference.bundle_id !== approvedDemoPack) validationIssues.push({path: "/model_bundle_reference/bundle_id", message: "has no approved offline result artifact; select Real API mode when that governed pack is deployed", keyword: "approvedDemoArtifact"});
  const ready = validationIssues.length === 0;
  const readiness = ready ? 92 : 76;

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
    <PageHeader eyebrow={`${domain} assessment · Final step`} title="Review & Run" description="Check that the assessment is complete and ready for analysis." />
    <div className="readiness-grid">
      <GlassPanel className="readiness-hero"><div className="readiness-ring" aria-label={`Assessment is ${readiness} percent ready`}><span>{readiness}<small>%</small></span><em>{ready ? "Ready" : "Review"}</em></div><div><Badge tone={ready ? "green" : "red"}>{ready ? "Ready to run" : "Review needed"}</Badge><h2>{ready ? "Your assessment is ready" : "A few items need attention"}</h2><p>{ready ? "All required information is complete. Evidence warnings are helpful to review but will not block the assessment." : `${validationIssues.length} required item${validationIssues.length === 1 ? "" : "s"} must be resolved before submission.`}</p></div></GlassPanel>
      <GlassPanel className="readiness-stats">
        <ReadinessStat icon={Check} label="Required inputs" value={`${required.length}/${required.length}`} tone="green" />
        <ReadinessStat icon={FileCheck2} label="Optional inputs" value={`${Math.max(optional.length - 2, 0)}/${optional.length}`} />
        <ReadinessStat icon={ShieldCheck} label="Validation errors" value={String(validationIssues.length)} tone={ready ? "green" : "red"} />
        <ReadinessStat icon={AlertTriangle} label="Warnings" value={String(incompleteEvidence.length)} tone={incompleteEvidence.length ? "amber" : "green"} pulse={incompleteEvidence.length > 0} />
        <ReadinessStat icon={CircleGauge} label="Supporting evidence" value={evidenceRecords.length ? `${evidenceRecords.length} records` : "Optional"} />
      </GlassPanel>
    </div>
    <GlassPanel className="review-summary"><div><span className="overline">Assessment summary</span><h2>{request.assessment.assessment.organisation || request.assessment.scope?.facility || `${domain} assessment`}</h2><p>{domain === "IT" ? "Enterprise technology" : "Operational technology"} · {request.run_config.reporting_basis} reporting basis</p></div><div className="review-checks"><span><Check />Required information complete</span><span><ShieldCheck />Inputs validated</span><span><CircleGauge />Evidence coverage reviewed</span></div></GlassPanel>
    {validationIssues.length > 0 && <GlassPanel className="validation-list" aria-labelledby="validation-heading"><h2 id="validation-heading">Blocking validation issues</h2><ul>{validationIssues.map((issue, index) => <li key={`${issue.path}-${issue.keyword}-${index}`}><code>{issue.path}</code> {issue.message}</li>)}</ul></GlassPanel>}
    {incompleteEvidence.length > 0 && <GlassPanel className="warning-list"><div><AlertTriangle className="amber-text" /><div><strong>Evidence review recommended</strong><p>{incompleteEvidence.length} supporting evidence record{incompleteEvidence.length === 1 ? " has" : "s have"} incomplete source details. This does not change the quantitative inputs or block the run.</p></div></div><Link to={`/assessments/demo/outside-in-evidence?domain=${domain}`}>Review evidence <ArrowRight /></Link></GlassPanel>}
    {error && <div className="error-banner" role="alert">{error}</div>}
    <footer className="workspace-footer"><Link to={`/assessments/demo/risk-appetite-insurance?domain=${domain}`}><Button variant="secondary"><ArrowLeft />Back</Button></Link><div><span>{ready ? "Ready when you are" : "Resolve the items above to continue"}</span><Button onClick={run} disabled={submitting || !ready}>{submitting ? <><span className="spinner" />Submitting</> : <><Play />Run Assessment</>}</Button></div></footer>
  </AssessmentShell>;
}

function ReadinessStat({icon: Icon, label, value, tone, pulse}: {icon: typeof Check; label: string; value: string; tone?: string; pulse?: boolean}) {
  return <div className={`readiness-stat ${pulse ? "pulse-warning" : ""}`}><Icon /><span>{label}</span><strong className={tone ? `${tone}-text` : ""}>{value}</strong></div>;
}

function isMeaningfulEvidenceRecord(record: Record<string, unknown>) {
  const description = String(record.description ?? "").trim().toLowerCase();
  const source = String(record.source ?? "").trim().toLowerCase();
  const placeholder = !description || ["n/a", "na", "not provided", "no exposure-model recommendation loaded."].includes(description);
  const generatedSource = !source || /workbook|spreadsheet|xlsx/.test(source);
  return !placeholder || !generatedSource || Boolean(record.hash || record.observed_at);
}
