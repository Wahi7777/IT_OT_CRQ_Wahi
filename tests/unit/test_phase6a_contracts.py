from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

from crq.copilot.context import build_view_context


ROOT = Path(__file__).resolve().parents[2]


def test_view_context_bundle_matches_governed_schema():
    schema = json.loads((ROOT / "contracts/schemas/view-context-bundle.schema.json").read_text())
    assessment = json.loads((ROOT / "contracts/examples/assessment-run-request-it-fs.json").read_text())["assessment"]
    result = json.loads((ROOT / "contracts/examples/assessment-run-response-it-fs.json").read_text())["result"]
    bundle = build_view_context(current_view="results.overview", assessment=assessment, result=result)
    Draft202012Validator(schema).validate(bundle.to_dict())


def test_copilot_response_example_shape_matches_schema():
    schema = json.loads((ROOT / "contracts/schemas/copilot-response.schema.json").read_text())
    value = {"schema_version": "1.0.0", "context_type": "results.overview", "answer": "Supported answer.", "key_points": [], "caveats": [], "supporting_fact_ids": ["vf_0123456789abcdef"], "related_entities": [], "status": "READY"}
    Draft202012Validator(schema).validate(value)


def test_governed_evaluation_set_references_existing_approved_examples():
    evaluation = json.loads((ROOT / "contracts/evaluations/copilot-evaluation-set.json").read_text())
    assert len(evaluation["cases"]) >= 12
    for case in evaluation["cases"]:
        assert (ROOT / case["assessment_fixture"]).is_file()
        assert (ROOT / case["result_fixture"]).is_file()
