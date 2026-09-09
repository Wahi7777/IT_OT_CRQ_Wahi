import type {AssessmentRunRequest, FieldInventoryItem} from "../../contracts/types";
import {sectorPacks} from "../../contracts/governedData";

export interface ConcreteField {
  key: string;
  label: string;
  path?: (string | number)[];
  value: unknown;
  allowed?: unknown[];
}

const a = ["assessment"];

export function expandField(item: FieldInventoryItem, request: AssessmentRunRequest, preferences: {tvar_selection: "TVaR95" | "TVaR99"}): ConcreteField[] {
  const assessment = request.assessment;
  const domainInputs = assessment.domain_inputs;
  const canonical = item.canonical_path;
  const field = (key: string, label: string, path: (string | number)[], value: unknown, allowed?: unknown[]): ConcreteField => ({key, label, path, value, allowed});

  if (canonical.startsWith("assessment.") && !canonical.includes("{parameter}") && !canonical.includes("resolved_")) {
    const key = canonical.split(".")[1];
    const allowed = key === "sector" ? sectorPacks.filter((pack) => pack.domain === assessment.assessment.domain).map((pack) => pack.sector) : Array.isArray(item.allowed_values) ? item.allowed_values : undefined;
    return [field(key, humanize(key), [...a, "assessment", key], (assessment.assessment as Record<string, unknown>)[key], allowed)];
  }
  if (canonical === "assessment.{parameter}") {
    const entries = [
      ["organisation", assessment.assessment.organisation],
      ["currency", assessment.assessment.currency],
      ["country_region", assessment.scope?.country_region],
      ["facility", assessment.scope?.facility],
      ["critical_process", assessment.scope?.critical_process]
    ] as const;
    return entries.filter(([key, value]) => value !== undefined && (!item.parameter_keys || item.parameter_keys.includes(key))).map(([key, value]) =>
      field(key, humanize(key), key in assessment.assessment ? [...a, "assessment", key] : [...a, "scope", key], value)
    );
  }
  if (canonical === "runtime.tvar_selection") {
    return [field("tvar_selection", "Tail metric display", ["__ui", "tvar_selection"], preferences.tvar_selection, Array.isArray(item.allowed_values) ? item.allowed_values : undefined)];
  }
  if (canonical === "runtime.{parameter}") {
    return Object.entries(assessment.runtime).filter(([key]) => !item.parameter_keys || item.parameter_keys.includes(key)).map(([key, value]) => field(key, humanize(key), [...a, "runtime", key], value));
  }
  if (canonical === "outside_in.apply") return [field("apply", "Apply outside-in evidence", [...a, "outside_in", "apply"], assessment.outside_in.apply, [true, false])];
  if (canonical.startsWith("risk_appetite.")) return objectFields("risk_appetite", assessment.risk_appetite, [...a, "risk_appetite"], item.parameter_keys);
  if (canonical === "insurance.retention") return [field("retention", "Retention", [...a, "insurance", "retention"], assessment.insurance.retention)];
  if (canonical === "insurance.primary_limit") return [field("primary_limit", "Primary limit", [...a, "insurance", "primary_limit"], assessment.insurance.primary_limit)];
  if (canonical === "insurance.aggregate_programme_limit") return [field("aggregate_programme_limit", "Aggregate programme limit", [...a, "insurance", "aggregate_programme_limit"], assessment.insurance.aggregate_programme_limit)];
  if (canonical.startsWith("insurance.layers")) return flattenArray("layer", assessment.insurance.layers ?? [], [...a, "insurance", "layers"]);
  if (canonical.includes("financial_exposure.employees")) return [field("employees", "Employees · inactive", undefined as never, domainInputs.financial_exposure?.employees)];
  if (canonical === "domain_inputs.financial_exposure.{parameter}") {
    const entries = Object.entries(domainInputs.financial_exposure ?? {}).filter(([key]) => item.parameter_keys ? item.parameter_keys.includes(key) : item.classification === "INACTIVE_LEGACY" ? ["employees", "customers"].includes(key) : !["employees", "customers"].includes(key));
    return entries.map(([key, value]) => field(key, humanize(key), [...a, "domain_inputs", "financial_exposure", key], value));
  }
  if (canonical === "domain_inputs.exposure_model_enabled") return [field("exposure_model_enabled", "Use exposure model", [...a, "domain_inputs", "exposure_model_enabled"], domainInputs.exposure_model_enabled, [true, false])];
  if (canonical.startsWith("domain_inputs.routes")) return flattenArray("route", domainInputs.routes ?? [], [...a, "domain_inputs", "routes"], ["route_id", ...(item.parameter_keys ?? [])], item.item_keys, "route_id").map((routeField) => {
    const fieldName = String(routeField.path?.at(-1) ?? "");
    return ["organisation_applicable", "model_feasible"].includes(fieldName) ? {...routeField, allowed: ["Yes", "No", "Unknown"]} : routeField;
  });
  if (canonical.startsWith("domain_inputs.controls")) {
    const keys = ["control_id", ...(item.parameter_keys ?? [])];
    return flattenArray("control", domainInputs.controls ?? [], [...a, "domain_inputs", "controls"], keys, item.item_keys, "control_id").map((controlField) => {
      const fieldName = String(controlField.path?.at(-1) ?? "");
      return fieldName === "maturity" ? {...controlField, allowed: ["Absent", "Initial", "Developing", "Managed", "Optimised", "Not Assessed"]} : controlField;
    });
  }
  if (canonical.startsWith("domain_inputs.impact_overrides")) return flattenArray("override", domainInputs.impact_overrides ?? [], [...a, "domain_inputs", "impact_overrides"], undefined, undefined, undefined, (value) => (!item.parameter_keys || item.parameter_keys.includes(String(value.parameter_id))) && (!item.item_keys || item.item_keys.includes(String(value.scenario_id))));
  if (canonical === "domain_inputs.frequency_adjustments.{parameter}") return objectFields("frequency", domainInputs.frequency_adjustments ?? {}, [...a, "domain_inputs", "frequency_adjustments"], item.parameter_keys);
  if (canonical === "domain_inputs.topology.{parameter}") return objectFields("topology", domainInputs.topology ?? {}, [...a, "domain_inputs", "topology"], item.parameter_keys, allowedMap(item.allowed_values));
  if (canonical.startsWith("domain_inputs.impact_drivers")) return flattenArray("driver", domainInputs.impact_drivers ?? [], [...a, "domain_inputs", "impact_drivers"], ["driver_id", ...(item.parameter_keys ?? [])], item.item_keys, "driver_id");
  if (canonical === "domain_inputs.assessment_adjustments.prudence_factor") return [field("prudence_factor", "Prudence factor", [...a, "domain_inputs", "assessment_adjustments", "prudence_factor"], domainInputs.assessment_adjustments?.prudence_factor)];
  if (canonical.startsWith("outside_in.evidence")) return flattenArray("evidence", assessment.evidence ?? [], [...a, "evidence"]);
  if (canonical.startsWith("model_bundle") || canonical.startsWith("assessment.resolved")) {
    return [field(canonical, "Resolved from approved model bundle", undefined as never, `${request.model_bundle_reference.bundle_id} · ${request.model_bundle_reference.bundle_version}`)];
  }
  return [field(canonical, humanize(canonical.split(".").at(-1) ?? canonical), undefined as never, item.inert ? "Inactive" : "Governed by canonical contract")];
}

