import {AlertTriangle, ArrowLeft, ArrowRight, Check, FileCheck2, ShieldCheck} from "lucide-react";
import type {CSSProperties} from "react";
import {Link, useLocation, useNavigate} from "react-router-dom";
import {PageHeader} from "../components/PageHeader";
import {Button, GlassPanel} from "../components/ui";
import {inventoryForScreen, routeLabels} from "../contracts/governedData";
import {AssessmentShell, getSteps} from "../features/assessment/AssessmentShell";
import {useAssessment} from "../features/assessment/AssessmentContext";
import {FieldGroup} from "../features/assessment/FieldCard";

export function AssessmentSectionPage() {
  const {domain} = useAssessment();
  const location = useLocation();
  const navigate = useNavigate();
  const screenId = location.pathname.split("/").at(-1) ?? "assessment-setup";
  const fields = inventoryForScreen(screenId, domain);
  const steps = getSteps(domain);
  const index = steps.indexOf(screenId);
  const previous = steps[index - 1];
  const next = steps[index + 1];
  const description = screenDescriptions[screenId] ?? "Complete the governed assessment fields for this section.";
  const requiredCount = fields.filter((field) => field.required).length;
  const evidenceCount = fields.filter((field) => field.classification === "EVIDENCE_ONLY").length;
  const progress = Math.min(94, Math.max(16, Math.round(((index + 1) / steps.length) * 100)));
  return <AssessmentShell>
    <PageHeader eyebrow={`Step ${userStepNumber(screenId)} / 6`} title={displayTitle(screenId)} description={description} />
    <div className="step-context"><span><ShieldCheck />Your answers are saved as you continue</span><span><Check />Required fields marked with *</span></div>
    <div className="assessment-body-grid">
      <div className="assessment-form-column">
        <div className="field-stack">{fields.map((item, itemIndex) => <FieldGroup key={`${item.canonical_path}-${item.classification}-${item.location}-${itemIndex}`} item={item} />)}</div>
        {!fields.length && <div className="inline-note">This page summarizes readiness and does not ask you to repeat assessment information.</div>}
      </div>
      <GlassPanel as="aside" className="step-readiness">
        <h2>Assessment readiness</h2>
        <div className="readiness-summary"><div className="mini-readiness-ring" style={{"--progress": `${progress * 3.6}deg`} as CSSProperties}><strong>{progress}%</strong></div><div><strong>Making good progress</strong><p>Complete the remaining inputs to run your assessment.</p></div></div>
        <div className="readiness-list">
          <div><Check /><span>Required inputs</span><strong>{requiredCount ? `${requiredCount} in this step` : "Complete"}</strong></div>
          <div><AlertTriangle /><span>Warnings</span><strong>{fields.some((field) => field.classification === "PERMITTED_OVERRIDE") ? "Review" : "None"}</strong></div>
          <div><FileCheck2 /><span>Evidence</span><strong>{evidenceCount ? `${evidenceCount} item${evidenceCount === 1 ? "" : "s"}` : "Optional"}</strong></div>
        </div>
        <p className="readiness-advice">Clear evidence makes the result easier to explain and act on.</p>
      </GlassPanel>
    </div>
    <footer className="workspace-footer">
      {previous ? <Link to={`/assessments/demo/${previous}?domain=${domain}`}><Button variant="secondary"><ArrowLeft />Back</Button></Link> : <span />}
      <div><span>Your progress is saved automatically</span>{next && <Button onClick={() => navigate(`/assessments/demo/${next}?domain=${domain}`)}>Save & continue<ArrowRight /></Button>}</div>
    </footer>
  </AssessmentShell>;
}

const screenDescriptions: Record<string, string> = {
  "assessment-setup": "Choose the kind of assessment and how you want the result presented.",
  "organisation-exposure": "Tell us about the organisation and the operations that could be financially affected.",
  facility: "Define the facility and critical process at the heart of this assessment.",
  "it-architecture": "Help us understand how users, services and critical systems are connected.",
  "ot-architecture-topology": "Help us understand access to production and the separation of critical systems.",
  "it-controls": "Assess the maturity and reach of the safeguards protecting the environment.",
  "ot-controls": "Review operational safeguards in clear, manageable capability groups.",
  "it-business-impact": "Review potential business consequences and refine only where evidence supports a change.",
  "ot-business-impact": "Capture the financial and operational exposure of the facility.",
  "ot-loss-driver-assumptions": "The underlying impact assumptions are managed for you.",
  "outside-in-evidence": "Add supporting observations that improve traceability and confidence.",
  "it-assumptions-overrides": "Optionally refine the assessment where strong client evidence is available.",
  "ot-assumptions-overrides": "Optionally refine the assessment where strong client evidence is available.",
  "risk-appetite-insurance": "Add decision thresholds and insurance details to understand retained exposure."
};

function displayTitle(screenId: string) {
  const map: Record<string, string> = {"assessment-setup": "Assessment setup", "organisation-exposure": "Organization", facility: "Organization & facility", "it-architecture": "Architecture", "ot-architecture-topology": "Architecture", "it-controls": "Controls", "ot-controls": "Controls", "it-business-impact": "Business impact", "ot-business-impact": "Business impact", "ot-loss-driver-assumptions": "Business impact", "outside-in-evidence": "Supporting evidence", "it-assumptions-overrides": "Business impact refinements", "ot-assumptions-overrides": "Business impact refinements", "risk-appetite-insurance": "Risk appetite & insurance"};
  return map[screenId] ?? routeLabels[screenId] ?? "Assessment";
}

function userStepNumber(screenId: string) {
  if (screenId.includes("architecture")) return 2;
  if (screenId.includes("controls")) return 3;
  if (["it-business-impact", "ot-business-impact", "ot-loss-driver-assumptions", "outside-in-evidence", "it-assumptions-overrides", "ot-assumptions-overrides"].includes(screenId)) return 4;
  if (screenId === "risk-appetite-insurance") return 5;
  if (screenId === "review-run") return 6;
  return 1;
}
