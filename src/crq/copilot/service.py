"""Provider-neutral orchestration and fail-closed verification."""

from __future__ import annotations

import os
from typing import Any, Mapping

from crq.copilot.context import build_view_context
from crq.copilot.models import CopilotResponse
from crq.copilot.prompts import build_prompts
from crq.copilot.providers.base import CopilotProvider, ProviderResult
from crq.copilot.verifier import verify_response


class CopilotService:
    def __init__(self, provider: CopilotProvider, *, max_tokens: int = 700, temperature: float = 0.0):
        self.provider = provider
        self.max_tokens = max_tokens
        self.temperature = temperature

    def query(self, *, current_view: str, question: str, assessment: Mapping[str, Any], result: Mapping[str, Any] | None = None, run_id: str | None = None, result_hash: str | None = None, selected_entity: Mapping[str, str] | None = None) -> dict[str, Any]:
        context = build_view_context(current_view=current_view, assessment=assessment, result=result, run_id=run_id, result_hash=result_hash, selected_entity=selected_entity)
        redirect = _cross_view_redirect(current_view, question)
        if redirect:
            return {"status": "VERIFIED", "answer": redirect, "key_points": [], "caveats": [], "supporting_fact_ids": [], "related_entities": [], "context_type": context.context_type, "schema_version": "1.0.0"}
        overview_answer = _overview_answer(context, question)
        if overview_answer:
            return overview_answer
        risk_driver_answer = _risk_driver_answer(context, question)
        if risk_driver_answer:
            return risk_driver_answer
        scenario_answer = _scenario_answer(context, question)
        if scenario_answer:
            return scenario_answer
        path_state_answer = _missing_path_state_answer(context, question)
        if path_state_answer:
            return path_state_answer
        no_benefit_answer = _no_treatment_benefit_answer(context, question)
        if no_benefit_answer:
            return no_benefit_answer
        missing_evidence_ranking = _missing_evidence_ranking_answer(context, question)
        if missing_evidence_ranking:
            return missing_evidence_ranking
        business_impact_answer = _business_impact_answer(context, question)
        if business_impact_answer:
            return business_impact_answer
        assessment_evidence_answer = _assessment_evidence_answer(context, question)
        if assessment_evidence_answer:
            return assessment_evidence_answer
        system, user = build_prompts(context, question)
        reasons: tuple[str, ...] = ("response_schema",)
        for attempt in range(2):
            attempt_user = user
            if attempt:
                attempt_user += "\nThe previous candidate was rejected by deterministic checks: " + ", ".join(reasons) + ". Return a corrected candidate. Include every required field, cite every fact used, copy only exact rendered values, remove unsupported claims, and keep key_points to at most three. If unsupported_qualitative_label appears, do not use high, low, significant, moderate, elevated, substantial, material or heavier. If noncanonical_metric_label appears, use only AAL, VaR95, VaR99, TVaR95, TVaR99 and P(Material Event)."
            try:
                generated_payload = self.provider.generate(system_prompt=system, user_prompt=attempt_user, max_tokens=self.max_tokens, temperature=self.temperature)
            except ValueError:
                reasons = ("provider_response",)
                continue
            payload = generated_payload.payload if isinstance(generated_payload, ProviderResult) else generated_payload
            payload = _complete_exact_fact_citations(payload, context)
            reasons = _response_shape_reasons(payload)
            if reasons:
                continue
            generated = CopilotResponse.from_dict(payload)
            valid, reasons = verify_response(generated, context)
            if valid:
                return {"status": "VERIFIED", "answer": generated.answer, "key_points": list(generated.key_points), "caveats": list(generated.caveats), "supporting_fact_ids": list(generated.supporting_fact_ids), "related_entities": list(generated.related_entities), "context_type": context.context_type, "schema_version": "1.0.0"}
        return _rejected(reasons)


