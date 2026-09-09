from __future__ import annotations

import json

from crq.copilot.providers.bedrock import BedrockProvider


class Client:
    def __init__(self, *, tool_response=False):
        self.request = None
        self.tool_response = tool_response

    def converse(self, **kwargs):
        self.request = kwargs
        payload = {"schema_version": "1.0.0", "context_type": "results.overview", "answer": "Answer", "key_points": [], "caveats": [], "supporting_fact_ids": ["vf_1"], "related_entities": [], "status": "READY"}
        if self.tool_response:
            return {"output": {"message": {"content": [{"toolUse": {"name": "return_crq_response", "toolUseId": "test", "input": payload}}]}}, "usage": {"inputTokens": 42, "outputTokens": 12}}
        return {"output": {"message": {"content": [{"text": json.dumps(payload)}]}}, "usage": {"inputTokens": 42, "outputTokens": 12}}


def test_bedrock_converse_enforces_structured_json_and_returns_usage():
    client = Client()
    result = BedrockProvider("anthropic.claude-test-v1:0", client=client).generate(system_prompt="system", user_prompt="user", max_tokens=700, temperature=0)
    output = client.request["outputConfig"]["textFormat"]
    assert output["type"] == "json_schema"
    assert json.loads(output["structure"]["jsonSchema"]["schema"])["additionalProperties"] is False
    assert result.input_tokens == 42
    assert result.output_tokens == 12


def test_nova_uses_prompt_contract_without_unsupported_output_config():
    client = Client(tool_response=True)
    result = BedrockProvider("amazon.nova-lite-v1:0", client=client).generate(system_prompt="system", user_prompt="user", max_tokens=700, temperature=0)
    assert "outputConfig" not in client.request
    assert client.request["toolConfig"]["toolChoice"]["tool"]["name"] == "return_crq_response"
    assert result.payload["status"] == "READY"
