import {AlertTriangle, Check, Clock3, Cpu, Database, RotateCw} from "lucide-react";
import {useEffect, useRef, useState} from "react";
import {useNavigate, useParams, useSearchParams} from "react-router-dom";
import {getRunApi} from "../api/RunApi";
import {PageHeader} from "../components/PageHeader";
import {Badge, Button, GlassPanel} from "../components/ui";
import type {ClientRunState, RunStatus} from "../contracts/types";
import {useAssessment} from "../features/assessment/AssessmentContext";

export function RunPage() {
  const {runId = ""} = useParams();
  const [params] = useSearchParams();
  const {dataMode, setDomain} = useAssessment();
  const [status, setStatus] = useState<ClientRunState>("QUEUED");
  const [detail, setDetail] = useState<RunStatus | null>(null);
  const [transportError, setTransportError] = useState<string | null>(null);
  const navigate = useNavigate();
  const completed = useRef(false);

  useEffect(() => {
    const domain = params.get("domain");
    if (domain === "IT" || domain === "OT") setDomain(domain);
  }, [params, setDomain]);

  useEffect(() => {
    let active = true;
    let timer: number;
    const poll = async () => {
      try {
        const next = await getRunApi(dataMode).getStatus(runId);
        if (!active) return;
        setDetail(next); setStatus(next.status); setTransportError(null);
        if (next.status === "COMPLETED" && !completed.current) {
          completed.current = true;
          await getRunApi(dataMode).getResult(runId);
          window.setTimeout(() => navigate(`/results/${runId}/overview`), 500);
          return;
        }
        if (next.status !== "FAILED") timer = window.setTimeout(poll, 2500);
      } catch (reason) {
        if (!active) return;
        setTransportError(reason instanceof Error ? reason.message : "Status is temporarily unavailable.");
        timer = window.setTimeout(poll, 5000);
      }
    };
    poll();
    return () => {active = false; window.clearTimeout(timer);};
  }, [dataMode, navigate, runId]);

  const phases = [
    {state: "QUEUED", label: "Request accepted", icon: Clock3},
    {state: "RUNNING", label: "Risk analysis", icon: Cpu},
    {state: "COMPLETED", label: "Result prepared", icon: Database}
  ];
  const order = status === "QUEUED" ? 0 : status === "RUNNING" ? 1 : status === "COMPLETED" ? 2 : -1;
  return <div className="run-page">
    <PageHeader eyebrow="Run execution" title={status === "FAILED" ? "Run needs attention" : status === "COMPLETED" ? "Result ready" : "Quantification in progress"} description="This page can be safely closed. The run identifier preserves your place." />
    <GlassPanel className={`run-focus ${status === "FAILED" ? "run-focus--failed" : ""}`}>
      <div className={`run-orbit ${["QUEUED", "RUNNING"].includes(status) ? "pulse" : ""}`}>{status === "FAILED" ? <AlertTriangle /> : status === "COMPLETED" ? <Check /> : <Cpu />}</div>
      <Badge tone={status === "FAILED" ? "red" : status === "COMPLETED" ? "green" : status === "QUEUED" ? "amber" : "indigo"}>{status}</Badge>
      <h2>{statusCopy[status].title}</h2><p>{detail?.phase ? `${detail.phase.toLowerCase().replace("_", " ")} · ` : ""}{statusCopy[status].body}</p>
      <code>{runId}</code>
      {transportError && <div className="error-banner" role="alert">{transportError}</div>}
      {detail?.failure && <div className="failure-card"><strong>{detail.failure.code}</strong><p>{detail.failure.message}</p><small>Correlation ID · {detail.failure.correlation_id}</small></div>}
    </GlassPanel>
    <div className="run-timeline">
      {phases.map((phase, index) => <div className={`run-phase ${index < order ? "complete" : index === order ? "active" : ""}`} key={phase.state}><span><phase.icon /></span><div><small>0{index + 1}</small><strong>{phase.label}</strong><em>{index < order ? "Complete" : index === order ? status : "Pending"}</em></div></div>)}
    </div>
    <GlassPanel className="run-note"><RotateCw /><div><strong>Status refreshes automatically</strong><p>You can safely leave this page and return while the assessment runs.</p></div></GlassPanel>
    {status === "FAILED" && <Button onClick={() => window.location.reload()}>Retry status check</Button>}
  </div>;
}

const statusCopy: Record<ClientRunState, {title: string; body: string}> = {
  SUBMITTING: {title: "Submitting assessment", body: "Validating the request envelope."},
  QUEUED: {title: "Your assessment is queued", body: "We’ll begin the analysis as soon as processing capacity is available."},
  RUNNING: {title: "Running your cyber risk assessment", body: "Analysing scenarios and loss distributions. No progress percentage is inferred."},
  COMPLETED: {title: "Your result is ready", body: "The assessment completed successfully and is ready to explore."},
  FAILED: {title: "Run could not complete", body: "The assessment remains available. Use the safe reference below when requesting support."}
};
