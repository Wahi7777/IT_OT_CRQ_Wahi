"""Amazon Bedrock Converse adapter; no CRQ application logic lives here."""

from __future__ import annotations

import json
import time
from typing import Any

from crq.copilot.providers.base import ProviderResult


_RESPONSE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["schema_version", "context_type", "answer", "key_points", "caveats", "supporting_fact_ids", "related_entities", "status"],
    "properties": {
        "schema_version": {"type": "string", "const": "1.0.0"},
        "context_type": {"type": "string"},
        "answer": {"type": "string"},
        "key_points": {"type": "array", "items": {"type": "string"}},
        "caveats": {"type": "array", "items": {"type": "string"}},
        "supporting_fact_ids": {"type": "array", "items": {"type": "string"}},
        "related_entities": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["entity_type", "entity_id"],
                "properties": {"entity_type": {"type": "string"}, "entity_id": {"type": "string"}},
            },
        },
        "status": {"type": "string", "enum": ["READY", "REJECTED"]},
    },
}


class BedrockProvider:
    def __init__(self, model_id: str, client: Any | None = None):
        if not model_id:
            raise ValueError("Bedrock model_id is required")
        if client is None:
            import boto3

            client = boto3.client("bedrock-runtime")
        self.model_id = model_id
        self.client = client

    def generate(self, *, system_prompt: str, user_prompt: str, max_tokens: int, temperature: float) -> ProviderResult:
        started = time.perf_counter()
        request = dict(
            modelId=self.model_id,
            system=[{"text": system_prompt}],
            messages=[{"role": "user", "content": [{"text": user_prompt}]}],
            inferenceConfig={"maxTokens": max_tokens, "temperature": temperature},
        )
        # Claude 4.5 supports Bedrock's native constrained decoding. Amazon Nova
        # uses the same structured contract in the prompt and is still checked
        # by the deterministic schema/fact verifier before anything is shown.
        if "anthropic.claude" in self.model_id:
            request["outputConfig"] = {
                "textFormat": {
                    "type": "json_schema",
                    "structure": {
                        "jsonSchema": {
                            "schema": json.dumps(_RESPONSE_SCHEMA, sort_keys=True, separators=(",", ":")),
                            "name": "crq_copilot_response",
                            "description": "A fact-cited CRQ Copilot response",
                        }
                    },
                }
            }
        else:
            request["toolConfig"] = {
                "tools": [
                    {
                        "toolSpec": {
                            "name": "return_crq_response",
                            "description": "Return the CRQ response candidate for deterministic verification.",
                            "inputSchema": {"json": _RESPONSE_SCHEMA},
                        }
                    }
                ],
                "toolChoice": {"tool": {"name": "return_crq_response"}},
            }
        try:
            response = self.client.converse(**request)
        except Exception as exc:
            model_error = getattr(getattr(self.client, "exceptions", None), "ModelErrorException", None)
            if model_error is not None and isinstance(exc, model_error):
                raise ValueError("Bedrock returned a malformed structured response") from exc
            raise
        content = response["output"]["message"]["content"]
        if "anthropic.claude" in self.model_id:
            value = json.loads(content[0]["text"])
        else:
            tool_uses = [item["toolUse"] for item in content if "toolUse" in item and item["toolUse"].get("name") == "return_crq_response"]
            if len(tool_uses) != 1:
                raise ValueError("Bedrock response must contain one CRQ response tool call")
            value = tool_uses[0]["input"]
        if not isinstance(value, dict):
            raise ValueError("Bedrock response must be a JSON object")
        usage = response.get("usage") or {}
        return ProviderResult(
            value,
            input_tokens=usage.get("inputTokens"),
            output_tokens=usage.get("outputTokens"),
            latency_ms=(time.perf_counter() - started) * 1000,
        )
