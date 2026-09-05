import json
from pathlib import Path

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from crq.versions import (
    APPLICATION_REQUEST_SCHEMA_VERSION,
    APPLICATION_RESPONSE_SCHEMA_VERSION,
    INPUT_SCHEMA_VERSION,
    MODEL_BUNDLE_SCHEMA_VERSION,
    NARRATIVE_FACT_SCHEMA_VERSION,
    OUTPUT_SCHEMA_VERSION,
    PLATFORM_VERSION,
)

ROOT = Path(__file__).resolve().parents[2]


def test_contract_schemas_are_parseable_and_versioned():
    expected = {
        "assessment-run-request.schema.json": APPLICATION_REQUEST_SCHEMA_VERSION,
        "assessment-run-response.schema.json": APPLICATION_RESPONSE_SCHEMA_VERSION,
        "crq-assessment.schema.json": INPUT_SCHEMA_VERSION,
        "model-bundle.schema.json": MODEL_BUNDLE_SCHEMA_VERSION,
        "crq-result.schema.json": OUTPUT_SCHEMA_VERSION,
        "narrative-fact-bundle.schema.json": NARRATIVE_FACT_SCHEMA_VERSION,
    }
    for name, version in expected.items():
        data = json.loads((ROOT / "contracts" / "schemas" / name).read_text())
        assert data["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert data["properties"]["schema_version"]["const"] == version


def test_field_inventory_uses_one_ownership_classification_per_entry():
    data = json.loads((ROOT / "contracts" / "mappings" / "field-inventory.json").read_text())
    allowed = set(data["classification_enum"])
    assert len(data["fields"]) >= 40
    for entry in data["fields"]:
        assert entry["classification"] in allowed
        assert entry["canonical_path"]
        assert entry["consumer"]
        assert entry["location"]


def test_machine_readable_mappings_are_parseable():
    mapping_dir = ROOT / "contracts" / "mappings"
    for name in ("engine-output-to-crq-result.json", "model-bundle-source-map.json", "excel-adapter-source-map.json"):
        data = json.loads((mapping_dir / name).read_text())
        assert data["schema_version"] == "1.0.0-draft"


def test_narrative_example_has_source_pointer_for_every_numeric_fact():
    data = json.loads((ROOT / "contracts" / "examples" / "narrative-fact-bundle.example.json").read_text())
    for section in data["facts"].values():
        for fact in section:
            if fact["kind"] == "numeric":
                assert fact["source_pointer"].startswith("/")
                assert any(x["source_pointer"] == fact["source_pointer"] for x in data["numeric_allowlist"])


def test_platform_version_matches_package_metadata():
    pyproject = (ROOT / "pyproject.toml").read_text()
    assert f'version = "{PLATFORM_VERSION}"' in pyproject


def test_application_examples_conform_to_runtime_contracts():
    from crq.application.service import AssessmentRunRequest, validate_response_payload

    example_dir = ROOT / "contracts" / "examples"
    schema_dir = ROOT / "contracts" / "schemas"
    request_schema = json.loads((schema_dir / "assessment-run-request.schema.json").read_text())
    response_schema = json.loads((schema_dir / "assessment-run-response.schema.json").read_text())
    assessment_schema = json.loads((schema_dir / "crq-assessment.schema.json").read_text())
    result_schema = json.loads((schema_dir / "crq-result.schema.json").read_text())
    registry = Registry().with_resources(
        (schema["$id"], Resource.from_contents(schema)) for schema in (assessment_schema, result_schema)
    )
    request_validator = Draft202012Validator(request_schema, registry=registry)
    response_validator = Draft202012Validator(response_schema, registry=registry)
    for case_id in ("it-fs", "ot-pg"):
        request = json.loads((example_dir / f"assessment-run-request-{case_id}.json").read_text())
        response = json.loads((example_dir / f"assessment-run-response-{case_id}.json").read_text())
        AssessmentRunRequest.from_dict(request)
        validate_response_payload(response)
        request_validator.validate(request)
        response_validator.validate(response)
        assert response["status"] == "SUCCESS"
        assert response["request_id"] == request["request_id"]
        assert "output" not in response["result"]["compatibility"]["legacy_engine_extension"]
        assert "/Users/" not in json.dumps(response)


def test_approved_bundle_registry_is_explicit_and_unique():
    registry = json.loads((ROOT / "config" / "approved_model_bundles.json").read_text())
    expected = {"FS-v1.1.1", "PG-v1.6", "EA-v1.0", "MF-v1.0"}
    ids = [row["bundle_id"] for row in registry["bundles"]]
    assert set(ids) == expected
    assert len(ids) == len(set(ids))
    for row in registry["bundles"]:
        assert row["status"] == "APPROVED"
        assert len(row["pack_hash"]) == 64
