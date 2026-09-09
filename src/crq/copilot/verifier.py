"""Reject unsupported facts, entities and numeric claims before display."""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

from crq.copilot.models import CopilotResponse, ViewContextBundle


_NUMBER = re.compile(r"(?<![A-Za-z0-9_])(?:[$€£]\s*)?[-+]?\d[\d,]*(?:\.\d+)?(?:[eE][-+]?\d+)?\s*(?:%|[KMB])?", re.IGNORECASE)


def verify_response(response: CopilotResponse, context: ViewContextBundle) -> tuple[bool, tuple[str, ...]]:
    reasons: list[str] = []
    if response.schema_version != "1.0.0" or response.context_type != context.context_type or response.status != "READY" or not response.answer.strip():
        reasons.append("schema_or_context")
    allowed_ids = {fact.fact_id for fact in context.facts}
    if not response.supporting_fact_ids or not set(response.supporting_fact_ids).issubset(allowed_ids):
        reasons.append("unknown_or_missing_fact_id")
    allowed_entities = {(item["entity_type"], item["entity_id"]) for item in context.allowed_entities}
    if any((item.get("entity_type"), item.get("entity_id")) not in allowed_entities for item in response.related_entities):
        reasons.append("unknown_entity")
    text = " ".join((response.answer, *response.key_points, *response.caveats))
    folded = text.casefold()
    if re.search(r"\bvf_[0-9a-f]{16}\b", text, re.IGNORECASE):
        reasons.append("visible_internal_fact_id")
    if re.search(r"\b(?:approximately|approx\.?|about|around)\b", folded):
        reasons.append("unsupported_approximation")
    if "external validation" in folded:
        reasons.append("unsupported_external_claim")
    if re.search(r"\b(?:Tvar|TVar|tvar|Var|var)\s?(?:95|99)\b|\b(?:Average Annual Loss|Annual Average Loss)\b", text):
        reasons.append("noncanonical_metric_label")
    allowed_numbers = _allowed_numeric_forms(context, set(response.supporting_fact_ids))
    for match in _NUMBER.finditer(text):
        token = match.group(0).strip()
        if _identifier_number(text, match.start()):
            continue
        percent_word = text[match.end() :].lstrip().casefold().startswith("percent") and f"{token}%" in allowed_numbers
        if token not in allowed_numbers and _normalise_number(token) not in allowed_numbers and not percent_word and not _metric_name_number(context, text, match.start(), match.end(), token):
            reasons.append(f"unsupported_number:{token}")
    entity_labels = {item["label"].casefold() for item in context.allowed_entities}
    ranking_claims = ("dominant", "highest", "largest", "leading", "top-ranked", "most material", "most critical", "weakest", "strongest", "matters most")
    if any(term in folded for term in ranking_claims):
        cited_rank_facts = [
            fact for fact in context.facts
            if fact.fact_id in response.supporting_fact_ids and fact.label.casefold().startswith(("dominant", "largest", "top"))
        ]
        named_entities = {label for label in entity_labels if label in folded}
        supported_ranked_values = {str(fact.value).casefold() for fact in cited_rank_facts}
        if not cited_rank_facts or (named_entities and not named_entities.issubset(supported_ranked_values)):
            reasons.append("unsupported_ranking")
        if "most material" in folded and not any("most material" in fact.label.casefold() for fact in cited_rank_facts):
            reasons.append("unsupported_ranking")
    cited_facts = [fact for fact in context.facts if fact.fact_id in response.supporting_fact_ids]
    supported_qualitative = any(
        fact.label.casefold().startswith(("dominant", "largest", "top", "rank"))
        or any(term in fact.label.casefold() for term in ("threshold", "benchmark", "appetite", "status", "governed comparison"))
        for fact in cited_facts
    )
    qualitative_text = re.sub(r"p\s*\(\s*material event\s*\)|material[- ]event", "", folded)
    if re.search(r"\b(?:high|low|significant|moderate|elevated|substantial|heavier)\b", qualitative_text):
        reasons.append("unsupported_qualitative_label")
    if re.search(r"\bmuch\s+(?:larger|smaller|greater|higher|lower)\b", qualitative_text):
        reasons.append("unsupported_qualitative_label")
    if re.search(r"\bmaterial\b", qualitative_text) and not supported_qualitative:
        reasons.append("unsupported_qualitative_label")
    if re.search(r"\b(?:larger|smaller|greater|lower|exceeds?|higher)\b", folded) and not any(fact.label == "Governed comparison" for fact in cited_facts):
        reasons.append("unsupported_comparison")
    ordinal_claims = set(re.findall(r"\b(?:second|third|fourth|fifth)\b", folded))
    if ordinal_claims:
        cited_labels = {
            fact.label.casefold()
            for fact in context.facts
            if fact.fact_id in response.supporting_fact_ids
        }
        if any(not any(label.startswith(ordinal) for label in cited_labels) for ordinal in ordinal_claims):
            reasons.append("unsupported_ranking")
    path_states = {state for state in ("open", "closed", "conditional", "unknown") if context.context_type == "results.attack_paths" and re.search(rf"\b{state}\b", text, re.IGNORECASE)}
    if path_states:
        cited_states = {
            str(fact.value).casefold()
            for fact in context.facts
            if fact.fact_id in response.supporting_fact_ids and str(fact.value).casefold() in {"open", "closed", "conditional", "unknown"}
        }
        if not path_states.issubset(cited_states):
            reasons.append("unsupported_path_state")
    for match in re.finditer(r"\breduction\s+of\s+" + _NUMBER.pattern, text, re.IGNORECASE):
        nearby = text[max(0, match.start() - 24) : match.start()].casefold()
        if not re.search(r"(?:aal|var95|var99|tvar95|tvar99|percentage|percent)\s*$", nearby):
            reasons.append("ambiguous_reduction")
    cited_entity_values = {str(fact.value).casefold() for fact in cited_facts}
    for label in entity_labels:
        if label in folded and label not in cited_entity_values:
            reasons.append("uncited_entity_claim")
    for item in response.related_entities:
        if item.get("entity_id", "").casefold() not in {value.casefold() for value in entity_labels} | {entity_id.casefold() for _, entity_id in allowed_entities}:
            reasons.append("unsupported_entity_claim")
    return not reasons, tuple(dict.fromkeys(reasons))


