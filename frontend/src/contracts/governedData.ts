import itRequestJson from "../../../contracts/examples/assessment-run-request-it-fs.json";
import otRequestJson from "../../../contracts/examples/assessment-run-request-ot-pg.json";
import inventoryJson from "../../../contracts/mappings/field-inventory.json";
import outputMappingJson from "../../../contracts/mappings/engine-output-to-crq-result.json";
import placementJson from "../../../contracts/frontend/frontend-placement.json";
import registryJson from "../../../config/sector_pack_registry.json";
import type {AssessmentRunRequest, CRQResult, Domain, FieldInventoryItem, PlacementScreen} from "./types";

export const approvedRequests = {
  IT: structuredClone(itRequestJson) as AssessmentRunRequest,
  OT: structuredClone(otRequestJson) as AssessmentRunRequest
};

export async function loadApprovedResult(domain: Domain): Promise<CRQResult> {
  const module = domain === "IT"
    ? await import("../../../contracts/examples/assessment-run-response-it-fs.json")
    : await import("../../../contracts/examples/assessment-run-response-ot-pg.json");
  return structuredClone(module.default.result) as CRQResult;
}

export const fieldInventory = inventoryJson.fields as FieldInventoryItem[];
export const inputScreens = placementJson.input_screens as PlacementScreen[];
export const resultScreens = placementJson.results_screens;
export const outputMappings = outputMappingJson.mappings;
export const sectorPacks = registryJson.packs;

export const editableClasses = new Set(["USER_INPUT", "PERMITTED_OVERRIDE"]);

export function inventoryForScreen(screenId: string, domain: "IT" | "OT") {
  const placement = inputScreens.find((screen) => screen.screen_id === screenId);
  if (!placement) return [];
  return fieldInventory.filter((field) => {
    const domainMatch = field.domain === "common" || field.domain === domain;
    return domainMatch && placement.canonical_paths.includes(field.canonical_path) && !field.frontend.hidden;
  });
}

export const routeLabels: Record<string, string> = {
  "assessment-setup": "Assessment setup",
  "organisation-exposure": "Organisation & exposure",
  facility: "Facility",
  "it-architecture": "Architecture",
  "ot-architecture-topology": "OT architecture & topology",
  "it-controls": "Controls",
  "ot-controls": "OT controls",
  "it-business-impact": "Business impact",
  "ot-business-impact": "Business impact",
  "ot-loss-driver-assumptions": "Loss-driver assumptions",
  "it-assumptions-overrides": "Assumptions & overrides",
  "ot-assumptions-overrides": "Assumptions & overrides",
  "outside-in-evidence": "Outside-in evidence",
  "risk-appetite-insurance": "Risk appetite & insurance",
  "review-run": "Review & Run"
};