def _response_shape_reasons(value: Any) -> tuple[str, ...]:
    required = {"schema_version", "context_type", "answer", "key_points", "caveats", "supporting_fact_ids", "related_entities", "status"}
    if not isinstance(value, dict) or set(value) != required:
        return ("response_schema",)
    if not isinstance(value.get("answer"), str) or len(value["answer"]) > 1800:
        return ("response_schema",)
    list_limits = {"key_points": (3, 500), "caveats": (3, 500), "supporting_fact_ids": (100, 128)}
    for key, (max_items, max_length) in list_limits.items():
        items = value.get(key)
        if not isinstance(items, list) or len(items) > max_items or any(not isinstance(item, str) or len(item) > max_length for item in items):
            return ("response_schema",)
    entities = value.get("related_entities")
    if not isinstance(entities, list) or any(not isinstance(item, dict) or set(item) != {"entity_type", "entity_id"} or not all(isinstance(part, str) for part in item.values()) for item in entities):
        return ("response_schema",)
    return ()


def _rejected(reasons: Any) -> dict[str, Any]:
    return {"status": "REJECTED", "answer": None, "supporting_fact_ids": [], "error_code": "COPILOT_VERIFICATION_FAILED", "verification_reasons": list(reasons)}


def _cross_view_redirect(current_view: str, question: str) -> str | None:
    text = question.casefold()
    if current_view != "results.insurance" and any(term in text for term in ("insurance", "policy attach", "exhaustion probability", "uninsured")):
        return "That information is available in the Insurance view."
    return None


def _standard_response(context: Any, answer: str, facts: list[Any], *, caveats: list[str] | None = None) -> dict[str, Any]:
    return {
        "status": "VERIFIED",
        "answer": answer,
        "key_points": [],
        "caveats": caveats or [],
        "supporting_fact_ids": [fact.fact_id for fact in facts],
        "related_entities": [context.selected_entity] if context.selected_entity else [],
        "context_type": context.context_type,
        "schema_version": "1.0.0",
    }


def _fact(context: Any, *, path: str | None = None, label: str | None = None) -> Any | None:
    return next(
        (
            fact
            for fact in context.facts
            if (path is None or fact.source_path == path) and (label is None or fact.label == label)
        ),
        None,
    )


def _assessment_evidence_answer(context: Any, question: str) -> dict[str, Any] | None:
    if context.context_type != "assessment.business_impact" or "evidence" not in question.casefold():
        return None
    count = _fact(context, path="/evidence/meaningful_count")
    if count is None:
        return None
    text = question.casefold()
    if any(term in text for term in ("continue without", "evidence optional", "is supporting evidence optional")):
        answer = "Yes. Supporting evidence is optional, so you can continue without adding it. Add evidence when it helps a reviewer verify an input or understand why an assumption was changed."
    elif any(term in text for term in ("what evidence", "evidence would", "evidence helps", "improve confidence")):
        answer = "Useful supporting evidence includes current policies, architecture diagrams, control test reports, business-impact analyses and finance-approved estimates. Add only sources that directly support the assessment input or adjustment."
    elif any(term in text for term in ("do i have", "supporting evidence", "evidence provided", "evidence attached")):
        answer = f"This assessment currently has {count.rendered_value} of supporting evidence. Placeholder records are not counted."
    else:
        return None
    return _standard_response(context, answer, [count])


def _overview_answer(context: Any, question: str) -> dict[str, Any] | None:
    if context.context_type != "results.overview" or not any(term in question.casefold() for term in ("headline", "tail risk", "overview", "metric")):
        return None
    aal = _fact(context, path="/summary/prudent/aal")
    var99 = _fact(context, path="/summary/prudent/var99")
    tvar99 = _fact(context, path="/summary/prudent/tvar99")
    probability = _fact(context, path="/summary/prudent/p_any_event")
    comparisons = [fact for fact in context.facts if fact.label == "Governed comparison"]
    if not all((aal, var99, tvar99, probability)) or len(comparisons) < 2:
        return None
    answer = (
        f"Expected annual loss (AAL) is {aal.rendered_value}, while severe-loss outcomes are larger in absolute terms: "
        f"VaR99 is {var99.rendered_value} and TVaR99 is {tvar99.rendered_value}. "
        "This means expected annual loss is smaller than the losses represented in the tail of the distribution. "
        f"The modelled probability of at least one material event during the year, P(Material Event), is {probability.rendered_value}."
    )
    return _standard_response(context, answer, [aal, var99, tvar99, probability, *comparisons[:2]])


