import Ajv2020, {type ErrorObject} from "ajv/dist/2020";
import assessmentSchema from "../../../contracts/schemas/crq-assessment.schema.json";
import runRequestSchema from "../../../contracts/schemas/assessment-run-request.schema.json";
import type {AssessmentRunRequest} from "./types";
import {sectorPacks} from "./governedData";

const ajv = new Ajv2020({allErrors: true, strict: false});
ajv.addFormat("date", /^\d{4}-\d{2}-\d{2}$/);
ajv.addFormat("date-time", {type: "string", validate: (value: string) => !Number.isNaN(Date.parse(value))});
ajv.addSchema(assessmentSchema);
const validate = ajv.compile<AssessmentRunRequest>(runRequestSchema);
const assessmentSchemaId = "https://crq.local/contracts/crq-assessment/1.0.0-draft";
const validateItInputs = ajv.compile({$ref: `${assessmentSchemaId}#/$defs/itInputs`});
const validateOtInputs = ajv.compile({$ref: `${assessmentSchemaId}#/$defs/otInputs`});

export interface ContractValidationIssue {
  path: string;
  message: string;
  keyword: string;
}

function issueFrom(error: ErrorObject): ContractValidationIssue {
  return {
    path: error.instancePath || "/",
    message: error.message ?? "does not satisfy the governed contract",
    keyword: error.keyword
  };
}

/** Validate only against the governed request contract; this never calculates model values. */
export function validateRunRequest(request: AssessmentRunRequest): ContractValidationIssue[] {
  const valid = validate(request);
  const issues = valid ? [] : (validate.errors ?? [])
    .filter((error) => !error.instancePath.startsWith("/assessment/domain_inputs"))
    .map(issueFrom);
  const validateDomainInputs = request.assessment.assessment.domain === "OT" ? validateOtInputs : validateItInputs;
  if (!validateDomainInputs(request.assessment.domain_inputs)) {
    issues.push(...(validateDomainInputs.errors ?? []).map((error) => ({
      ...issueFrom(error),
      path: `/assessment/domain_inputs${error.instancePath}`
    })));
  }
  const identity = request.assessment.assessment;
  const pack = sectorPacks.find((candidate) => candidate.domain === identity.domain && candidate.sector === identity.sector);
  if (!pack || pack.pack_id !== request.model_bundle_reference.bundle_id) {
    issues.push({path: "/model_bundle_reference/bundle_id", message: "is incompatible with the selected domain and sector", keyword: "packCompatibility"});
  }
  return issues;
}
