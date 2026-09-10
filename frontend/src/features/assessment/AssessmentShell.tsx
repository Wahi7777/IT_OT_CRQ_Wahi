import {Check} from "lucide-react";
import {useEffect, type ReactNode} from "react";
import {Link, useLocation, useSearchParams} from "react-router-dom";
import {useAssessment} from "./AssessmentContext";
import {CopilotPanel} from "./CopilotPanel";

const routes = {
  IT: ["assessment-setup", "organisation-exposure", "it-architecture", "it-controls", "it-business-impact", "outside-in-evidence", "it-assumptions-overrides", "risk-appetite-insurance", "review-run"],
  OT: ["assessment-setup", "facility", "ot-architecture-topology", "ot-controls", "ot-business-impact", "outside-in-evidence", "ot-assumptions-overrides", "risk-appetite-insurance", "review-run"]
};
const journey = {
  IT: [
    {label: "Organization", route: "organisation-exposure", members: ["assessment-setup", "organisation-exposure"]},
    {label: "Architecture", route: "it-architecture", members: ["it-architecture"]},
    {label: "Controls", route: "it-controls", members: ["it-controls"]},
    {label: "Business Impact", route: "it-business-impact", members: ["it-business-impact", "outside-in-evidence", "it-assumptions-overrides"]},
    {label: "Risk Appetite & Insurance", route: "risk-appetite-insurance", members: ["risk-appetite-insurance"]},
    {label: "Review & Run", route: "review-run", members: ["review-run"]}
  ],
  OT: [
    {label: "Organization", route: "facility", members: ["assessment-setup", "facility"]},
    {label: "Architecture", route: "ot-architecture-topology", members: ["ot-architecture-topology"]},
    {label: "Controls", route: "ot-controls", members: ["ot-controls"]},
    {label: "Business Impact", route: "ot-business-impact", members: ["ot-business-impact", "outside-in-evidence", "ot-assumptions-overrides"]},
    {label: "Risk Appetite & Insurance", route: "risk-appetite-insurance", members: ["risk-appetite-insurance"]},
    {label: "Review & Run", route: "review-run", members: ["review-run"]}
  ]
};

export function AssessmentShell({children}: {children: ReactNode}) {
  const {domain, setDomain} = useAssessment();
  const [params] = useSearchParams();
  const location = useLocation();
  useEffect(() => { const requested = params.get("domain"); if (requested === "IT" || requested === "OT") setDomain(requested); }, [params, setDomain]);
  const screenId = location.pathname.split("/").at(-1) ?? "assessment-setup";
  const currentJourney = journey[domain];
  const activeIndex = Math.max(0, currentJourney.findIndex((step) => step.members.includes(screenId)));
  return <div className="assessment-experience"><CopilotPanel screenId={screenId} /><section className="guided-workspace">
    <nav className="journey-stepper" aria-label="Assessment progress"><ol>{currentJourney.map((step, index) => <li key={step.label} className={index < activeIndex ? "complete" : index === activeIndex ? "current" : ""}><Link to={`/assessments/demo/${step.route}?domain=${domain}`}><span>{index < activeIndex ? <Check /> : index + 1}</span><strong>{step.label}</strong></Link></li>)}</ol></nav>
    <div className="guided-content">{children}</div>
  </section></div>;
}
export function getSteps(domain: "IT" | "OT") { return routes[domain]; }
