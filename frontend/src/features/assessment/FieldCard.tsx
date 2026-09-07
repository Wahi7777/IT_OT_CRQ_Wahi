import {AlertTriangle, Check, Database, FileSearch, Info, LockKeyhole, Plus, ShieldCheck} from "lucide-react";
import {Badge, Button, GlassPanel, LockedBanner} from "../../components/ui";
import type {FieldInventoryItem} from "../../contracts/types";
import {useAssessment} from "./AssessmentContext";
import {expandField, type ConcreteField} from "./fieldExpansion";

export function FieldGroup({item}: {item: FieldInventoryItem}) {
  const {request, setValue, preferences} = useAssessment();
  const fields = expandField(item, request, preferences);
  const locked = ["GOVERNED_PACK_INPUT", "DERIVED", "DISPLAY_ONLY", "INACTIVE_LEGACY"].includes(item.classification);
  const evidenceOnly = item.classification === "EVIDENCE_ONLY";
  const tone = item.classification === "PERMITTED_OVERRIDE" ? "override" : locked ? "locked" : evidenceOnly ? "evidence" : "editable";
  return <GlassPanel className={`field-group field-group--${tone}`}>
    <div className="field-group-head">
      <div className="field-type-icon">{locked ? <LockKeyhole /> : evidenceOnly ? <FileSearch /> : item.classification === "PERMITTED_OVERRIDE" ? <AlertTriangle /> : <Database />}</div>
      <div><div className="panel-title-row"><h2>{titleFor(item)}</h2><Badge tone={item.classification === "PERMITTED_OVERRIDE" ? "amber" : locked ? "neutral" : evidenceOnly ? "indigo" : "green"}>{item.classification.replaceAll("_", " ")}</Badge></div><code>{item.canonical_path}</code></div>
    </div>
    {locked && <LockedBanner>{item.classification === "INACTIVE_LEGACY" ? "Inactive legacy field · excluded from quantitative execution" : "Resolved from the approved immutable model bundle"}</LockedBanner>}
    {evidenceOnly && <div className="evidence-banner"><Info />Evidence context only · this field does not directly change quantitative output.</div>}
    <div className={fields.length > 8 ? "field-table" : "field-grid"}>
      {fields.length ? fields.map((field) => <ValueField key={field.key} field={field} item={item} onChange={setValue} />) : item.canonical_path.startsWith("insurance.layers") ? <div className="empty-editor"><p>No insurance layers are currently defined.</p><Button type="button" variant="secondary" onClick={() => setValue(["assessment", "insurance", "layers"], [{name: "", attachment: 0, limit: 0, coinsurance: 1}])}><Plus />Add insurance layer</Button></div> : <p className="muted">No records are present in the approved example.</p>}
    </div>
    <div className="field-foot">
      <span><Info />Why it matters: {whyItMatters(item)}</span>
      <span><ShieldCheck />{item.required ? "Required" : "Optional"}</span>
      <span><Check />Valid</span>
      <span><FileSearch />{evidenceOnly ? "Evidence source" : "Source trace available"}</span>
      <span>Confidence · {evidenceOnly ? "Reported" : "High"}</span>
    </div>
  </GlassPanel>;
}

function ValueField({field, item, onChange}: {field: ConcreteField; item: FieldInventoryItem; onChange: (path: (string | number)[], value: unknown) => void}) {
  const lastPath = String(field.path?.at(-1) ?? "");
  const identity = ["route_id", "control_id", "driver_id", "parameter_id", "name"].includes(lastPath);
  const editable = item.frontend.editable && !item.inert && !identity && Boolean(field.path);
  const inputId = `field-${field.key.replace(/[^a-z0-9]/gi, "-")}`;
  return <label className={`value-field ${editable ? "" : "is-readonly"}`} htmlFor={inputId}>
    <span>{field.label}{item.required && <em aria-label="required"> *</em>}</span>
    {editable ? <Control id={inputId} field={field} item={item} onChange={(value) => onChange(field.path!, value)} /> : <output id={inputId}>{displayValue(field.value)}</output>}
    <small>{editable ? (item.classification === "PERMITTED_OVERRIDE" ? "Overridden · approval evidence required" : "Entered") : item.classification === "INACTIVE_LEGACY" ? "Inactive" : "Locked / resolved"}</small>
  </label>;
}

function Control({id, field, item, onChange}: {id: string; field: ConcreteField; item: FieldInventoryItem; onChange: (value: unknown) => void}) {
  if (field.allowed?.length) return <select id={id} value={String(field.value)} onChange={(event) => onChange(coerce(event.target.value, field.value))}>{field.allowed.map((option) => <option key={String(option)} value={String(option)}>{String(option)}</option>)}</select>;
  if (typeof field.value === "boolean") return <select id={id} value={String(field.value)} onChange={(event) => onChange(event.target.value === "true")}><option value="true">Yes</option><option value="false">No</option></select>;
  if (typeof field.value === "number" || item.datatype.toLowerCase().includes("number")) {
    const boundedUnit = ["coverage", "coinsurance", "max_acceptable_event_probability"].includes(String(field.path?.at(-1)));
    return <input id={id} type="number" min="0" max={boundedUnit ? "1" : undefined} step="any" value={field.value == null ? "" : String(field.value)} onChange={(event) => onChange(event.target.value === "" ? null : Number(event.target.value))} />;
  }
  if (Array.isArray(field.value)) return <input id={id} value={field.value.join(", ")} onChange={(event) => onChange(event.target.value.split(",").map((value) => value.trim()).filter(Boolean))} />;
  return <input id={id} value={field.value == null ? "" : String(field.value)} onChange={(event) => onChange(event.target.value)} />;
}

function displayValue(value: unknown) {
  if (value === null || value === undefined || value === "") return "Not provided";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (typeof value === "number") return new Intl.NumberFormat("en-AE", {maximumFractionDigits: 4}).format(value);
  if (Array.isArray(value)) return value.length ? value.join(", ") : "None recorded";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function coerce(value: string, current: unknown) {
  if (typeof current === "boolean") return value === "true";
  if (typeof current === "number") return Number(value);
  return value;
}

function titleFor(item: FieldInventoryItem) {
  const leaf = item.canonical_path.split(".").at(-1) ?? item.canonical_path;
  return leaf.replace(/[{}[\]_]/g, " ").replace(/\s+/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase()).trim();
}

function whyItMatters(item: FieldInventoryItem) {
  if (item.inert) return "Retained only for migration traceability; it must not alter results.";
  if (item.classification === "GOVERNED_PACK_INPUT") return "Provides governed assumptions required to reproduce the model run.";
  if (item.classification === "EVIDENCE_ONLY") return "Supports confidence and auditability without becoming a numeric model input.";
  return `Affects ${item.affected_results.slice(0, 3).join(", ") || "assessment validation"}.`;
}
