import {describe, expect, it} from "vitest";
import {approvedRequests} from "../contracts/governedData";
import {validateRunRequest} from "../contracts/validation";

describe("governed request validation", () => {
  it.each(["IT", "OT"] as const)("accepts the approved %s request artifact", (domain) => {
    expect(validateRunRequest(approvedRequests[domain])).toEqual([]);
  });

  it("rejects an invalid run configuration instead of submitting it", () => {
    const invalid = structuredClone(approvedRequests.IT);
    invalid.run_config.simulation_count = 1;
    expect(validateRunRequest(invalid)).toEqual(expect.arrayContaining([
      expect.objectContaining({path: "/run_config/simulation_count", keyword: "minimum"})
    ]));
  });

  it("rejects a sector and governed pack mismatch", () => {
    const invalid = structuredClone(approvedRequests.OT);
    invalid.assessment.assessment.sector = "Manufacturing";
    expect(validateRunRequest(invalid)).toEqual(expect.arrayContaining([
      expect.objectContaining({path: "/model_bundle_reference/bundle_id", keyword: "packCompatibility"})
    ]));
  });

  it("reports only the selected domain's input errors", () => {
    const invalid = structuredClone(approvedRequests.IT);
    invalid.assessment.domain_inputs.financial_exposure.annual_revenue_at_risk = "1000000";
    const issues = validateRunRequest(invalid);
    expect(issues).toEqual(expect.arrayContaining([
      expect.objectContaining({path: "/assessment/domain_inputs/financial_exposure/annual_revenue_at_risk", keyword: "type"})
    ]));
    expect(issues).not.toEqual(expect.arrayContaining([
      expect.objectContaining({message: expect.stringContaining("facility")})
    ]));
    expect(issues).not.toEqual(expect.arrayContaining([
      expect.objectContaining({message: expect.stringContaining("topology")})
    ]));
  });
});
