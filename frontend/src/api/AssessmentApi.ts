import {clearSession} from "../auth/CognitoAuth";

type AssessmentPayload = Record<string, any> & {
  assessment: {assessment_id: string; assessment_version: number};
};

export async function saveAssessmentDraft(baseUrl: string, token: string, assessment: AssessmentPayload) {
  const root = baseUrl.replace(/\/$/, "");
  const id = encodeURIComponent(assessment.assessment.assessment_id);
  const existingResponse = await fetch(`${root}/v1/assessments/${id}`, {
    cache: "no-store",
    headers: {Authorization: `Bearer ${token}`},
  });
  if (existingResponse.status === 401 || existingResponse.status === 403) return expireSession();
  let payload = structuredClone(assessment);
  if (existingResponse.ok) {
    const existing = (await existingResponse.json()).assessment as AssessmentPayload;
    const currentVersion = Number(existing.assessment.assessment_version);
    payload.assessment.assessment_version = currentVersion;
    if (stableJson(payload) === stableJson(existing)) return existing;
    payload.assessment.assessment_version = currentVersion + 1;
  } else if (existingResponse.status !== 404) {
    throw await responseError(existingResponse, "Assessment could not be loaded.");
  }
  const saved = await fetch(`${root}/v1/assessments`, {
    method: "POST",
    cache: "no-store",
    headers: {Authorization: `Bearer ${token}`, "Content-Type": "application/json"},
    body: JSON.stringify(payload),
  });
  if (saved.status === 401 || saved.status === 403) return expireSession();
  if (!saved.ok) throw await responseError(saved, "Assessment could not be saved.");
  return ((await saved.json()).assessment ?? payload) as AssessmentPayload;
}

function stableJson(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(stableJson).join(",")}]`;
  if (value && typeof value === "object") return `{${Object.entries(value as Record<string, unknown>).sort(([a], [b]) => a.localeCompare(b)).map(([key, item]) => `${JSON.stringify(key)}:${stableJson(item)}`).join(",")}}`;
  return JSON.stringify(value) ?? "null";
}

async function responseError(response: Response, fallback: string) {
  const body = await response.json().catch(() => null);
  return new Error(body?.message ?? fallback);
}

function expireSession(): never {
  clearSession();
  window.location.assign("/login?expired=1");
  throw new Error("An authenticated session is required.");
}
