"""Deterministic minimum-data ViewContextBundle builder."""

from __future__ import annotations

import hashlib
from typing import Any, Iterable, Mapping

from crq.copilot.models import ViewContextBundle, ViewFact


SUGGESTED_QUESTIONS = {
    "assessment.organization": ("Why is this input required?", "What evidence should support this value?", "Review the assessment scope"),
    "assessment.architecture": ("Why are we asking this?", "What evidence would support this answer?", "What does Unknown mean?"),
    "assessment.controls": ("Why does this control matter?", "What evidence should I provide?", "Which scenarios depend on this control?"),
    "assessment.business_impact": ("Why is this input required?", "How is this used in the model?", "When should I override this assumption?"),
    "assessment.risk_appetite_insurance": ("Explain risk appetite", "How is insurance represented?", "What policy evidence should I provide?"),
    "assessment.review": ("Is this assessment ready?", "Which evidence gaps remain?", "Review outstanding inputs"),
    "results.overview": ("Explain headline metrics", "What drives this result?", "What does the tail risk mean?", "Why is P(Material Event) at this level?", "Review evidence quality"),
    "results.risk_drivers": ("What is driving the exposure?", "Which actor matters most?", "Which loss component dominates?", "Is the risk concentrated or diversified?"),
    "results.scenarios": ("Why is this scenario material?", "What drives the severity?", "Which attack routes contribute?", "Which treatments affect this scenario?"),
    "results.attack_paths": ("Why is this path open?", "What is preventing this path from closing?", "Which controls influence this route?", "What evidence supports this state?"),
    "results.business_impact": ("What is driving the financial loss?", "Why is business interruption dominant?", "Which assumptions affect severity most?", "What happens in the tail?"),
    "results.treatment": ("Why is this treatment prioritized?", "What part of the risk does it reduce?", "Which scenarios does it affect?", "How does it change tail risk?"),
    "results.insurance": ("How much risk remains after insurance?", "How often does the policy attach?", "What does exhaustion probability mean?", "Which losses remain uninsured?"),
    "results.uncertainty": ("How stable are the modelled values?", "What does simulation uncertainty mean?", "Which limitations matter?"),
    "results.evidence": ("Where is the assessment weakest?", "Which assumptions matter most?", "What evidence should we collect next?", "Which unknowns affect the result?"),
    "results.executive": ("Generate executive interpretation",),
}

_RESULT_PATHS = {
    "results.overview": ("/summary/prudent", "/summary/appetite", "/architecture/evidence_status", "/decomposition/actors", "/decomposition/scenarios", "/loss/categories"),
    "results.risk_drivers": ("/formation", "/decomposition/actors", "/decomposition/scenarios", "/loss/drivers"),
    "results.scenarios": ("/decomposition/scenarios", "/architecture/route_path_states", "/loss/drivers"),
    "results.attack_paths": ("/architecture/route_path_states", "/architecture/applicability", "/architecture/feasibility", "/architecture/barriers", "/architecture/relevant_ttps", "/architecture/evidence_status"),
    "results.business_impact": ("/loss/categories", "/loss/drivers", "/impact"),
    "results.treatment": ("/treatments/individual_controls", "/treatments/packages", "/treatments/rankings"),
    "results.insurance": ("/insurance",),
    "results.uncertainty": ("/uncertainty", "/limitations"),
    "results.evidence": ("/architecture/evidence_status", "/limitations"),
    "results.executive": ("/summary/prudent", "/summary/appetite", "/decomposition/actors", "/decomposition/scenarios", "/loss/categories", "/treatments/rankings", "/insurance", "/limitations"),
}

_ASSESSMENT_PATHS = {
    "assessment.organization": ("/assessment", "/scope", "/domain_inputs/financial_exposure"),
    "assessment.architecture": ("/domain_inputs/routes",),
    "assessment.controls": ("/domain_inputs/controls",),
    "assessment.business_impact": ("/domain_inputs/financial_exposure", "/domain_inputs/impact_overrides"),
    "assessment.risk_appetite_insurance": ("/risk_appetite", "/insurance"),
    "assessment.review": ("/assessment", "/scope", "/risk_appetite", "/insurance", "/evidence"),
}

_SENSITIVE_KEYS = {
    "description", "hash", "content", "payload", "diagram", "document", "file", "uri", "url",
    "lec", "samples", "simulation_values", "trials", "raw",
    "client_name", "assessment_name", "organisation_name", "organization_name", "tenant_id", "user_id",
}
_MAX_FACTS = 300
_MAX_LIST_ITEMS = 20


