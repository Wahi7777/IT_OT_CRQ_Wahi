"""Small immutable structures used at the Copilot trust boundary."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class ViewFact:
    fact_id: str
    type: str
    label: str
    value: Any
    rendered_value: str | None
    unit: str | None
    source_path: str


@dataclass(frozen=True)
class ViewContextBundle:
    context_type: str
    assessment_id: str
    run_id: str | None
    result_hash: str | None
    selected_entity: dict[str, str] | None
    facts: tuple[ViewFact, ...]
    allowed_entities: tuple[dict[str, str], ...]
    suggested_questions: tuple[str, ...]
    schema_version: str = "1.0.0"

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["facts"] = list(value["facts"])
        value["allowed_entities"] = list(value["allowed_entities"])
        value["suggested_questions"] = list(value["suggested_questions"])
        return value


@dataclass(frozen=True)
class CopilotResponse:
    context_type: str
    answer: str
    supporting_fact_ids: tuple[str, ...]
    related_entities: tuple[dict[str, str], ...] = field(default_factory=tuple)
    key_points: tuple[str, ...] = field(default_factory=tuple)
    caveats: tuple[str, ...] = field(default_factory=tuple)
    status: str = "READY"
    schema_version: str = "1.0.0"

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "CopilotResponse":
        return cls(
            context_type=str(value.get("context_type", "")),
            answer=str(value.get("answer", "")),
            supporting_fact_ids=tuple(str(item) for item in value.get("supporting_fact_ids", [])),
            related_entities=tuple(dict(item) for item in value.get("related_entities", [])),
            key_points=tuple(str(item) for item in value.get("key_points", [])),
            caveats=tuple(str(item) for item in value.get("caveats", [])),
            status=str(value.get("status", "READY")),
            schema_version=str(value.get("schema_version", "1.0.0")),
        )

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        for key in ("supporting_fact_ids", "related_entities", "key_points", "caveats"):
            value[key] = list(value[key])
        return value
