import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _load(relative_path):
    return json.loads((ROOT / relative_path).read_text())


def test_every_grouped_input_resolves_to_one_canonical_frontend_location():
    inventory = _load("contracts/mappings/field-inventory.json")
    placement = _load("contracts/frontend/frontend-placement.json")
    placed = [path for screen in placement["input_screens"] for path in screen["canonical_paths"]]
    expected = {field["canonical_path"] for field in inventory["fields"]}
    assert set(placed) == expected
    for field in inventory["fields"]:
        domain = field["domain"]
        applicable_domain = {"IT", "OT"} if domain == "common" else {domain}
        screens = {
            screen["screen_id"]
            for screen in placement["input_screens"]
            if field["canonical_path"] in screen["canonical_paths"]
            and applicable_domain.intersection(screen["applies_to"])
        }
        assert len(screens) == 1, (field["canonical_path"], domain, screens)


def test_frontend_rendering_never_makes_governed_or_inactive_fields_editable():
    inventory = _load("contracts/mappings/field-inventory.json")
    rendering = _load("contracts/frontend/frontend-placement.json")["rendering_by_classification"]
    assert rendering["GOVERNED_PACK_INPUT"]["editable"] is False
    assert rendering["DERIVED"]["editable"] is False
    assert rendering["DISPLAY_ONLY"]["editable"] is False
    assert rendering["INACTIVE_LEGACY"]["editable"] is False
    for field in inventory["fields"]:
        if field["classification"] in {"GOVERNED_PACK_INPUT", "DERIVED", "DISPLAY_ONLY", "INACTIVE_LEGACY"}:
            assert field["frontend"]["editable"] is False


def test_every_result_mapping_has_a_results_screen():
    output_mapping = _load("contracts/mappings/engine-output-to-crq-result.json")["mappings"]
    screens = _load("contracts/frontend/frontend-placement.json")["results_screens"]
    for row in output_mapping:
        matches = [screen["screen_id"] for screen in screens if any(row["canonical_path"].startswith(prefix) for prefix in screen["prefixes"])]
        assert matches, row["canonical_path"]


def test_numerical_equivalence_is_default_exact_and_exceptions_are_narrow():
    policy = _load("contracts/policies/numerical-equivalence-policy.json")
    assert policy["exact_rules"]["default_numeric_rule"] == "exact"
    assert policy["failure_governance"]["baseline_update"] == "PROHIBITED_BY_THIS_POLICY"
    assert policy["failure_governance"]["automatic_blessing"] is False
    assert {rule["id"] for rule in policy["platform_sensitive_exceptions"]} == {
        "IT_LIBM_ANNUAL_EVENT_PROBABILITY",
        "OT_EMPIRICAL_LEC_SINGLE_ORDINATE",
    }
    assert policy["platform_sensitive_exceptions"][0]["comparison"]["absolute_tolerance"] <= 1.2e-16
    assert policy["platform_sensitive_exceptions"][1]["comparison"]["absolute_tolerance"] <= 4.0e-9


def test_async_api_has_only_minimum_routes_and_immediate_sqs_dispatch():
    api = _load("contracts/api/async-run-api.openapi.json")
    assert set(api["paths"]) == {
        "/v1/assessments/run",
        "/v1/runs/{run_id}",
        "/v1/runs/{run_id}/result",
    }
    assert set(api["components"]["schemas"]["RunState"]["enum"]) == {"QUEUED", "RUNNING", "COMPLETED", "FAILED"}
    design = api["x-crq-execution-design"]
    assert design["sqs"] == {"batch_size": 1, "maximum_batching_window_seconds": 0}
    assert design["s3_keys"] == [
        "assessments/{assessment_id}/input.json",
        "runs/{run_id}/status.json",
        "runs/{run_id}/result.json",
    ]
    assert set(design["excluded"]) == {"RDS", "STEP_FUNCTIONS", "FARGATE"}
