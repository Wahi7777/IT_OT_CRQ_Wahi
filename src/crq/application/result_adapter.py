"""Lossless normalization of native IT/OT engine dictionaries into CRQResult."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from crq.application.models import CRQAssessment, CRQResult, ModelBundle, RunConfig, canonical_hash, json_value
from crq.versions import INPUT_SCHEMA_VERSION, METHODOLOGY_VERSION, OUTPUT_SCHEMA_VERSION, PLATFORM_VERSION


def normalize_result(
    router_result: dict[str, Any],
    assessment: CRQAssessment,
    bundle: ModelBundle,
    config: RunConfig,
    started_at: datetime,
) -> CRQResult:
    completed = datetime.now(timezone.utc)
    # The engine's output path is execution infrastructure, not a model result.
    # Never expose the temporary filesystem path through the canonical contract.
    native = json_value({key: value for key, value in router_result["engine_result"].items() if key != "output"})
    identity = assessment.to_dict()["assessment"]
    bundle_data = bundle.to_dict()
    best = _metrics(native, "best")
    prudent = _metrics(native, "prudent")
    payload = {
        "schema_version": OUTPUT_SCHEMA_VERSION,
        "run": {
            "run_id": router_result["run_id"],
            "started_at": started_at.isoformat(),
            "completed_at": completed.isoformat(),
            "assessment_id": identity["assessment_id"],
            "assessment_version": identity["assessment_version"],
            "simulation_count": config.simulation_count,
            "seed": config.random_seed,
            "runtime_configuration": config.to_dict(),
        },
        "provenance": {
            "platform_version": PLATFORM_VERSION,
            "engine_version": str(native.get("engine_version") or router_result.get("engine_version")),
            "methodology_version": METHODOLOGY_VERSION,
            "input_schema_version": INPUT_SCHEMA_VERSION,
            "output_schema_version": OUTPUT_SCHEMA_VERSION,
            "model_bundle_id": bundle_data["bundle_id"],
            "model_bundle_version": bundle_data["model_bundle_version"],
            "sector_pack_id": bundle_data["sector_pack"]["pack_id"],
            "sector_pack_version": bundle_data["sector_pack"]["pack_version"],
            "assessment_hash": assessment.to_dict()["assessment_hash"],
            "bundle_hash": bundle_data["bundle_hash"],
            "result_hash": "",
        },
        "summary": {
            "best_estimate": best,
            "prudent": prudent,
            "appetite": {
                "inputs": native.get("appetite_inputs"),
                "status": native.get("appetite_status"),
                "breaches": native.get("appetite_breaches"),
            },
        },
        "formation": json_value(native.get("formation") or {
            "campaigns": native.get("campaigns"),
            "attempts": native.get("attempt_frequency"),
            "successful_events": native.get("event_frequency"),
        }),
        "decomposition": {
            "actors": _components(native, "actor"),
            "scenarios": _components(native, "scenario"),
            "actor_scenario": json_value(native.get("actor_scenario_rows") or []),
            "it_routes": json_value(native.get("route_analysis") or []),
            "ot_paths_ttps": json_value(native.get("path_rows") or native.get("ttp_rows") or []),
        },
        "loss": {
            "aep": json_value(native.get("aep_lec") or native.get("lec") or []),
            "oep": json_value(native.get("oep_lec") or []),
            "return_periods": json_value(native.get("return_periods") or []),
            "business_interruption": json_value(native.get("business_interruption") or {}),
            "non_bi": json_value(native.get("non_bi") or {}),
            "categories": json_value(native.get("loss_components") or []),
            "drivers": json_value(native.get("loss_drivers") or native.get("driver_matrix_summary") or []),
            "reconciliation": json_value(native.get("impact_reconcile") or {}),
        },
        "architecture": {
            "input_snapshot": json_value(assessment.to_dict()["domain_inputs"]),
            "route_path_states": json_value(native.get("actor_scenario_rows") or []),
            "relevant_ttps": json_value(native.get("ttp_rows") or []),
            "barriers": json_value(native.get("barriers") or []),
            "stage_through_probabilities": json_value(native.get("stage_through") or []),
            "applicability": json_value(native.get("applicability") or []),
            "feasibility": json_value(native.get("feasibility") or []),
            "evidence_status": json_value(assessment.to_dict().get("evidence") or []),
        },
        "impact": _impact(native, identity["domain"]),
        "treatments": {
            "individual_controls": json_value(native.get("whatifs") or []),
            "packages": json_value(native.get("control_packages") or []),
            "post_treatment_metrics": json_value(native.get("whatifs") or []),
            "reductions": json_value([{"control_id": x.get("cid"), "reduction": x.get("reduction")} for x in native.get("whatifs") or []]),
            "rankings": json_value(native.get("top_controls") or []),
        },
        "sensitivity": json_value(native.get("sensitivities") or []),
        "uncertainty": {
            "monte_carlo": {"best_aal_se": native.get("best_aal_se"), "prudent_aal_se": native.get("prudent_aal_se")},
            "evidence_limitations": json_value(native.get("balbix_gaps") or []),
        },
        "insurance": json_value(native.get("insurance_analysis") or {}),
        "limitations": json_value(native.get("balbix_gaps") or []),
        "compatibility": {
            "native_domain": identity["domain"],
            "legacy_engine_extension": native,
            "router_metadata": {k: json_value(v) for k, v in router_result.items() if k not in {"engine_result", "output"}},
            "lossless": True,
        },
    }
    payload["provenance"]["result_hash"] = canonical_hash({**payload, "provenance": {**payload["provenance"], "result_hash": ""}})
    return CRQResult.from_dict(payload)


def _metrics(native: dict[str, Any], prefix: str) -> dict[str, Any]:
    return {
        "aal": native[f"{prefix}_aal"],
        "var95": native[f"{prefix}_var95"],
        "var99": native[f"{prefix}_var99"],
        "tvar95": native[f"{prefix}_tvar95"],
        "tvar99": native[f"{prefix}_tvar99"],
        "event_frequency": native[f"{prefix}_event_frequency"],
        "p_any_event": native[f"{prefix}_pany"],
        "multi_year_probabilities": {"3y": native.get(f"{prefix}_pany_3y"), "5y": native.get(f"{prefix}_pany_5y")},
        "tolerance_exceedance_probability": native.get(f"{prefix}_p_exceed_tolerance"),
    }


def _components(native: dict[str, Any], kind: str) -> list[dict[str, Any]]:
    current = native.get(f"{kind}_aal") or {}
    best = native.get(f"{kind}_aal_best") or {}
    prudent = native.get(f"{kind}_aal_prudent") or {}
    t95 = native.get(f"{kind}_tvar95_contribution") or {}
    t99 = native.get(f"{kind}_tvar99_contribution") or {}
    names = sorted(set(current) | set(best) | set(prudent) | set(t95) | set(t99))
    return [{"id": name, "name": name, "metrics": {"selected_aal": current.get(name), "best_aal": best.get(name), "prudent_aal": prudent.get(name)}, "contribution": {"tvar95": t95.get(name), "tvar99": t99.get(name)}, "metadata": {}} for name in names]


def _impact(native: dict[str, Any], domain: str) -> dict[str, Any]:
    diagnostics = json_value(native.get("operational_diagnostics") or {})
    if domain == "OT":
        return {"ot_downtime": diagnostics, "ot_capacity": diagnostics, "it_affected_records": None, "it_affected_endpoints": None, "it_affected_services": None}
    return {
        "ot_downtime": None, "ot_capacity": None,
        "it_affected_records": {k: v for k, v in diagnostics.items() if k.startswith("records_")},
        "it_affected_endpoints": {k: v for k, v in diagnostics.items() if k.startswith("endpoints_")},
        "it_affected_services": {k: v for k, v in diagnostics.items() if k.startswith("services_")},
    }
