import {afterEach, describe, expect, it, vi} from "vitest";
import {DemoRunApi, HttpRunApi} from "../api/RunApi";
import {approvedRequests} from "../contracts/governedData";

describe("asynchronous run adapters", () => {
  afterEach(() => vi.restoreAllMocks());

  it("moves a demo run through the governed lifecycle", async () => {
    vi.useFakeTimers();
    const api = new DemoRunApi();
    const acceptedPromise = api.submit(approvedRequests.IT, "0123456789abcdef0123456789abcdef");
    await vi.advanceTimersByTimeAsync(500);
    const accepted = await acceptedPromise;
    expect(accepted.status).toBe("QUEUED");
    const states = [];
    for (let i = 0; i < 4; i += 1) {
      const statusPromise = api.getStatus(accepted.run_id);
      await vi.advanceTimersByTimeAsync(250);
      states.push((await statusPromise).status);
    }
    expect(states).toEqual(["QUEUED", "RUNNING", "RUNNING", "COMPLETED"]);
    vi.useRealTimers();
  });

  it("uses the exact governed HTTP routes and idempotency header", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(new Response(JSON.stringify({message: "Not found"}), {status: 404, headers: {"Content-Type": "application/json"}}))
      .mockResolvedValueOnce(new Response(JSON.stringify({assessment: approvedRequests.IT.assessment}), {status: 201, headers: {"Content-Type": "application/json"}}))
      .mockResolvedValueOnce(new Response(JSON.stringify({status: "QUEUED"}), {status: 202, headers: {"Content-Type": "application/json"}}));
    const api = new HttpRunApi("https://crq.example", () => "verified-id-token");
    await api.submit(approvedRequests.IT, "governed-idempotency-key");
    expect(fetchMock).toHaveBeenNthCalledWith(1, `https://crq.example/v1/assessments/${approvedRequests.IT.assessment.assessment.assessment_id}`, expect.objectContaining({headers: expect.any(Object)}));
    expect(fetchMock).toHaveBeenNthCalledWith(2, "https://crq.example/v1/assessments", expect.objectContaining({method: "POST"}));
    expect(fetchMock).toHaveBeenNthCalledWith(3, `https://crq.example/v1/assessments/${approvedRequests.IT.assessment.assessment.assessment_id}/run`, expect.objectContaining({method: "POST"}));
    const submitHeaders = fetchMock.mock.calls[2][1]?.headers as Headers;
    expect(submitHeaders.get("Idempotency-Key")).toBe("governed-idempotency-key");
    expect(submitHeaders.get("Authorization")).toBe("Bearer verified-id-token");
    fetchMock.mockResolvedValue(new Response(JSON.stringify({status: "RUNNING"}), {status: 200, headers: {"Content-Type": "application/json"}}));
    await api.getStatus("run-1");
    expect(fetchMock).toHaveBeenLastCalledWith("https://crq.example/v1/runs/run-1", expect.objectContaining({headers: expect.any(Headers)}));
    await api.getResult("run-1");
    expect(fetchMock).toHaveBeenLastCalledWith("https://crq.example/v1/runs/run-1/result", expect.any(Object));
  });
});
