import json
from pathlib import Path

from crq.versions import (
    INPUT_SCHEMA_VERSION,
    MODEL_BUNDLE_SCHEMA_VERSION,
    NARRATIVE_FACT_SCHEMA_VERSION,
    OUTPUT_SCHEMA_VERSION,
    PLATFORM_VERSION,
)

ROOT = Path(__file__).resolve().parents[2]


def test_contract_schemas_are_parseable_and_versioned():
    expected = {
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
