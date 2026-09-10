import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { outputMappings, resultScreens } from "../contracts/governedData";
import { AssessmentProvider } from "../features/assessment/AssessmentContext";
import { ResultsPage } from "../pages/ResultsPage";

vi.mock("../api/RunApi", async () => {
  const { loadApprovedResult } = await import("../contracts/governedData");
  return { getRunApi: () => ({ getResult: () => loadApprovedResult("IT") }) };
});

const { copilotQuery } = vi.hoisted(() => ({ copilotQuery: vi.fn() }));

vi.mock("../api/CopilotApi", () => ({
  getCopilotApi: () => ({ query: copilotQuery }),
}));

describe("canonical result presentation", () => {
  beforeEach(() => {
    copilotQuery.mockReset();
    copilotQuery.mockResolvedValue({
      status: "VERIFIED",
      answer: "Verified against the selected governed route.",
    });
  });

  it("maps every canonical output family to a results screen", () => {
    for (const mapping of outputMappings) {
      expect(
        resultScreens.some((screen) =>
          screen.prefixes.some((prefix) =>
            mapping.canonical_path.startsWith(prefix),
          ),
        ),
        mapping.canonical_path,
      ).toBe(true);
    }
  });

  it("renders approved headline metrics without calculating replacements", async () => {
    render(
      <MemoryRouter initialEntries={["/results/demo/overview"]}>
        <AssessmentProvider>
          <Routes>
            <Route path="/results/:runId/:page" element={<ResultsPage />} />
          </Routes>
        </AssessmentProvider>
      </MemoryRouter>,
    );
    expect(await screen.findByText("Prudent AAL")).toBeInTheDocument();
    expect(screen.getByText("VaR 95")).toBeInTheDocument();
    expect(screen.getByText("VaR 99")).toBeInTheDocument();
    expect(screen.getByText("TVaR 95")).toBeInTheDocument();
    expect(screen.getByText("TVaR 99")).toBeInTheDocument();
    expect(screen.getByText("CRQ Copilot")).toBeInTheDocument();
    expect(
      screen.queryByText("AI Risk Interpretation"),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("link", { name: "Uncertainty" }),
    ).not.toBeInTheDocument();
    expect(screen.getByText("Tail-loss anchors")).toBeInTheDocument();
    expect(screen.getByText(/no intermediate values are inferred/i)).toBeInTheDocument();
  });

  it("does not invent a treatment benefit absent from the approved result", async () => {
    render(
      <MemoryRouter initialEntries={["/results/demo/treatment"]}>
        <AssessmentProvider>
          <Routes>
            <Route path="/results/:runId/:page" element={<ResultsPage />} />
          </Routes>
        </AssessmentProvider>
      </MemoryRouter>,
    );
    expect(
      await screen.findByText(
        "No control-uplift benefit is present in this result",
      ),
    ).toBeInTheDocument();
    expect(screen.getAllByText("No modelled change").length).toBeGreaterThan(0);
  });

  it("switches treatment values between governed AAL and TVaR measures", async () => {
    render(
      <MemoryRouter initialEntries={["/results/demo/treatment"]}>
        <AssessmentProvider>
          <Routes>
            <Route path="/results/:runId/:page" element={<ResultsPage />} />
          </Routes>
        </AssessmentProvider>
      </MemoryRouter>,
    );
    fireEvent.click(await screen.findByRole("button", { name: "TVaR95" }));
    expect(screen.getByText("Current TVaR95")).toBeInTheDocument();
    expect(screen.getByText("Post-treatment TVaR95")).toBeInTheDocument();
  });

  it("shows both governed tail-contribution columns for scenarios", async () => {
    const view = render(
      <MemoryRouter initialEntries={["/results/demo/scenarios"]}>
        <AssessmentProvider>
          <Routes>
            <Route path="/results/:runId/:page" element={<ResultsPage />} />
          </Routes>
        </AssessmentProvider>
      </MemoryRouter>,
    );
    expect(
      await within(view.container).findByText("TVaR95 contribution"),
    ).toBeInTheDocument();
    expect(
      within(view.container).getByText("TVaR99 contribution"),
    ).toBeInTheDocument();
  });

  it("labels loss drivers by category and offers governed chart measures", async () => {
    const view = render(
      <MemoryRouter initialEntries={["/results/demo/business-impact"]}>
        <AssessmentProvider>
          <Routes>
            <Route path="/results/:runId/:page" element={<ResultsPage />} />
          </Routes>
        </AssessmentProvider>
      </MemoryRouter>,
    );
    expect(
      (await within(view.container).findAllByText("Indirect Losses")).length,
    ).toBeGreaterThan(1);
    const tvar99 = within(view.container).getByRole("button", {
      name: "TVaR99",
    });
    fireEvent.click(tvar99);
    expect(tvar99).toHaveAttribute("aria-pressed", "true");
  });

  it("passes the selected attack route into a Copilot query", async () => {
    render(
      <MemoryRouter initialEntries={["/results/demo/attack-paths"]}>
        <AssessmentProvider>
          <Routes>
            <Route path="/results/:runId/:page" element={<ResultsPage />} />
          </Routes>
        </AssessmentProvider>
      </MemoryRouter>,
    );

    const routeSelect = (await screen.findByLabelText("Route")) as HTMLSelectElement;
    const selectedRoute = routeSelect.options[1]?.value;
    expect(selectedRoute).toBeTruthy();
    fireEvent.change(routeSelect, { target: { value: selectedRoute } });
    fireEvent.click(screen.getByRole("button", { name: "Why is this path open?" }));

    await waitFor(() => {
      expect(copilotQuery).toHaveBeenCalledWith(
        expect.objectContaining({
          current_view: "results.attack_paths",
          selected_entity: {
            entity_type: "route",
            entity_id: selectedRoute,
          },
        }),
        undefined,
      );
    });
  });
});
