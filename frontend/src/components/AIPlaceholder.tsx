import {Sparkles} from "lucide-react";
import {useState} from "react";
import type {AIState} from "../contracts/types";
import {Badge, Button, GlassPanel} from "./ui";

export function AIPlaceholder() {
  const [state, setState] = useState<AIState>("NOT_GENERATED");
  const generate = () => {
    setState("GENERATING");
    window.setTimeout(() => setState("READY"), 1500);
  };
  return <GlassPanel className="ai-panel">
    <div className={`ai-icon ${state === "GENERATING" || state === "READY" ? "pulse" : ""}`}><Sparkles aria-hidden="true" /></div>
    <div className="ai-copy"><div className="panel-title-row"><h2>AI Risk Interpretation</h2><Badge tone={state === "FAILED" ? "red" : state === "READY" ? "green" : "indigo"}>{state.replace("_", " ")}</Badge></div>
      <p>This governed placeholder will later receive deterministic facts only. It does not calculate or infer CRQ metrics.</p>
    </div>
    <Button variant="secondary" onClick={generate} disabled={state === "GENERATING"}>{state === "READY" ? "View placeholder" : state === "GENERATING" ? "Preparing…" : "Generate placeholder"}</Button>
  </GlassPanel>;
}