def build_view_context(*, current_view: str, assessment: Mapping[str, Any], result: Mapping[str, Any] | None = None, run_id: str | None = None, result_hash: str | None = None, selected_entity: Mapping[str, str] | None = None) -> ViewContextBundle:
    if current_view not in SUGGESTED_QUESTIONS:
        raise ValueError("unsupported current_view")
    assessment_id = str((assessment.get("assessment") or {}).get("assessment_id") or "")
    if not assessment_id:
        raise ValueError("assessment_id is required")
    source: Mapping[str, Any]
    paths: tuple[str, ...]
    if current_view.startswith("results."):
        if result is None:
            raise ValueError("result is required for result context")
        source, paths = result, _RESULT_PATHS[current_view]
    else:
        source, paths = assessment, _ASSESSMENT_PATHS[current_view]
    facts: list[ViewFact] = []
    entities: dict[tuple[str, str], dict[str, str]] = {}
    for path in paths:
        value = _pointer(source, path)
        _collect(value, path, current_view, facts, entities, selected_entity)
    if current_view == "results.overview":
        facts.extend(_overview_methodology_facts(current_view))
        facts.extend(_overview_comparison_facts(current_view, source))
    if current_view == "results.scenarios":
        facts.extend(_scenario_comparison_facts(current_view, source, selected_entity))
    if current_view == "assessment.business_impact":
        facts.append(_assessment_evidence_count_fact(current_view, assessment))
    return ViewContextBundle(
        context_type=current_view,
        assessment_id=assessment_id,
        run_id=run_id,
        result_hash=result_hash,
        selected_entity=dict(selected_entity) if selected_entity else None,
        facts=tuple(facts),
        allowed_entities=tuple(entities[key] for key in sorted(entities)),
        suggested_questions=SUGGESTED_QUESTIONS[current_view],
    )


def _assessment_evidence_count_fact(context_type: str, assessment: Mapping[str, Any]) -> ViewFact:
    records = assessment.get("evidence")
    meaningful = [record for record in records if isinstance(record, Mapping) and _is_meaningful_evidence(record)] if isinstance(records, list) else []
    count = len(meaningful)
    path = "/evidence/meaningful_count"
    return ViewFact(_fact_id(context_type, path), "numeric", "Supporting evidence records", count, f"{count} record{'s' if count != 1 else ''}", "records", path)


def _is_meaningful_evidence(record: Mapping[str, Any]) -> bool:
    description = str(record.get("description") or "").strip().casefold()
    source = str(record.get("source") or "").strip().casefold()
    placeholder = not description or description in {"n/a", "na", "not provided", "no exposure-model recommendation loaded."}
    generated_source = not source or any(term in source for term in ("workbook", "spreadsheet", "xlsx"))
    return not placeholder or not generated_source or bool(record.get("hash") or record.get("observed_at"))


def _pointer(value: Mapping[str, Any], path: str) -> Any:
    target: Any = value
    for token in path.strip("/").split("/"):
        if not isinstance(target, Mapping):
            return None
        target = target.get(token)
    return target


def _collect(value: Any, path: str, context_type: str, facts: list[ViewFact], entities: dict[tuple[str, str], dict[str, str]], selected: Mapping[str, str] | None, depth: int = 0) -> None:
    if value is None or depth > 5 or len(facts) >= _MAX_FACTS:
        return
    if isinstance(value, Mapping):
        entity = _entity(value, path)
        if entity:
            entities[(entity["entity_type"], entity["entity_id"])] = entity
            if selected and selected.get("entity_id") and selected["entity_id"] != entity["entity_id"] and depth <= 1:
                return
        for key in sorted(value):
            if str(key).lower() in _SENSITIVE_KEYS:
                continue
            _collect(value[key], f"{path}/{_escape(str(key))}", context_type, facts, entities, selected, depth + 1)
        return
    if isinstance(value, list):
        indexed_items = list(enumerate(value))
        limit = _list_limit(context_type, path)
        if selected and selected.get("entity_id"):
            matching = [(index, item) for index, item in indexed_items if isinstance(item, Mapping) and (_entity(item, path) or {}).get("entity_id") == selected["entity_id"]]
            indexed_items = (matching or indexed_items)[:limit]
        else:
            indexed_items = indexed_items[:limit]
        for index, item in indexed_items:
            entity = _entity(item, path) if isinstance(item, Mapping) else None
            if selected and selected.get("entity_id") and entity and entity["entity_id"] != selected["entity_id"]:
                continue
            _collect(item, f"{path}/{index}", context_type, facts, entities, selected, depth + 1)
        return
    if isinstance(value, (str, int, float, bool)):
        label = _fact_label(path)
        fact_type = "numeric" if isinstance(value, (int, float)) and not isinstance(value, bool) else "categorical" if isinstance(value, (bool, str)) else "text"
        unit = _unit(path, value)
        facts.append(ViewFact(_fact_id(context_type, path), fact_type, label, value, _render(value, unit), unit, path))


