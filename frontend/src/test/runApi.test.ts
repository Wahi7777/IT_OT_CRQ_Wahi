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
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({status: "QUEUED"}), {status: 202, headers: {"Content-Type": "application/json"}}));
    const api = new HttpRunApi("https://crq.example");
    await api.submit(approvedRequests.IT, "governed-idempotency-key");
    expect(fetchMock).toHaveBeenCalledWith("https://crq.example/v1/assessments/run", expect.objectContaining({method: "POST", headers: expect.objectContaining({"Idempotency-Key": "governed-idempotency-key"})}));
    fetchMock.mockResolvedValue(new Response(JSON.stringify({status: "RUNNING"}), {status: 200, headers: {"Content-Type": "application/json"}}));
    await api.getStatus("run-1");
    expect(fetchMock).toHaveBeenLastCalledWith("https://crq.example/v1/runs/run-1", expect.any(Object));
    await api.getResult("run-1");
    expect(fetchMock).toHaveBeenLastCalledWith("https://crq.example/v1/runs/run-1/result", expect.any(Object));
  });
});
