import {fireEvent, render, waitFor, within} from "@testing-library/react";
import {beforeEach, describe, expect, it, vi} from "vitest";
import {AssessmentProvider} from "../features/assessment/AssessmentContext";
import {CopilotPanel} from "../features/assessment/CopilotPanel";

const query = vi.fn();
vi.mock("../api/CopilotApi", () => ({
  getCopilotApi: () => ({query}),
}));

describe("view-specific CRQ Copilot", () => {
  beforeEach(() => {
    query.mockReset();
    query.mockResolvedValue({status: "VERIFIED", answer: "Verified page-specific interpretation.", supporting_fact_ids: ["vf_test"]});
  });

  it("submits a suggested assessment question with automatic view context", async () => {
    const view = render(<AssessmentProvider><CopilotPanel screenId="it-architecture" /></AssessmentProvider>);
    fireEvent.click(within(view.container).getByRole("button", {name: "Why are we asking this?"}));
    await waitFor(() => expect(query).toHaveBeenCalled());
    expect(query.mock.calls[0][0]).toMatchObject({current_view: "assessment.architecture", run_id: null, question: "Why are we asking this?"});
    expect(query.mock.calls[0][1]).toMatchObject({assessment: {assessment_id: expect.any(String)}});
    expect(await within(view.container).findByText("Verified page-specific interpretation.")).toBeInTheDocument();
  });

  it("uses evidence-specific guidance and prompts on the supporting-evidence page", async () => {
    const view = render(<AssessmentProvider><CopilotPanel screenId="outside-in-evidence" /></AssessmentProvider>);
    expect(within(view.container).getByText("Add evidence where it strengthens the assessment.")).toBeInTheDocument();
    fireEvent.click(within(view.container).getByRole("button", {name: "Is supporting evidence optional?"}));
    await waitFor(() => expect(query).toHaveBeenCalled());
    expect(query.mock.calls[0][0]).toMatchObject({
      current_view: "assessment.business_impact",
      question: "Is supporting evidence optional?",
    });
  });

  it("attaches run and selected-entity context on a result question", async () => {
    const selected = {entity_type: "route", entity_id: "Insider or trusted access"};
    const view = render(<AssessmentProvider><CopilotPanel screenId="results-attack-paths" runId="run-123" selectedEntity={selected} /></AssessmentProvider>);
    const input = within(view.container).getByLabelText("Ask CRQ Copilot");
    fireEvent.change(input, {target: {value: "Why is this path open?"}});
    fireEvent.submit(input.closest("form")!);
    await waitFor(() => expect(query).toHaveBeenCalled());
    expect(query.mock.calls[0][0]).toMatchObject({current_view: "results.attack_paths", run_id: "run-123", selected_entity: selected});
    expect(query.mock.calls[0][1]).toBeUndefined();
  });

  it("never displays a rejected generated answer", async () => {
    query.mockResolvedValueOnce({status: "REJECTED", answer: "Unsupported $75M claim", supporting_fact_ids: []});
    const view = render(<AssessmentProvider><CopilotPanel screenId="results-overview" runId="run-123" /></AssessmentProvider>);
    fireEvent.click(within(view.container).getByRole("button", {name: "Explain headline metrics"}));
    expect(await within(view.container).findByText("Response not shown")).toBeInTheDocument();
    expect(within(view.container).queryByText("Unsupported $75M claim")).not.toBeInTheDocument();
  });
});
