import {ArrowUp, BarChart3, ChevronLeft, ChevronRight, FileText, Lightbulb, MessageCircle, Paperclip, Sparkles} from "lucide-react";
import {useState} from "react";
import {getCopilotApi, type CopilotState} from "../../api/CopilotApi";
import {useAssessment} from "./AssessmentContext";

const guidance: Record<string, {title: string; intro: string; why: string; evidence: string}> = {
  "assessment-setup": {title: "Let’s begin with the assessment scope.", intro: "A clear scope keeps the assessment focused on the decisions you need to make.", why: "We’ll use this to tailor the questions for IT or operational technology risk.", evidence: "A recent risk register or statement of scope can be helpful."},
  "organisation-exposure": {title: "Tell me about the organisation.", intro: "We’ll capture the scale of operations and the financial exposure that could be affected.", why: "These figures anchor the financial impact analysis.", evidence: "Annual reports, service inventories and finance-approved exposure values are useful."},
  facility: {title: "Let’s define the critical facility.", intro: "Focus on the operational site and process that matter for this assessment.", why: "A precise facility scope makes the operational impact easier to interpret.", evidence: "Facility profiles, production plans and critical process maps are useful."},
  "it-architecture": {title: "Next, let’s look at technology architecture.", intro: "We’re exploring the practical ways an event could reach critical services.", why: "Connectivity and access shape route feasibility, separately from control strength.", evidence: "Network diagrams, access reviews and service maps are ideal."},
  "ot-architecture-topology": {title: "Next, let’s look at your OT connections.", intro: "Simple questions about access and connectivity help us understand plausible paths to production.", why: "Architecture determines which paths are possible; it does not score your controls.", evidence: "Network diagrams, remote access registers and vendor access policies are ideal."},
  "it-controls": {title: "Now we’ll review the safeguards in place.", intro: "Assess how consistently each protective capability operates across the environment.", why: "Control maturity and coverage influence the existing risk position.", evidence: "Control test results, standards, dashboards and assurance reports are useful."},
  "ot-controls": {title: "Now we’ll review operational safeguards.", intro: "Work through the controls by capability, focusing on maturity and coverage.", why: "This distinguishes technical protection from whether an attack path exists.", evidence: "Testing records, maintenance evidence and control owner attestations are useful."},
  "it-business-impact": {title: "Let’s understand the business consequences.", intro: "Only add an adjustment when client evidence supports a more relevant impact range.", why: "This keeps the result grounded in the organisation’s actual exposure.", evidence: "BIA records, incident costs and finance-approved estimates are useful."},
  "ot-business-impact": {title: "Let’s understand operational consequences.", intro: "Capture the scale of interruption and the critical assets supporting production.", why: "This translates disruption into decision-ready financial impact.", evidence: "BIA, production value and restoration assumptions are useful."},
  "outside-in-evidence": {title: "Add evidence where it strengthens the assessment.", intro: "Supporting evidence is optional. Include a concise source when it helps a reviewer understand or verify an input.", why: "Clear evidence improves traceability without changing an answer by itself.", evidence: "Use current policies, diagrams, test reports or approved business-impact records. Leave placeholder records blank."},
  "risk-appetite-insurance": {title: "Finally, add the decision thresholds.", intro: "Risk appetite and insurance help frame what the result means for action and transfer.", why: "They let the result show tolerance exceedance and retained exposure.", evidence: "Board risk appetite and current insurance schedules are useful."},
  "review-run": {title: "Your assessment is ready for review.", intro: "Check completeness, warnings and evidence coverage before starting the analysis.", why: "A final review protects the quality and reproducibility of the result.", evidence: "Resolve blocking items; evidence warnings may remain non-blocking."},
  "results-overview": {title: "Your results are ready.", intro: "Start with the headline loss measures and material-event likelihood.", why: "AAL describes expected annual loss; VaR and TVaR show increasingly severe tail outcomes.", evidence: "Use the evidence view to see where the assessment is well supported."},
  "results-risk-drivers": {title: "Let’s trace how the risk forms.", intro: "Follow the progression from threat activity through paths and scenarios to financial impact.", why: "This helps distinguish the factors driving frequency from those driving severity.", evidence: "Compare the dominant actors and stages with your threat intelligence and architecture evidence."},
  "results-scenarios": {title: "Compare the modelled loss scenarios.", intro: "The scenarios are ranked by their financial contribution to the result.", why: "Scenario concentration shows where resilience and treatment decisions can matter most.", evidence: "Business-impact analysis and incident history help validate scenario relevance."},
  "results-attack-paths": {title: "Explore how threats could reach critical services.", intro: "Use the filters to focus on an actor, scenario or route.", why: "Path feasibility remains separate from control effectiveness, and unknown never means closed.", evidence: "Network diagrams, access reviews and trusted-connection records support path review."},
  "results-business-impact": {title: "See where financial loss is concentrated.", intro: "The chart and ranked lists show the categories contributing to annual expected loss.", why: "Understanding loss composition helps target resilience, response and risk-transfer decisions.", evidence: "Finance-approved cost data and BIA assumptions are the strongest supporting sources."},
  "results-treatment": {title: "Review modelled control uplifts.", intro: "Only benefits returned by the quantitative engine are shown here.", why: "The frontend never estimates treatment reductions; a zero result means no benefit was returned for that run.", evidence: "Use current control testing and implementation plans when considering an uplift."},
  "results-insurance": {title: "Review risk transfer and retained exposure.", intro: "These values show insurance outcomes returned by the assessment.", why: "Ground-up loss and retained loss should be considered together when making transfer decisions.", evidence: "Validate policy limits, retention, layers and terms against the current insurance schedule."},
  "results-evidence": {title: "Review the assessment evidence trail.", intro: "This view shows the evidence records carried into the result.", why: "Clear provenance makes the result easier to challenge, reproduce and govern.", evidence: "Prioritise missing or stale evidence for the inputs that drive material decisions."}
};