function objectFields(prefix: string, object: Record<string, unknown>, path: (string | number)[], allowedKeys?: string[], allowedValues?: Record<string, unknown[]>): ConcreteField[] {
  const normalizedKeys = allowedKeys?.map((key) => key.toLowerCase());
  return Object.entries(object).filter(([key]) => !normalizedKeys || normalizedKeys.includes(key.toLowerCase())).map(([key, value]) => ({key: `${prefix}-${key}`, label: humanize(key), path: [...path, key], value, allowed: allowedValues?.[key.toUpperCase()] ?? allowedValues?.[key]}));
}

function allowedMap(value: FieldInventoryItem["allowed_values"]): Record<string, unknown[]> | undefined {
  return value && typeof value === "object" && !Array.isArray(value) ? value : undefined;
}

function flattenArray(prefix: string, values: Record<string, any>[], path: (string | number)[], allowedKeys?: string[], allowedIds?: string[], idKey?: string, include?: (value: Record<string, any>) => boolean): ConcreteField[] {
  return values.flatMap((value, index) => (allowedIds && idKey && !allowedIds.includes(String(value[idKey]))) || (include && !include(value)) ? [] : Object.entries(value)
    .filter(([key]) => !allowedKeys || allowedKeys.includes(key))
    .flatMap(([key, nested]) => {
      const identity = value.route_id ?? value.control_id ?? value.driver_id ?? value.parameter_id ?? value.name ?? index + 1;
      if (nested && typeof nested === "object" && !Array.isArray(nested)) {
        return Object.entries(nested).map(([nestedKey, nestedValue]) => ({
          key: `${prefix}-${index}-${key}-${nestedKey}`,
          label: `${identity} · ${humanize(key)} · ${nestedKey}`,
          path: [...path, index, key, nestedKey],
          value: nestedValue
        }));
      }
      return [{key: `${prefix}-${index}-${key}`, label: `${identity} · ${humanize(key)}`, path: [...path, index, key], value: nested}];
    }));
}

export function humanize(value: string) {
  return value.replace(/[_.]/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}
