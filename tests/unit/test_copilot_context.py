from __future__ import annotations

import json
from pathlib import Path

import pytest

from crq.copilot.context import build_view_context


ROOT = Path(__file__).resolve().parents[2]
IT_REQUEST = json.loads((ROOT / "contracts/examples/assessment-run-request-it-fs.json").read_text())
IT_RESULT = json.loads((ROOT / "contracts/examples/assessment-run-response-it-fs.json").read_text())["result"]
OT_REQUEST = json.loads((ROOT / "contracts/examples/assessment-run-request-ot-pg.json").read_text())
OT_RESULT = json.loads((ROOT / "contracts/examples/assessment-run-response-ot-pg.json").read_text())["result"]


@pytest.mark.parametrize(
    ("view", "assessment", "result"),
    [
        ("results.overview", IT_REQUEST["assessment"], IT_RESULT),
        ("results.risk_drivers", IT_REQUEST["assessment"], IT_RESULT),
        ("results.scenarios", IT_REQUEST["assessment"], IT_RESULT),
        ("results.attack_paths", IT_REQUEST["assessment"], IT_RESULT),
        ("results.treatment", IT_REQUEST["assessment"], IT_RESULT),
        ("results.evidence", IT_REQUEST["assessment"], IT_RESULT),
        ("results.overview", OT_REQUEST["assessment"], OT_RESULT),
        ("results.scenarios", OT_REQUEST["assessment"], OT_RESULT),
        ("results.attack_paths", OT_REQUEST["assessment"], OT_RESULT),
        ("results.business_impact", OT_REQUEST["assessment"], OT_RESULT),
        ("results.treatment", OT_REQUEST["assessment"], OT_RESULT),
        ("results.evidence", OT_REQUEST["assessment"], OT_RESULT),
    ],
)
def test_governed_evaluation_views_build_deterministically(view, assessment, result):
    first = build_view_context(current_view=view, assessment=assessment, result=result, run_id="run-1", result_hash="hash-1")
    second = build_view_context(current_view=view, assessment=assessment, result=result, run_id="run-1", result_hash="hash-1")
    assert first.to_dict() == second.to_dict()
    assert first.facts
    assert len({fact.fact_id for fact in first.facts}) == len(first.facts)
    assert all(fact.source_path.startswith("/") for fact in first.facts)


@pytest.mark.parametrize("view", ["assessment.organization", "assessment.architecture", "assessment.controls", "assessment.business_impact", "assessment.risk_appetite_insurance", "assessment.review"])
def test_assessment_views_are_supported(view):
    context = build_view_context(current_view=view, assessment=IT_REQUEST["assessment"])
    assert context.context_type == view
    assert context.suggested_questions


def test_business_impact_context_counts_only_meaningful_evidence():
    assessment = dict(OT_REQUEST["assessment"])
    assessment["evidence"] = [
        {"description": "n/a", "source": "workbook", "hash": None, "observed_at": None},
        {"description": "Approved BIA", "source": "Finance", "hash": None, "observed_at": None},
    ]
    context = build_view_context(current_view="assessment.business_impact", assessment=assessment)
    fact = next(item for item in context.facts if item.source_path == "/evidence/meaningful_count")
    assert fact.value == 1
    assert fact.rendered_value == "1 record"


def test_overview_does_not_leak_raw_monte_carlo_or_unrelated_insurance():
    context = build_view_context(current_view="results.overview", assessment=IT_REQUEST["assessment"], result=IT_RESULT)
    paths = {fact.source_path for fact in context.facts}
    assert not any("monte_carlo" in path or path.startswith("/uncertainty") or path.startswith("/insurance") for path in paths)
    assert not any("employees" in path.lower() or "customers" in path.lower() for path in paths)


def test_overview_uses_business_renderings_and_governed_comparisons():
    context = build_view_context(current_view="results.overview", assessment=IT_REQUEST["assessment"], result=IT_RESULT)
    probability = next(fact for fact in context.facts if fact.source_path == "/summary/prudent/p_any_event")
    assert probability.label == "P(Material Event)"
    assert probability.rendered_value == "12.76%"
    assert {fact.value for fact in context.facts if fact.label == "Governed comparison"} == {
        "VaR99 is greater than AAL.",
        "TVaR99 is greater than VaR99.",
    }


@pytest.mark.parametrize(("assessment", "result"), [(IT_REQUEST["assessment"], IT_RESULT), (OT_REQUEST["assessment"], OT_RESULT)])
def test_approved_attack_path_results_have_no_governed_state_or_barrier_facts(assessment, result):
    context = build_view_context(current_view="results.attack_paths", assessment=assessment, result=result)
    assert not any(str(fact.value).casefold() in {"open", "closed", "conditional", "unknown"} for fact in context.facts)
    assert not any(fact.source_path.startswith(("/architecture/barriers/", "/architecture/feasibility/", "/architecture/applicability/")) for fact in context.facts)


def test_treatment_context_excludes_loss_exceedance_arrays_and_is_bounded():
    context = build_view_context(current_view="results.treatment", assessment=OT_REQUEST["assessment"], result=OT_RESULT)
    assert len(context.facts) <= 300
    assert not any("/lec" in fact.source_path.lower() for fact in context.facts)


def test_evidence_context_excludes_payloads_hashes_and_descriptions():
    context = build_view_context(current_view="results.evidence", assessment=IT_REQUEST["assessment"], result=IT_RESULT)
    assert not any(any(word in fact.source_path.lower() for word in ("/hash", "/description", "/payload", "/content")) for fact in context.facts)


def test_selected_scenario_context_excludes_other_scenario_entities():
    scenarios = IT_RESULT["decomposition"]["scenarios"]
    selected = {"entity_type": "scenario", "entity_id": scenarios[0]["id"]}
    context = build_view_context(current_view="results.scenarios", assessment=IT_REQUEST["assessment"], result=IT_RESULT, selected_entity=selected)
    names = {entity["entity_id"] for entity in context.allowed_entities if entity["entity_type"] == "scenario"}
    assert names == {scenarios[0]["id"]}
    assert len([fact for fact in context.facts if fact.label == "Governed comparison"]) == 2
