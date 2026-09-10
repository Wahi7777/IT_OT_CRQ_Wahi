from __future__ import annotations

import json
from pathlib import Path

from crq.copilot.context import build_view_context
from crq.copilot.providers.base import ProviderResult
from crq.copilot.service import CopilotService


ROOT = Path(__file__).resolve().parents[2]
REQUEST = json.loads((ROOT / "contracts/examples/assessment-run-request-it-fs.json").read_text())["assessment"]
RESULT = json.loads((ROOT / "contracts/examples/assessment-run-response-it-fs.json").read_text())["result"]
OT_REQUEST = json.loads((ROOT / "contracts/examples/assessment-run-request-ot-pg.json").read_text())["assessment"]
OT_RESULT = json.loads((ROOT / "contracts/examples/assessment-run-response-ot-pg.json").read_text())["result"]


class Provider:
    def __init__(self, payload):
        self.payload = payload
        self.calls = 0

    def generate(self, **_kwargs):
        self.calls += 1
        return ProviderResult(self.payload)


def test_malformed_provider_response_is_rejected_before_display():
    provider = Provider({"answer": "Unstructured response"})
    reply = CopilotService(provider).query(current_view="results.overview", question="Explain", assessment=REQUEST, result=RESULT)
    assert reply["status"] == "REJECTED"
    assert reply["verification_reasons"] == ["response_schema"]


def test_cross_view_question_returns_deterministic_navigation_without_model_call():
    provider = Provider({})
    reply = CopilotService(provider).query(current_view="results.attack_paths", question="What is our insurance exhaustion probability?", assessment=REQUEST, result=RESULT)
    assert reply["status"] == "VERIFIED"
    assert reply["answer"] == "That information is available in the Insurance view."
    assert reply["supporting_fact_ids"] == []
    assert provider.calls == 0


def test_exact_fact_response_is_verified():
    context = build_view_context(current_view="results.overview", assessment=REQUEST, result=RESULT)
    fact = next(item for item in context.facts if item.source_path == "/summary/prudent/aal")
    payload = {
        "schema_version": "1.0.0",
        "context_type": "results.overview",
        "answer": f"Prudent AAL is {fact.rendered_value}.",
        "key_points": [],
        "caveats": [],
        "supporting_fact_ids": [fact.fact_id],
        "related_entities": [],
        "status": "READY",
    }
    reply = CopilotService(Provider(payload)).query(current_view="results.overview", question="Explain AAL", assessment=REQUEST, result=RESULT)
    assert reply["status"] == "VERIFIED"


def test_missing_evidence_ranking_is_answered_without_inventing_priority():
    provider = Provider({})
    reply = CopilotService(provider).query(
        current_view="results.evidence",
        question="Where is the assessment weakest?",
        assessment=REQUEST,
        result=RESULT,
    )
    assert reply["status"] == "VERIFIED"
    assert "does not contain an explicit governed evidence-quality ranking" in reply["answer"]
    assert provider.calls == 0


def test_missing_path_state_refusal_identifies_the_governed_data_gap():
    provider = Provider({})
    route = RESULT["architecture"]["route_path_states"][0]["route"]
    reply = CopilotService(provider).query(
        current_view="results.attack_paths",
        question="Why is this route open?",
        assessment=REQUEST,
        result=RESULT,
        selected_entity={"entity_type": "route", "entity_id": route},
    )
    assert reply["status"] == "VERIFIED"
    assert route in reply["answer"]
    assert "does not contain a governed path-state value" in reply["answer"]
    assert "No path state has been inferred." in reply["caveats"]
    assert provider.calls == 0


def test_zero_treatment_answer_names_aal_and_currency_unit():
    provider = Provider({})
    control = RESULT["treatments"]["individual_controls"][0]
    reply = CopilotService(provider).query(
        current_view="results.treatment",
        question="Why is this treatment prioritized?",
        assessment=REQUEST,
        result=RESULT,
        selected_entity={"entity_type": "control", "entity_id": control["cid"]},
    )
    assert reply["status"] == "VERIFIED"
    assert reply["answer"].startswith(f"The modelled AAL reduction for {control['name']} is $0.00.")
    assert "modelled reduction of 0" not in reply["answer"]
    assert provider.calls == 0


def test_overview_standard_prompt_uses_business_facing_governed_summary():
    provider = Provider({})
    reply = CopilotService(provider).query(
        current_view="results.overview",
        question="Explain headline metrics",
        assessment=REQUEST,
        result=RESULT,
    )
    assert reply["status"] == "VERIFIED"
    assert "Expected annual loss (AAL) is $1.16M" in reply["answer"]
    assert "VaR99 is $23.33M" in reply["answer"]
    assert "TVaR99 is $49.65M" in reply["answer"]
    assert "P(Material Event), is 12.76%" in reply["answer"]
    assert provider.calls == 0


def test_previously_accepted_risk_driver_response_is_stable():
    provider = Provider({})
    reply = CopilotService(provider).query(
        current_view="results.risk_drivers",
        question="What drives this result?",
        assessment=REQUEST,
        result=RESULT,
    )
    assert reply["answer"] == (
        "The dominant actor is Cybercriminal, the dominant scenario is Critical business-service disruption, "
        "and the largest AAL loss driver is Business downtime costs."
    )
    assert provider.calls == 0


def test_previously_accepted_ot_business_impact_response_is_stable():
    provider = Provider({})
    reply = CopilotService(provider).query(
        current_view="results.business_impact",
        question="What drives the business impact?",
        assessment=OT_REQUEST,
        result=OT_RESULT,
    )
    assert reply["answer"] == (
        "Business Interruption costs is the largest modelled loss category, contributing $924.04K to AAL. "
        "Within the underlying loss drivers, OT and digital forensic investigation is the largest individual contributor within Incident response costs."
    )
    assert provider.calls == 0


def test_assessment_evidence_optionality_is_answered_without_model_invention():
    provider = Provider({})
    reply = CopilotService(provider).query(
        current_view="assessment.business_impact",
        question="Is supporting evidence optional?",
        assessment=OT_REQUEST,
    )
    assert reply["status"] == "VERIFIED"
    assert reply["answer"].startswith("Yes. Supporting evidence is optional")
    assert reply["supporting_fact_ids"]
    assert provider.calls == 0


def test_scenario_standard_prompt_interprets_tail_contributions_without_qualitative_magnitude():
    provider = Provider({})
    scenario = OT_RESULT["decomposition"]["scenarios"][0]
    reply = CopilotService(provider).query(
        current_view="results.scenarios",
        question="Why is this scenario material?",
        assessment=OT_REQUEST,
        result=OT_RESULT,
        selected_entity={"entity_type": "scenario", "entity_id": scenario["id"]},
    )
    assert reply["status"] == "VERIFIED"
    assert "contributes $12.26M to TVaR95 and $55.21M to TVaR99" in reply["answer"]
    assert "Both tail-loss contributions are greater than its selected AAL contribution." in reply["answer"]
    assert not any(word in reply["answer"].casefold() for word in ("high", "significant", "elevated", "substantial"))
    assert provider.calls == 0
