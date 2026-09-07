import {ArrowLeft, ArrowRight, RotateCcw} from "lucide-react";
import {Link, useLocation, useNavigate} from "react-router-dom";
import {PageHeader} from "../components/PageHeader";
import {Button} from "../components/ui";
import {inventoryForScreen, routeLabels} from "../contracts/governedData";
import {AssessmentShell, getSteps} from "../features/assessment/AssessmentShell";
import {useAssessment} from "../features/assessment/AssessmentContext";
import {FieldGroup} from "../features/assessment/FieldCard";

export function AssessmentSectionPage() {
  const {domain, reset} = useAssessment();
  const location = useLocation();
  const navigate = useNavigate();
  const screenId = location.pathname.split("/").at(-1) ?? "assessment-setup";
  const fields = inventoryForScreen(screenId, domain);
  const steps = getSteps(domain);
  const index = steps.indexOf(screenId);
  const previous = steps[index - 1];
  const next = steps[index + 1];
  const description = screenDescriptions[screenId] ?? "Complete the governed assessment fields for this section.";
  return <AssessmentShell>
    <PageHeader eyebrow={`${domain} · Step ${index + 1} of ${steps.length}`} title={routeLabels[screenId] ?? "Assessment"} description={description} actions={<Button variant="ghost" onClick={reset}><RotateCcw />Reset approved example</Button>} />
    <div className="section-progress"><span style={{width: `${((index + 1) / steps.length) * 100}%`}} /></div>
    <div className="field-stack">{fields.map((item, itemIndex) => <FieldGroup key={`${item.canonical_path}-${item.classification}-${item.location}-${itemIndex}`} item={item} />)}</div>
    {!fields.length && <div className="inline-note">This page summarizes governed readiness and does not own a second copy of assessment fields.</div>}
    <footer className="workspace-footer">
      {previous ? <Link to={`/assessments/demo/${previous}?domain=${domain}`}><Button variant="secondary"><ArrowLeft />Back</Button></Link> : <span />}
      <div><span>Changes are held in this browser session</span>{next && <Button onClick={() => navigate(`/assessments/demo/${next}?domain=${domain}`)}>Save & continue<ArrowRight /></Button>}</div>
    </footer>
  </AssessmentShell>;
}

const screenDescriptions: Record<string, string> = {
  "assessment-setup": "Resolve the domain, sector, reporting basis and approved immutable model bundle.",
  "organisation-exposure": "Describe the organisation and active financial exposure used by the IT model.",
  facility: "Identify the facility, geography and critical production scope.",
  "it-architecture": "Assess each governed route without collapsing feasibility into control effectiveness.",
  "ot-architecture-topology": "Record topology responses. Unknown remains distinct from a closed path.",
  "it-controls": "Assess control maturity and coverage; attach evidence separately.",
  "ot-controls": "Review all OT controls with quantitative and evidence-only fields clearly separated.",
  "it-business-impact": "Review inherited impact parameters and apply only permitted, evidenced overrides.",
  "ot-business-impact": "Capture active OT financial and operational exposure.",
  "ot-loss-driver-assumptions": "Inspect locked driver assumptions resolved from the approved sector pack.",
  "outside-in-evidence": "Review evidence coverage without turning observations into unapproved model adjustments.",
  "it-assumptions-overrides": "Manage client-specific permitted overrides against locked model assumptions.",
  "ot-assumptions-overrides": "Prudence is editable only as a governed override; pack assumptions remain locked.",
  "risk-appetite-insurance": "Set decision thresholds and the insurance programme used by the existing model."
};