def _risk_driver_answer(context: Any, question: str) -> dict[str, Any] | None:
    if context.context_type != "results.risk_drivers" or "driv" not in question.casefold():
        return None
    actor = _fact(context, label="Dominant actor")
    scenario = _fact(context, label="Dominant scenario")
    driver = _fact(context, label="Largest AAL loss driver")
    if not all((actor, scenario, driver)):
        return None
    answer = f"The dominant actor is {actor.rendered_value}, the dominant scenario is {scenario.rendered_value}, and the largest AAL loss driver is {driver.rendered_value}."
    return _standard_response(context, answer, [actor, scenario, driver])


def _scenario_answer(context: Any, question: str) -> dict[str, Any] | None:
    if context.context_type != "results.scenarios" or not any(term in question.casefold() for term in ("scenario", "material", "severity")):
        return None
    name = _fact(context, label="Dominant scenario") or next((fact for fact in context.facts if fact.source_path.endswith("/name")), None)
    tvar95 = next((fact for fact in context.facts if fact.source_path.endswith("/contribution/tvar95")), None)
    tvar99 = next((fact for fact in context.facts if fact.source_path.endswith("/contribution/tvar99")), None)
    selected_aal = next((fact for fact in context.facts if fact.source_path.endswith("/metrics/selected_aal")), None)
    comparisons = [fact for fact in context.facts if fact.label == "Governed comparison"]
    if not all((name, tvar95, tvar99, selected_aal)):
        return None
    rank = " is the leading scenario in the returned ordering" if name.label == "Dominant scenario" else ""
    answer = (
        f"{name.rendered_value}{rank}. It contributes {tvar95.rendered_value} to TVaR95 and {tvar99.rendered_value} to TVaR99, "
        f"while its selected AAL contribution is {selected_aal.rendered_value}."
    )
    if len(comparisons) == 2:
        answer += " Both tail-loss contributions are greater than its selected AAL contribution."
    return _standard_response(context, answer, [name, tvar95, tvar99, selected_aal, *comparisons])


def _business_impact_answer(context: Any, question: str) -> dict[str, Any] | None:
    if context.context_type != "results.business_impact" or not any(term in question.casefold() for term in ("driv", "impact", "loss")):
        return None
    category = _fact(context, label="Largest AAL loss category")
    category_aal = _fact(context, path="/loss/categories/0/aal")
    driver = _fact(context, label="Largest AAL loss driver")
    driver_category = _fact(context, path="/loss/drivers/0/category")
    if not all((category, category_aal, driver)):
        return None
    detail = f" within {driver_category.rendered_value}" if driver_category else ""
    answer = f"{category.rendered_value} is the largest modelled loss category, contributing {category_aal.rendered_value} to AAL. Within the underlying loss drivers, {driver.rendered_value} is the largest individual contributor{detail}."
    return _standard_response(context, answer, [category, category_aal, driver, *([driver_category] if driver_category else [])])


def _missing_path_state_answer(context: Any, question: str) -> dict[str, Any] | None:
    if context.context_type != "results.attack_paths" or not any(term in question.casefold() for term in ("open", "closed", "closing", "path state")):
        return None
    state_facts = [fact for fact in context.facts if str(fact.value).casefold() in {"open", "closed", "conditional", "unknown"}]
    if state_facts:
        return None
    route_fact = next((fact for fact in context.facts if fact.source_path.endswith(("/route", "/path", "/path_name"))), None)
    cited = [route_fact.fact_id] if route_fact else ([context.facts[0].fact_id] if context.facts else [])
    subject = f" for {route_fact.rendered_value}" if route_fact else " for this path"
    return {
        "status": "VERIFIED",
        "answer": f"The current result does not contain a governed path-state value{subject}, so I cannot determine whether it is OPEN or CLOSED. I can still explain its returned probability facts, but this result provides no architecture-gate, barrier or control-state facts that explain a path state.",
        "key_points": [],
        "caveats": ["No path state has been inferred."],
        "supporting_fact_ids": cited,
        "related_entities": [context.selected_entity] if context.selected_entity else [],
        "context_type": context.context_type,
        "schema_version": "1.0.0",
    }


