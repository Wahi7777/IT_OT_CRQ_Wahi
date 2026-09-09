from __future__ import annotations

import json
from pathlib import Path

import pytest

from crq.copilot.context import build_view_context
from crq.copilot.models import CopilotResponse
from crq.copilot.verifier import verify_response


ROOT = Path(__file__).resolve().parents[2]
REQUEST = json.loads((ROOT / "contracts/examples/assessment-run-request-it-fs.json").read_text())["assessment"]
RESULT = json.loads((ROOT / "contracts/examples/assessment-run-response-it-fs.json").read_text())["result"]
OT_REQUEST = json.loads((ROOT / "contracts/examples/assessment-run-request-ot-pg.json").read_text())["assessment"]
OT_RESULT = json.loads((ROOT / "contracts/examples/assessment-run-response-ot-pg.json").read_text())["result"]


def overview():
    return build_view_context(current_view="results.overview", assessment=REQUEST, result=RESULT)


def response(context, answer, *, fact_ids=None, entities=()):
    ids = fact_ids if fact_ids is not None else (context.facts[0].fact_id,)
    return CopilotResponse(context.context_type, answer, tuple(ids), tuple(entities))


def test_accepts_exact_governed_currency_and_percentage_formatting():
    context = overview()
    money = next(fact for fact in context.facts if fact.source_path == "/summary/prudent/tvar99")
    probability = next(fact for fact in context.facts if fact.source_path == "/summary/prudent/p_any_event")
    valid, reasons = verify_response(response(context, f"TVaR99 is {money.rendered_value}; material-event probability is {probability.rendered_value}.", fact_ids=(money.fact_id, probability.fact_id)), context)
    assert valid, reasons


def test_material_event_probability_is_rendered_as_business_percentage():
    context = overview()
    probability = next(fact for fact in context.facts if fact.source_path == "/summary/prudent/p_any_event")
    assert probability.rendered_value == "12.76%"
    valid, reasons = verify_response(
        response(context, "P(Material Event) is 12.76%.", fact_ids=(probability.fact_id,)),
        context,
    )
    assert valid, reasons


def test_accepts_exact_rendered_day_value_and_percentile_label():
    context = build_view_context(current_view="results.business_impact", assessment=OT_REQUEST, result=OT_RESULT)
    downtime = next(fact for fact in context.facts if fact.source_path == "/impact/ot_downtime/downtime_p95")
    valid, reasons = verify_response(
        response(context, f"Downtime at the 95th percentile is {downtime.rendered_value}.", fact_ids=(downtime.fact_id,)),
        context,
    )
    assert valid, reasons


@pytest.mark.parametrize("claim", ["TVaR99 is $75M.", "AAL is $8.2M.", "The probability is 67%.", "The result is about $50M."])
def test_rejects_invented_or_ungoverned_numbers(claim):
    context = overview()
    valid, reasons = verify_response(response(context, claim), context)
    assert not valid
    assert any(reason.startswith("unsupported_number") for reason in reasons)


def test_rejects_unknown_fact_id_and_entity():
    context = overview()
    invalid = response(context, "The supplied result is available.", fact_ids=("vf_deadbeefdeadbeef",), entities=({"entity_type": "actor", "entity_id": "Invented actor"},))
    valid, reasons = verify_response(invalid, context)
    assert not valid
    assert "unknown_or_missing_fact_id" in reasons
    assert "unknown_entity" in reasons


def test_cross_view_insurance_number_is_rejected_on_attack_paths():
    context = build_view_context(current_view="results.attack_paths", assessment=REQUEST, result=RESULT)
    valid, reasons = verify_response(response(context, "Insurance exhaustion probability is 12.5%."), context)
    assert not valid
    assert any(reason.startswith("unsupported_number") for reason in reasons)


def test_fabricated_ranking_is_rejected_without_rank_fact():
    context = overview()
    valid, reasons = verify_response(response(context, "Nation-state is the dominant actor."), context)
    assert not valid
    assert "unsupported_ranking" in reasons


