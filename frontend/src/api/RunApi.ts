import {approvedRequests, approvedResults} from "../contracts/governedData";
import type {AssessmentRunRequest, CRQResult, Domain, RunAccepted, RunApi, RunStatus} from "../contracts/types";

type DemoRun = {domain: Domain; polls: number; submittedAt: string; failed: boolean};

export class DemoRunApi implements RunApi {
  private runs = new Map<string, DemoRun>();

  async submit(request: AssessmentRunRequest, idempotencyKey: string): Promise<RunAccepted> {
    await delay(450);
    const runId = deterministicUuid(idempotencyKey);
    const submittedAt = new Date().toISOString();
    this.runs.set(runId, {domain: request.assessment.assessment.domain, polls: 0, submittedAt, failed: false});
    return {
      schema_version: "1.0.0-draft",
      run_id: runId,
      assessment_id: request.assessment.assessment.assessment_id,
      status: "QUEUED",
      submitted_at: submittedAt,
      links: {status: `/v1/runs/${runId}`, result: `/v1/runs/${runId}/result`}
    };
  }

  async getStatus(runId: string): Promise<RunStatus> {
    await delay(220);
    const run = this.runs.get(runId) ?? {domain: inferDomain(), polls: 3, submittedAt: new Date().toISOString(), failed: false};
    run.polls += 1;
    this.runs.set(runId, run);
    const status = run.failed ? "FAILED" : run.polls < 2 ? "QUEUED" : run.polls < 4 ? "RUNNING" : "COMPLETED";
    return {
      schema_version: "1.0.0-draft",
      run_id: runId,
      assessment_id: approvedRequests[run.domain].assessment.assessment.assessment_id,
      status,
      submitted_at: run.submittedAt,
      started_at: run.polls >= 2 ? run.submittedAt : null,
      completed_at: status === "COMPLETED" ? new Date().toISOString() : null,
      updated_at: new Date().toISOString(),
      phase: status === "RUNNING" ? (run.polls === 2 ? "VALIDATING" : "EXECUTING") : null,
      failure: status === "FAILED" ? {code: "EXECUTION_FAILED", message: "The governed run could not be completed.", retryable: true, correlation_id: runId} : null,
      links: {status: `/v1/runs/${runId}`, result: `/v1/runs/${runId}/result`}
    };
  }

  async getResult(runId: string): Promise<CRQResult> {
    await delay(260);
    const domain = this.runs.get(runId)?.domain ?? inferDomain();
    return structuredClone(approvedResults[domain]);
  }
}

export class HttpRunApi implements RunApi {
  constructor(private baseUrl: string) {}

  submit(request: AssessmentRunRequest, idempotencyKey: string) {
    return this.request<RunAccepted>("/v1/assessments/run", {
      method: "POST",
      headers: {"Content-Type": "application/json", "Idempotency-Key": idempotencyKey},
      body: JSON.stringify(request)
    });
  }

  getStatus(runId: string) {
    return this.request<RunStatus>(`/v1/runs/${encodeURIComponent(runId)}`);
  }

  getResult(runId: string) {
    return this.request<CRQResult>(`/v1/runs/${encodeURIComponent(runId)}/result`);
  }

  private async request<T>(path: string, init?: RequestInit): Promise<T> {
    const response = await fetch(`${this.baseUrl.replace(/\/$/, "")}${path}`, {cache: "no-store", ...init});
    const body = await response.json().catch(() => null);
    if (!response.ok) throw new Error(body?.message ?? `Request failed (${response.status})`);
    return body as T;
  }
}

function inferDomain(): Domain {
  const requested = new URLSearchParams(window.location.search).get("domain");
  return requested === "OT" || window.location.pathname.toLowerCase().includes("ot") ? "OT" : "IT";
}

function deterministicUuid(value: string) {
  const chars = value.replace(/[^a-f0-9]/gi, "").padEnd(32, "0").slice(0, 32).toLowerCase();
  return `${chars.slice(0, 8)}-${chars.slice(8, 12)}-4${chars.slice(13, 16)}-a${chars.slice(17, 20)}-${chars.slice(20, 32)}`;
}

function delay(ms: number) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

export function createRunApi(mode: "demo" | "api") {
  return mode === "api" ? new HttpRunApi(import.meta.env.VITE_CRQ_API_BASE_URL ?? "") : new DemoRunApi();
}

const clients: Partial<Record<"demo" | "api", RunApi>> = {};
export function getRunApi(mode: "demo" | "api") {
  return clients[mode] ?? (clients[mode] = createRunApi(mode));
}
