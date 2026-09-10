import {clearSession, getIdToken} from "../auth/CognitoAuth";
import {saveAssessmentDraft} from "./AssessmentApi";

export type CopilotState = "IDLE" | "THINKING" | "VERIFIED" | "FAILED" | "REJECTED";
export interface CopilotQuery {
  assessment_id: string;
  run_id?: string | null;
  current_view: string;
  selected_entity?: {entity_type: string; entity_id: string} | null;
  question: string;
}
export interface CopilotReply {
  status: "VERIFIED" | "REJECTED";
  answer: string | null;
  supporting_fact_ids: string[];
  key_points?: string[];
  caveats?: string[];
  error_code?: string;
}

interface CopilotApi { query(request: CopilotQuery, assessment?: Record<string, any>): Promise<CopilotReply>; }

class HttpCopilotApi implements CopilotApi {
  constructor(private baseUrl: string, private tokenProvider: () => string | null = getIdToken) {}
  async query(request: CopilotQuery, assessment?: Record<string, any>): Promise<CopilotReply> {
    const token = this.tokenProvider();
    if (!token) {
      window.location.assign("/login?expired=1");
      throw new Error("An authenticated session is required.");
    }
    if (!request.current_view.startsWith("results.") && assessment) await saveAssessmentDraft(this.baseUrl, token, assessment as any);
    const response = await fetch(`${this.baseUrl.replace(/\/$/, "")}/v1/copilot/query`, {
      method: "POST",
      cache: "no-store",
      headers: {Authorization: `Bearer ${token}`, "Content-Type": "application/json"},
      body: JSON.stringify(request),
    });
    const body = await response.json().catch(() => null);
    if (response.status === 401 || response.status === 403) {
      clearSession();
      window.location.assign("/login?expired=1");
    }
    if (!response.ok) throw new Error(body?.message ?? `Copilot request failed (${response.status})`);
    return body as CopilotReply;
  }
}

class DemoCopilotApi implements CopilotApi {
  async query(request: CopilotQuery): Promise<CopilotReply> {
    await new Promise((resolve) => window.setTimeout(resolve, 450));
    return {
      status: "VERIFIED",
      answer: `This demo response is limited to ${request.current_view.replaceAll("_", " ").replace(".", " — ")}. Connect REAL_API mode for a Bedrock interpretation verified against stored model facts.`,
      supporting_fact_ids: ["demo_context_only"],
    };
  }
}

const clients: Partial<Record<"demo" | "api", CopilotApi>> = {};
export function getCopilotApi(mode: "demo" | "api"): CopilotApi {
  return clients[mode] ?? (clients[mode] = mode === "api" ? new HttpCopilotApi(import.meta.env.VITE_CRQ_API_BASE_URL ?? "") : new DemoCopilotApi());
}