def test_fabricated_evidence_priority_is_rejected_without_rank_fact():
    context = build_view_context(current_view="results.evidence", assessment=REQUEST, result=RESULT)
    valid, reasons = verify_response(response(context, "This is the weakest evidence area."), context)
    assert not valid
    assert "unsupported_ranking" in reasons


def test_second_and_third_rank_claims_require_explicit_rank_facts():
    context = build_view_context(current_view="results.business_impact", assessment=OT_REQUEST, result=OT_RESULT)
    largest = next(fact for fact in context.facts if fact.label == "Largest AAL loss category")
    valid, reasons = verify_response(
        response(context, "The second and third most material categories follow the largest category.", fact_ids=(largest.fact_id,)),
        context,
    )
    assert not valid
    assert "unsupported_ranking" in reasons


def test_correct_dominant_actor_requires_and_accepts_the_specific_rank_fact():
    context = overview()
    dominant = next(fact for fact in context.facts if fact.label == "Dominant actor")
    valid, reasons = verify_response(response(context, f"{dominant.value} is the dominant actor.", fact_ids=(dominant.fact_id,)), context)
    assert valid, reasons


def test_number_present_elsewhere_on_page_is_rejected_when_not_cited():
    context = overview()
    money = next(fact for fact in context.facts if fact.source_path == "/summary/prudent/tvar99")
    unrelated = next(fact for fact in context.facts if fact.source_path == "/summary/prudent/aal")
    valid, reasons = verify_response(response(context, f"TVaR99 is {money.rendered_value}.", fact_ids=(unrelated.fact_id,)), context)
    assert not valid
    assert any(reason.startswith("unsupported_number") for reason in reasons)


@pytest.mark.parametrize("entity_type", ["scenario", "actor", "route", "treatment"])
def test_rejects_each_invented_entity_family(entity_type):
    context = overview()
    invalid = response(context, "The result references an unsupported entity.", entities=({"entity_type": entity_type, "entity_id": f"invented-{entity_type}"},))
    valid, reasons = verify_response(invalid, context)
    assert not valid
    assert "unknown_entity" in reasons


def test_rejects_uncited_path_state_claim():
    context = build_view_context(current_view="results.attack_paths", assessment=REQUEST, result=RESULT)
    valid, reasons = verify_response(response(context, "This path is OPEN."), context)
    assert not valid
    assert "unsupported_path_state" in reasons


@pytest.mark.parametrize(
    ("claim", "reason"),
    [
        ("P(Material Event) is approximately 13%.", "unsupported_approximation"),
        ("TVaR99 is high.", "unsupported_qualitative_label"),
        ("The loss is significant.", "unsupported_qualitative_label"),
        ("The modelled reduction of 0 is returned.", "ambiguous_reduction"),
        ("Tvar99 is $49.65M.", "noncanonical_metric_label"),
        ("Average Annual Loss (AAL) is $1.16M.", "noncanonical_metric_label"),
        ("The distribution has heavier tail risk.", "unsupported_qualitative_label"),
        ("This conclusion is presented without external validation.", "unsupported_external_claim"),
    ],
)
def test_rejects_product_owner_prohibited_wording(claim, reason):
    context = overview()
    fact_ids = tuple(fact.fact_id for fact in context.facts)
    valid, reasons = verify_response(response(context, claim, fact_ids=fact_ids), context)
    assert not valid
    assert reason in reasons


def test_accepts_governed_comparison_when_explicitly_cited():
    context = overview()
    comparison = next(fact for fact in context.facts if fact.value == "TVaR99 is greater than VaR99.")
    tvar99 = next(fact for fact in context.facts if fact.source_path == "/summary/prudent/tvar99")
    var99 = next(fact for fact in context.facts if fact.source_path == "/summary/prudent/var99")
    valid, reasons = verify_response(
        response(
            context,
            f"TVaR99 at {tvar99.rendered_value} is greater than VaR99 at {var99.rendered_value}.",
            fact_ids=(comparison.fact_id, tvar99.fact_id, var99.fact_id),
        ),
        context,
    )
    assert valid, reasons
