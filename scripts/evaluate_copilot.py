#!/usr/bin/env python3
"""Run the governed Phase 6A evaluation set against Bedrock or context-only mode."""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any

from crq.copilot.context import build_view_context
from crq.copilot.providers.bedrock import BedrockProvider
from crq.copilot.service import CopilotService


ROOT = Path(__file__).resolve().parents[1]


class RecordingProvider:
    def __init__(self, provider: BedrockProvider):
        self.provider = provider
        self.results = []

    def generate(self, **kwargs: Any) -> Any:
        result = self.provider.generate(**kwargs)
        self.results.append(result)
        return result


def pointer(value: Any, path: str) -> Any:
    for token in path.strip("/").split("/"):
        value = value[int(token)] if isinstance(value, list) else value[token]
    return value


def selected_entity(case: dict[str, Any], result: dict[str, Any]) -> dict[str, str] | None:
    path = case.get("selected_entity_from")
    if not path:
        return None
    item = pointer(result, path)
    if "scenarios" in path:
        return {"entity_type": "scenario", "entity_id": str(item["id"])}
    if "route_path_states" in path:
        return {"entity_type": "route", "entity_id": str(item["route"])} if item.get("route") else None
    return {"entity_type": "control", "entity_id": str(item.get("cid") or item.get("control_id"))}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--invoke-bedrock", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    evaluation = json.loads((ROOT / "contracts/evaluations/copilot-evaluation-set.json").read_text())
    provider = RecordingProvider(BedrockProvider(os.environ["CRQ_BEDROCK_MODEL_ID"])) if args.invoke_bedrock else None
    service = CopilotService(provider) if provider else None
    records = []
    for case in evaluation["cases"]:
        assessment = json.loads((ROOT / case["assessment_fixture"]).read_text())["assessment"]
        result = json.loads((ROOT / case["result_fixture"]).read_text())["result"]
        started = time.perf_counter()
        context = build_view_context(current_view=case["current_view"], assessment=assessment, result=result, selected_entity=selected_entity(case, result))
        context_ms = (time.perf_counter() - started) * 1000
        paths = {fact.source_path for fact in context.facts}
        required_paths_ok = set(case.get("required_source_paths", ())).issubset(paths)
        record = {"case_id": case["case_id"], "current_view": case["current_view"], "context_fact_count": len(context.facts), "context_bytes": len(json.dumps(context.to_dict(), separators=(",", ":"))), "context_generation_ms": round(context_ms, 3), "required_paths_ok": required_paths_ok, "status": "CONTEXT_ONLY"}
        if provider and service:
            provider.results = []
            query_started = time.perf_counter()
            response = service.query(current_view=case["current_view"], question=case["question"], assessment=assessment, result=result, selected_entity=selected_entity(case, result))
            record.update({"status": response["status"], "answer": response.get("answer"), "key_points": response.get("key_points", []), "caveats": response.get("caveats", []), "supporting_fact_ids": response.get("supporting_fact_ids", []), "verification_reasons": response.get("verification_reasons", []), "bedrock_calls": len(provider.results), "bedrock_latency_ms": round(sum(item.latency_ms or 0 for item in provider.results), 3), "total_response_ms": round((time.perf_counter() - query_started) * 1000, 3), "input_tokens": sum(item.input_tokens or 0 for item in provider.results), "output_tokens": sum(item.output_tokens or 0 for item in provider.results)})
        records.append(record)
    payload = {"schema_version": "1.0.0", "provider": "amazon-bedrock" if provider else None, "model_id": os.environ.get("CRQ_BEDROCK_MODEL_ID") if provider else None, "region": os.environ.get("AWS_REGION") if provider else None, "mode": "BEDROCK" if provider else "CONTEXT_ONLY", "cases": records}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n")
    return 0 if all(item["required_paths_ok"] and item["status"] != "REJECTED" for item in records) else 1


if __name__ == "__main__":
    raise SystemExit(main())