const promptSets: Record<string, [string, string, string]> = {
  "assessment-setup": ["Why is this input required?", "What evidence should support this value?", "Review the assessment scope"],
  "organisation-exposure": ["Why is this input required?", "What evidence should support this value?", "Review the assessment scope"],
  facility: ["Explain facility scope", "What facility evidence helps?", "Review critical operations"],
  "it-architecture": ["Why are we asking this?", "What evidence would support this answer?", "What does Unknown mean?"],
  "ot-architecture-topology": ["Why are we asking this?", "What evidence would support this answer?", "What does Unknown mean?"],
  "it-controls": ["Why does this control matter?", "What evidence should I provide?", "Which scenarios depend on this control?"],
  "ot-controls": ["Why does this control matter?", "What evidence should I provide?", "Which scenarios depend on this control?"],
  "it-business-impact": ["Why is this input required?", "How is this used in the model?", "When should I override this assumption?"],
  "ot-business-impact": ["Why is this input required?", "How is this used in the model?", "When should I override this assumption?"],
  "outside-in-evidence": ["Do I have supporting evidence?", "What evidence would improve confidence?", "Is supporting evidence optional?"],
  "risk-appetite-insurance": ["Explain risk appetite", "What policy evidence helps?", "Review decision thresholds"],
  "review-run": ["Is this assessment ready?", "Which evidence gaps remain?", "Review outstanding inputs"],
  "results-overview": ["Explain headline metrics", "What drives this result?", "What does the tail risk mean?"],
  "results-risk-drivers": ["What is driving the exposure?", "Which actor matters most?", "Which loss component dominates?"],
  "results-scenarios": ["Why is this scenario material?", "What drives the severity?", "Which attack routes contribute?"],
  "results-attack-paths": ["Why is this path open?", "Which controls influence this route?", "What evidence supports this state?"],
  "results-business-impact": ["What is driving the financial loss?", "Which assumptions affect severity most?", "What happens in the tail?"],
  "results-treatment": ["Why is this treatment prioritized?", "What part of the risk does it reduce?", "How does it change tail risk?"],
  "results-insurance": ["How much risk remains after insurance?", "How often does the policy attach?", "What does exhaustion probability mean?"],
  "results-evidence": ["Where is the assessment weakest?", "What evidence should we collect next?", "Which unknowns affect the result?"]
};

