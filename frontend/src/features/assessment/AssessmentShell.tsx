import {Check, ChevronRight, Circle, PanelLeftClose} from "lucide-react";
import {useEffect, type ReactNode} from "react";
import {NavLink, useLocation, useSearchParams} from "react-router-dom";
import {Badge, GlassPanel} from "../../components/ui";
import {routeLabels} from "../../contracts/governedData";
import {useAssessment} from "./AssessmentContext";

const steps = {
  IT: ["assessment-setup", "organisation-exposure", "it-architecture", "it-controls", "it-business-impact", "outside-in-evidence", "it-assumptions-overrides", "risk-appetite-insurance", "review-run"],
  OT: ["assessment-setup", "facility", "ot-architecture-topology", "ot-controls", "ot-business-impact", "ot-loss-driver-assumptions", "outside-in-evidence", "ot-assumptions-overrides", "risk-appetite-insurance", "review-run"]
};

export function AssessmentShell({children}: {children: ReactNode}) {
  const {domain, setDomain, request} = useAssessment();
  const [params] = useSearchParams();
  const location = useLocation();
  useEffect(() => {
    const requested = params.get("domain");
    if (requested === "IT" || requested === "OT") setDomain(requested);
  }, [params, setDomain]);
  const current = location.pathname.split("/").at(-1) ?? "assessment-setup";
  const currentIndex = steps[domain].indexOf(current);
  return <div className="workspace-layout">
    <GlassPanel as="aside" className="stepper">
      <div className="stepper-head"><div><span>{domain} assessment</span><strong>{request.assessment.assessment.organisation || request.assessment.scope?.facility || "Approved example"}</strong></div><PanelLeftClose /></div>
      <ol>
        {steps[domain].map((step, index) => <li key={step} className={index === currentIndex ? "current" : index < currentIndex ? "complete" : ""}>
          <NavLink to={`/assessments/demo/${step}?domain=${domain}`}>
            <span className="step-state">{index < currentIndex ? <Check /> : index === currentIndex ? <Circle fill="currentColor" /> : index + 1}</span>
            <span>{routeLabels[step]}</span><ChevronRight />
          </NavLink>
        </li>)}
      </ol>
      <div className="stepper-foot"><Badge tone="green">Governed</Badge><span>{request.model_bundle_reference.bundle_id}</span></div>
    </GlassPanel>
    <div className="workspace-main">{children}</div>
  </div>;
}

export function getSteps(domain: "IT" | "OT") { return steps[domain]; }
