import {describe, expect, it} from "vitest";
import {getSteps} from "../features/assessment/AssessmentShell";

describe("assessment journey", () => {
  it("does not send OT users through the obsolete loss-driver assumptions page", () => {
    const steps = getSteps("OT");
    expect(steps).not.toContain("ot-loss-driver-assumptions");
    expect(steps).toContain("ot-business-impact");
    expect(steps).toContain("outside-in-evidence");
  });
});