export function CopilotPanel({screenId, subtitle = "Your cyber risk guide", runId = null, selectedEntity = null}: {screenId: string; subtitle?: string; runId?: string | null; selectedEntity?: {entity_type: string; entity_id: string} | null}) {
  const {request, dataMode} = useAssessment();
  const [prompt, setPrompt] = useState("");
  const [collapsed, setCollapsed] = useState(false);
  const [state, setState] = useState<CopilotState>("IDLE");
  const [answer, setAnswer] = useState<string | null>(null);
  const copy = guidance[screenId] ?? {title: "I’ll guide you through this step.", intro: "Answer the questions using the best available information.", why: "Each response supports a clear, traceable assessment.", evidence: "Add a source or note where it improves confidence."};
  const prompts = promptSets[screenId] ?? ["Explain this page", "What evidence helps?", "Review my inputs"];
  const currentView = contextType(screenId);
  const ask = async (question: string) => {
    const clean = question.trim();
    if (!clean || state === "THINKING") return;
    setPrompt(clean);
    setState("THINKING");
    setAnswer(null);
    try {
      const reply = await getCopilotApi(dataMode).query({assessment_id: request.assessment.assessment.assessment_id, run_id: currentView.startsWith("results.") ? runId : null, current_view: currentView, selected_entity: selectedEntity, question: clean}, currentView.startsWith("results.") ? undefined : request.assessment);
      if (reply.status === "VERIFIED" && reply.answer) { setAnswer(reply.answer); setState("VERIFIED"); }
      else { setState("REJECTED"); }
    } catch { setState("FAILED"); }
  };
  if (collapsed) return <aside className="copilot-panel copilot-panel--collapsed" aria-label="CRQ Copilot guidance"><button type="button" onClick={() => setCollapsed(false)} aria-label="Open CRQ Copilot"><span className="copilot-orbit"><Sparkles /></span><ChevronRight /></button><strong>Copilot</strong></aside>;
  return <aside className="copilot-panel" aria-label="CRQ Copilot guidance">
    <div className="copilot-brand"><span className="copilot-orbit"><Sparkles /></span><div><strong>CRQ Copilot</strong><small>{subtitle}</small></div><button type="button" onClick={() => setCollapsed(true)} aria-label="Collapse CRQ Copilot"><ChevronLeft /></button></div>
    <div className="copilot-thread"><GuidanceMessage icon={MessageCircle} title={copy.title} body={copy.intro} /><GuidanceMessage icon={Lightbulb} title="Why this matters" body={copy.why} /><GuidanceMessage icon={FileText} title="Helpful evidence" body={copy.evidence} />{state === "THINKING" && <article className="guidance-message copilot-thinking" aria-live="polite"><span><Sparkles /></span><div><strong>Reviewing governed facts…</strong><p>I’m checking this page’s model facts and evidence.</p></div></article>}{state === "VERIFIED" && answer && <GuidanceMessage icon={Sparkles} title="Verified interpretation" body={answer} />}{state === "REJECTED" && <GuidanceMessage icon={ShieldIcon} title="Response not shown" body="The generated response could not be verified against this page’s governed facts." />}{state === "FAILED" && <GuidanceMessage icon={ShieldIcon} title="Copilot unavailable" body="The interpretation service could not respond. Your assessment and results are unchanged." />}</div>
    <div className="copilot-spacer" />
    <div className="quick-prompts"><span>Suggested questions</span><div><button type="button" disabled={state === "THINKING"} onClick={() => void ask(prompts[0])}><Lightbulb />{prompts[0]}</button><button type="button" disabled={state === "THINKING"} onClick={() => void ask(prompts[1])}><FileText />{prompts[1]}</button><button type="button" disabled={state === "THINKING"} onClick={() => void ask(prompts[2])}><BarChart3 />{prompts[2]}</button></div></div>
    <form className="copilot-input" onSubmit={(event) => {event.preventDefault(); void ask(prompt);}}><Paperclip /><input value={prompt} onChange={(event) => setPrompt(event.target.value)} placeholder="Ask a question or request guidance…" aria-label="Ask CRQ Copilot" /><button type="submit" disabled={state === "THINKING"} aria-label="Send question"><ArrowUp /></button></form>
    <small className="copilot-disclaimer">Generated from this CRQ view and verified against underlying model facts</small>
  </aside>;
}

const ShieldIcon = FileText;

function contextType(screenId: string) {
  if (screenId.startsWith("results-")) return `results.${screenId.slice(8).replaceAll("-", "_")}`;
  if (["assessment-setup", "organisation-exposure", "facility"].includes(screenId)) return "assessment.organization";
  if (screenId.includes("architecture")) return "assessment.architecture";
  if (screenId.includes("controls")) return "assessment.controls";
  if (["it-business-impact", "ot-business-impact", "ot-loss-driver-assumptions", "outside-in-evidence", "it-assumptions-overrides", "ot-assumptions-overrides"].includes(screenId)) return "assessment.business_impact";
  if (screenId === "risk-appetite-insurance") return "assessment.risk_appetite_insurance";
  return "assessment.review";
}

function GuidanceMessage({icon: Icon, title, body}: {icon: typeof MessageCircle; title: string; body: string}) { return <article className="guidance-message"><span><Icon /></span><div><strong>{title}</strong><p>{body}</p></div></article>; }
