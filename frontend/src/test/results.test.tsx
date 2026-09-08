import {render, screen} from "@testing-library/react";
import {MemoryRouter, Route, Routes} from "react-router-dom";
import {describe, expect, it} from "vitest";
import {outputMappings, resultScreens} from "../contracts/governedData";
import {AssessmentProvider} from "../features/assessment/AssessmentContext";
import {ResultsPage} from "../pages/ResultsPage";

describe("canonical result presentation", () => {
  it("maps every canonical output family to a results screen", () => {
    for (const mapping of outputMappings) {
      expect(resultScreens.some((screen) => screen.prefixes.some((prefix) => mapping.canonical_path.startsWith(prefix))), mapping.canonical_path).toBe(true);
    }
  });

  it("renders approved headline metrics without calculating replacements", async () => {
    render(<MemoryRouter initialEntries={["/results/demo/overview"]}><AssessmentProvider><Routes><Route path="/results/:runId/:page" element={<ResultsPage />} /></Routes></AssessmentProvider></MemoryRouter>);
    expect(await screen.findByText("Prudent AAL")).toBeInTheDocument();
    expect(screen.getByText("VaR 99")).toBeInTheDocument();
    expect(screen.getByText("TVaR 99")).toBeInTheDocument();
    expect(screen.getByText("AI Risk Interpretation")).toBeInTheDocument();
    expect(screen.getByText(/does not calculate or infer CRQ metrics/i)).toBeInTheDocument();
  });
});
