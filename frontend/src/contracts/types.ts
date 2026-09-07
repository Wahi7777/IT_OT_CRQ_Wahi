export type Domain = "IT" | "OT";
export type Ownership =
  | "USER_INPUT"
  | "GOVERNED_PACK_INPUT"
  | "PERMITTED_OVERRIDE"
  | "DERIVED"
  | "EVIDENCE_ONLY"
  | "DISPLAY_ONLY"
  | "INACTIVE_LEGACY";

export type RunState = "QUEUED" | "RUNNING" | "COMPLETED" | "FAILED";
export type ClientRunState = "SUBMITTING" | RunState;
export type AIState = "NOT_GENERATED" | "GENERATING" | "READY" | "FAILED";

export interface FieldInventoryItem {
  canonical_path: string;
  item_keys?: string[];
  parameter_keys?: string[];
  domain: "common" | Domain;
  source: string;
  location: string;
  datatype: string;
  allowed_values?: unknown[] | Record<string, unknown[]> | string;
  required: boolean;
  default?: unknown;
  validation: string;
  consumer: string;
  affected_results: string[];
  classification: Ownership;
  frontend: {editable: boolean; read_only: boolean; hidden: boolean};
  inert: boolean;
}

export interface PlacementScreen {
  screen_id: string;
  applies_to: Domain[];
  canonical_paths: string[];
  classification_disambiguation?: string;
  summary_rule?: string;
}

export interface AssessmentRunRequest {
  schema_version: string;
  request_id: string;
  assessment: Record<string, any> & {
    assessment: {
      assessment_id: string;
      assessment_version: number;
      domain: Domain;
      sector: string;
      asset_type: string;
      reporting_basis: string;
      organisation?: string | null;
      currency?: string | null;
    };
    runtime: {simulation_count: number; random_seed: number; [key: string]: unknown};
    domain_inputs: Record<string, any>;
  };
  model_bundle_reference: {bundle_id: string; bundle_version: string};
  run_config: {reporting_basis: string; simulation_count: number; random_seed: number};
}

export interface CRQResult {
  schema_version: string;
  run: Record<string, any>;
  provenance: Record<string, any>;
  summary: {
    best_estimate: Record<string, any>;
    prudent: Record<string, any>;
    appetite: {status?: string; [key: string]: unknown};
  };
  formation: Record<string, any>;
  decomposition: Record<string, any>;
  loss: Record<string, any>;
  architecture: Record<string, any>;
  impact: Record<string, any>;
  treatments: Record<string, any>;
  sensitivity: any[];
  uncertainty: Record<string, any>;
  insurance: Record<string, any> | any[];
  limitations: any[];
  compatibility: Record<string, any>;
}

export interface RunStatus {
  schema_version: string;
  run_id: string;
  assessment_id: string;
  status: RunState;
  submitted_at: string;
  started_at?: string | null;
  completed_at?: string | null;
  updated_at: string;
  phase?: "VALIDATING" | "EXECUTING" | "FINALISING" | null;
  failure?: {code: string; message: string; retryable: boolean; correlation_id?: string} | null;
  links: {status: string; result: string};
}

export interface RunAccepted {
  schema_version: string;
  run_id: string;
  assessment_id: string;
  status: "QUEUED";
  submitted_at: string;
  links: {status: string; result: string};
}

export interface RunApi {
  submit(request: AssessmentRunRequest, idempotencyKey: string): Promise<RunAccepted>;
  getStatus(runId: string): Promise<RunStatus>;
  getResult(runId: string): Promise<CRQResult>;
}