def _allowed_numeric_forms(context: ViewContextBundle, cited_fact_ids: set[str]) -> set[str]:
    allowed: set[str] = set()
    for fact in context.facts:
        if fact.type != "numeric" or fact.fact_id not in cited_fact_ids:
            continue
        allowed.add(str(fact.value))
        if fact.rendered_value:
            allowed.add(fact.rendered_value)
            allowed.add(_normalise_number(fact.rendered_value))
            # The scanner intentionally extracts only the numeric token from
            # prose such as ``0.30 days``. Permit that exact token when the
            # complete governed rendering belongs to a cited fact; this does
            # not permit rounding or unit conversion.
            rendered_match = _NUMBER.search(fact.rendered_value)
            if rendered_match:
                rendered_number = rendered_match.group(0).strip()
                allowed.add(rendered_number)
                allowed.add(_normalise_number(rendered_number))
    return allowed


def _normalise_number(value: str) -> str:
    token = value.replace(",", "").replace(" ", "")
    prefix = token[:1] if token[:1] in "$€£" else ""
    if prefix:
        token = token[1:]
    suffix = token[-1:].upper() if token[-1:].upper() in {"%", "K", "M", "B"} else ""
    if suffix:
        token = token[:-1]
    try:
        number = Decimal(token).normalize()
    except InvalidOperation:
        return value
    return f"{prefix}{number}{suffix}"


def _metric_name_number(context: ViewContextBundle, text: str, start: int, end: int, token: str) -> bool:
    metric_token = token.rstrip("%")
    if metric_token not in {"95", "99"}:
        return False
    nearby = text[max(0, start - 16) : min(len(text), end + 16)].casefold()
    labels = {fact.label.casefold().replace(" ", "") for fact in context.facts}
    return bool(
        re.search(r"(?:var|tvar|percentile)\s*" + metric_token + r"(?:st|th|%)?", nearby)
        or re.search(metric_token + r"(?:st|th|%)?\s*percentile", nearby)
        or any(label.endswith(metric_token) for label in labels if label.startswith(("var", "tvar")))
    )


def _identifier_number(text: str, start: int) -> bool:
    return start >= 2 and text[start - 1] == "-" and text[start - 2].isalnum()