def _fact_label(path: str) -> str:
    ranked_paths = {
        "/decomposition/actors/0/name": "Dominant actor",
        "/decomposition/scenarios/0/name": "Dominant scenario",
        "/loss/categories/0/name": "Largest AAL loss category",
        "/loss/drivers/0/name": "Largest AAL loss driver",
    }
    if path in ranked_paths:
        return ranked_paths[path]
    leaf = path.rsplit("/", 1)[-1]
    metric_labels = {
        "aal": "AAL",
        "best_aal": "Best-estimate AAL",
        "prudent_aal": "Prudent AAL",
        "selected_aal": "Selected AAL",
        "current_aal": "Current AAL",
        "whatif_aal": "Post-treatment AAL",
        "var95": "VaR95",
        "var95_base": "Baseline VaR95",
        "var95_change": "VaR95 reduction",
        "var95_pct": "VaR95 reduction percentage",
        "var99": "VaR99",
        "var99_base": "Baseline VaR99",
        "var99_change": "VaR99 reduction",
        "var99_pct": "VaR99 reduction percentage",
        "tvar95": "TVaR95",
        "tvar95_base": "Baseline TVaR95",
        "tvar95_change": "TVaR95 reduction",
        "tvar95_pct": "TVaR95 reduction percentage",
        "tvar99": "TVaR99",
        "tvar99_base": "Baseline TVaR99",
        "tvar99_change": "TVaR99 reduction",
        "tvar99_pct": "TVaR99 reduction percentage",
        "p_any_event": "P(Material Event)",
        "reduction": "AAL reduction" if "/treatments/individual_controls/" in path else "Reduction",
        "reduction_pct": "AAL reduction percentage",
    }
    return metric_labels.get(leaf, leaf.replace("_", " ").title())


def _entity(value: Mapping[str, Any], path: str) -> dict[str, str] | None:
    if "/decomposition/scenarios" in path and value.get("id"):
        return {"entity_type": "scenario", "entity_id": str(value["id"]), "label": str(value.get("name") or value["id"])}
    if "/decomposition/actors" in path and value.get("id"):
        return {"entity_type": "actor", "entity_id": str(value["id"]), "label": str(value.get("name") or value["id"])}
    if "/architecture/route_path_states" in path and value.get("route"):
        return {"entity_type": "route", "entity_id": str(value["route"]), "label": str(value["route"])}
    if "/loss/drivers" in path and value.get("driver_id"):
        return {"entity_type": "loss_driver", "entity_id": str(value["driver_id"]), "label": str(value.get("name") or value["driver_id"])}
    candidates = (("scenario", "scenario_id", "scenario"), ("actor", "actor_id", "actor"), ("route", "route_id", "route"), ("control", "control_id", "name"), ("control", "cid", "name"), ("treatment", "treatment_id", "name"))
    for entity_type, identifier, label_key in candidates:
        raw = value.get(identifier)
        if raw:
            return {"entity_type": entity_type, "entity_id": str(raw), "label": str(value.get(label_key) or raw)}
    return None


def _fact_id(context_type: str, path: str) -> str:
    return "vf_" + hashlib.sha256(f"{context_type}|{path}".encode()).hexdigest()[:16]


def _unit(path: str, value: Any) -> str | None:
    lower = path.lower()
    if any(word in lower for word in ("probability", "pct", "share", "coverage", "p_any_event")):
        return "percent"
    if isinstance(value, (int, float)) and "/treatments/individual_controls/" in lower and lower.endswith("/reduction"):
        return "currency"
    if isinstance(value, (int, float)) and any(word in lower for word in ("aal", "var95", "var99", "tvar", "loss", "recovery", "retention", "limit", "cost", "revenue")):
        return "currency"
    if isinstance(value, (int, float)) and "downtime" in lower:
        return "days"
    if "frequency" in lower or "per_year" in lower:
        return "events_per_year"
    return None


def _render(value: Any, unit: str | None) -> str:
    if unit == "percent" and isinstance(value, (int, float)):
        return f"{value * 100:.2f}%"
    if unit == "currency" and isinstance(value, (int, float)):
        absolute = abs(value)
        if absolute >= 1_000_000:
            return f"${value / 1_000_000:.2f}M"
        if absolute >= 1_000:
            return f"${value / 1_000:.2f}K"
        return f"${value:,.2f}"
    if unit == "days" and isinstance(value, (int, float)):
        return f"{value:,.2f} days"
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)


def _escape(token: str) -> str:
    return token.replace("~", "~0").replace("/", "~1")


