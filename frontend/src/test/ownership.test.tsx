import {render, screen} from "@testing-library/react";
import {describe, expect, it} from "vitest";
import {approvedRequests, fieldInventory, inputScreens, inventoryForScreen} from "../contracts/governedData";
import {AssessmentProvider} from "../features/assessment/AssessmentContext";
import {FieldGroup} from "../features/assessment/FieldCard";
import {expandField} from "../features/assessment/fieldExpansion";

describe("governed input ownership", () => {
  it("places every inventory entry on exactly one domain-appropriate screen", () => {
    for (const item of fieldInventory) {
      for (const domain of item.domain === "common" ? ["IT", "OT"] as const : [item.domain]) {
        const screens = inputScreens.filter((candidate) => candidate.applies_to.includes(domain) && candidate.canonical_paths.includes(item.canonical_path));
        expect(screens, `${domain} ${item.canonical_path}`).toHaveLength(1);
      }
    }
  });

  it("never renders a governed pack field as editable", () => {
    const item = fieldInventory.find((field) => field.classification === "GOVERNED_PACK_INPUT" && !field.frontend.hidden)!;
    const {container} = render(<AssessmentProvider><FieldGroup item={item} /></AssessmentProvider>);
    expect(screen.getByText(/governed pack input/i)).toBeInTheDocument();
    expect(screen.getByText(/approved immutable model bundle/i)).toBeInTheDocument();
    expect(container.querySelector("input, select, textarea")).not.toBeInTheDocument();
  });

  it("keeps inactive legacy fields read-only", () => {
    const item = fieldInventory.find((field) => field.classification === "INACTIVE_LEGACY" && !field.frontend.hidden)!;
    const {container} = render(<AssessmentProvider><FieldGroup item={item} /></AssessmentProvider>);
    expect(screen.getByText(/excluded from quantitative execution/i)).toBeInTheDocument();
    expect(container.querySelector("input, select, textarea")).not.toBeInTheDocument();
  });

  it("renders active user inputs as controls", () => {
    const item = inventoryForScreen("assessment-setup", "IT").find((field) => field.canonical_path === "assessment.domain")!;
    const {container} = render(<AssessmentProvider><FieldGroup item={item} /></AssessmentProvider>);
    expect(container.querySelector("select")).toBeInTheDocument();
  });

  it("resolves every active editable inventory record to a concrete governed control", () => {
    for (const item of fieldInventory.filter((candidate) => candidate.frontend.editable && !candidate.inert)) {
      for (const domain of item.domain === "common" ? ["IT", "OT"] as const : [item.domain]) {
        const fields = expandField(item, approvedRequests[domain], {tvar_selection: "TVaR99"});
        const hasCollectionEditor = item.canonical_path.startsWith("insurance.layers");
        expect(fields.some((field) => Boolean(field.path)) || hasCollectionEditor, `${domain} ${item.canonical_path}`).toBe(true);
      }
    }
  });

  it("offers a canonical editor when the approved insurance layer collection is empty", () => {
    const item = fieldInventory.find((field) => field.canonical_path.startsWith("insurance.layers"))!;
    render(<AssessmentProvider><FieldGroup item={item} /></AssessmentProvider>);
    expect(screen.getByRole("button", {name: /add insurance layer/i})).toBeInTheDocument();
  });
});