def _complete_exact_fact_citations(payload: Any, context: Any) -> Any:
    if not isinstance(payload, dict):
        return payload
    value = dict(payload)
    prose = " ".join(
        item
        for item in (value.get("answer"), *(value.get("key_points") or ()), *(value.get("caveats") or ()))
        if isinstance(item, str)
    ).casefold()
    cited = [item for item in value.get("supporting_fact_ids", ()) if isinstance(item, str)]
    for fact in context.facts:
        rendered = str(fact.rendered_value or "").strip()
        if rendered and rendered.casefold() in prose and fact.fact_id not in cited:
            cited.append(fact.fact_id)
    value["supporting_fact_ids"] = cited
    return value


def _no_treatment_benefit_answer(context: Any, question: str) -> dict[str, Any] | None:
    if context.context_type != "results.treatment" or not any(term in question.casefold() for term in ("priorit", "benefit", "reduce", "reduction")):
        return None
    reduction_facts = [fact for fact in context.facts if "reduction" in fact.label.casefold() and fact.type == "numeric"]
    if not reduction_facts or any(float(fact.value) != 0.0 for fact in reduction_facts):
        return None
    fact = next((item for item in reduction_facts if item.label == "AAL reduction" and "/prudent/" in item.source_path), reduction_facts[0])
    name_fact = next((item for item in context.facts if item.source_path.endswith("/name")), None)
    subject = f" for {name_fact.rendered_value}" if name_fact else " for this treatment"
    cited = [fact.fact_id, *([name_fact.fact_id] if name_fact else [])]
    return {
        "status": "VERIFIED",
        "answer": f"The modelled AAL reduction{subject} is {fact.rendered_value}. On that basis, the current result does not support prioritising this treatment for AAL reduction.",
        "key_points": [],
        "caveats": ["No implementation cost, return on investment or practical priority has been inferred."],
        "supporting_fact_ids": cited,
        "related_entities": [context.selected_entity] if context.selected_entity else [],
        "context_type": context.context_type,
        "schema_version": "1.0.0",
    }


def _missing_evidence_ranking_answer(context: Any, question: str) -> dict[str, Any] | None:
    if context.context_type != "results.evidence" or not any(term in question.casefold() for term in ("weakest", "strongest", "matter most", "priorit")):
        return None
    ranking_facts = [fact for fact in context.facts if fact.label.casefold().startswith(("dominant", "largest", "top", "rank"))]
    if ranking_facts:
        return None
    cited = [context.facts[0].fact_id] if context.facts else []
    return {
        "status": "VERIFIED",
        "answer": "The current result does not contain an explicit governed evidence-quality ranking, so I cannot identify a weakest evidence area.",
        "key_points": [],
        "caveats": ["The Evidence view can still show the returned records without assigning an unsupported priority."],
        "supporting_fact_ids": cited,
        "related_entities": [],
        "context_type": context.context_type,
        "schema_version": "1.0.0",
    }


def bedrock_service() -> CopilotService:
    from crq.copilot.providers.bedrock import BedrockProvider

    return CopilotService(
        BedrockProvider(os.environ.get("CRQ_BEDROCK_MODEL_ID", "")),
        max_tokens=int(os.environ.get("CRQ_COPILOT_MAX_TOKENS", "700")),
        temperature=float(os.environ.get("CRQ_COPILOT_TEMPERATURE", "0")),
    )
