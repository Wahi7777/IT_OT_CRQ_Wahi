import {afterEach, describe, expect, it, vi} from "vitest";
import {saveAssessmentDraft} from "../api/AssessmentApi";
import {approvedRequests} from "../contracts/governedData";

describe("assessment draft persistence", () => {
  afterEach(() => vi.restoreAllMocks());

  it("increments the stored version before replacing a changed assessment", async () => {
    const current = structuredClone(approvedRequests.IT.assessment);
    current.assessment.assessment_version = 4;
    const changed = structuredClone(current);
    changed.assessment.organisation = "Updated organisation";
    const fetchMock = vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(new Response(JSON.stringify({assessment: current}), {status: 200, headers: {"Content-Type": "application/json"}}))
      .mockResolvedValueOnce(new Response(JSON.stringify({assessment: {...changed, assessment: {...changed.assessment, assessment_version: 5}}}), {status: 200, headers: {"Content-Type": "application/json"}}));

    const saved = await saveAssessmentDraft("https://crq.example", "token", changed);

    expect(saved.assessment.assessment_version).toBe(5);
    const body = JSON.parse(String(fetchMock.mock.calls[1][1]?.body));
    expect(body.assessment.assessment_version).toBe(5);
  });

  it("does not create another version when the stored assessment is unchanged", async () => {
    const current = structuredClone(approvedRequests.IT.assessment);
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(new Response(JSON.stringify({assessment: current}), {status: 200, headers: {"Content-Type": "application/json"}}));
    await saveAssessmentDraft("https://crq.example", "token", current);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});