def _list_limit(context_type: str, path: str) -> int:
    if context_type == "results.overview" and any(family in path for family in ("/decomposition/actors", "/decomposition/scenarios", "/loss/categories")):
        return 1
    if context_type == "results.business_impact" and any(family in path for family in ("/loss/categories", "/loss/drivers")):
        return 5
    if context_type == "results.risk_drivers" and any(family in path for family in ("/decomposition/actors", "/decomposition/scenarios", "/loss/drivers")):
        return 8
    if context_type == "results.executive" and any(family in path for family in ("/decomposition/actors", "/decomposition/scenarios", "/loss/categories", "/treatments/rankings")):
        return 3
    return _MAX_LIST_ITEMS


def _overview_methodology_facts(context_type: str) -> list[ViewFact]:
    definitions = (
        ("aal", "AAL definition", "Mean annual aggregate loss across all simulation trials."),
        ("var95", "VaR95 definition", "95th percentile of the annual aggregate loss distribution."),
        ("tvar95", "TVaR95 definition", "Mean annual aggregate loss across the worst 5% of simulation trials."),
        ("var99", "VaR99 definition", "99th percentile of the annual aggregate loss distribution."),
        ("tvar99", "TVaR99 definition", "Mean annual aggregate loss across the worst 1% of simulation trials."),
    )
    facts = [
        ViewFact(
            _fact_id(context_type, f"/methodology/financial-risk-metrics/{key}"),
            "categorical",
            label,
            value,
            value,
            None,
            f"/methodology/financial-risk-metrics/{key}",
        )
        for key, label, value in definitions
    ]
    facts.extend(
        (
            ViewFact(_fact_id(context_type, "/methodology/financial-risk-metrics/tvar95-tail-share"), "numeric", "TVaR95 tail share", 0.05, "5%", "percent", "/methodology/financial-risk-metrics/tvar95-tail-share"),
            ViewFact(_fact_id(context_type, "/methodology/financial-risk-metrics/tvar99-tail-share"), "numeric", "TVaR99 tail share", 0.01, "1%", "percent", "/methodology/financial-risk-metrics/tvar99-tail-share"),
        )
    )
    return facts


def _overview_comparison_facts(context_type: str, result: Mapping[str, Any]) -> list[ViewFact]:
    prudent = _pointer(result, "/summary/prudent")
    if not isinstance(prudent, Mapping):
        return []
    comparisons = (
        ("var99-exceeds-aal", "VaR99 is greater than AAL.", prudent.get("var99"), prudent.get("aal")),
        ("tvar99-exceeds-var99", "TVaR99 is greater than VaR99.", prudent.get("tvar99"), prudent.get("var99")),
    )
    return [
        ViewFact(
            _fact_id(context_type, f"/derived/overview/{key}"),
            "categorical",
            "Governed comparison",
            statement,
            statement,
            None,
            f"/derived/overview/{key}",
        )
        for key, statement, left, right in comparisons
        if isinstance(left, (int, float)) and isinstance(right, (int, float)) and left > right
    ]


def _scenario_comparison_facts(context_type: str, result: Mapping[str, Any], selected: Mapping[str, str] | None) -> list[ViewFact]:
    scenarios = _pointer(result, "/decomposition/scenarios")
    if not isinstance(scenarios, list) or not scenarios:
        return []
    selected_id = str((selected or {}).get("entity_id") or "")
    scenario = next((item for item in scenarios if isinstance(item, Mapping) and str(item.get("id")) == selected_id), scenarios[0])
    if not isinstance(scenario, Mapping):
        return []
    contribution = scenario.get("contribution") or {}
    metrics = scenario.get("metrics") or {}
    selected_aal = metrics.get("selected_aal") if isinstance(metrics, Mapping) else None
    comparisons = (
        ("tvar95-exceeds-selected-aal", "TVaR95 contribution is greater than selected AAL contribution.", contribution.get("tvar95") if isinstance(contribution, Mapping) else None),
        ("tvar99-exceeds-selected-aal", "TVaR99 contribution is greater than selected AAL contribution.", contribution.get("tvar99") if isinstance(contribution, Mapping) else None),
    )
    return [
        ViewFact(
            _fact_id(context_type, f"/derived/scenario/{key}"),
            "categorical",
            "Governed comparison",
            statement,
            statement,
            None,
            f"/derived/scenario/{key}",
        )
        for key, statement, tail_value in comparisons
        if isinstance(tail_value, (int, float)) and isinstance(selected_aal, (int, float)) and tail_value > selected_aal
    ]


def fact_ids(bundle: ViewContextBundle) -> Iterable[str]:
    return (fact.fact_id for fact in bundle.facts)
