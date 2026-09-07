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
});
