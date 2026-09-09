"""Provider-neutral generation protocol."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class ProviderResult:
    payload: dict[str, Any]
    input_tokens: int | None = None
    output_tokens: int | None = None
    latency_ms: float | None = None


class CopilotProvider(Protocol):
    def generate(self, *, system_prompt: str, user_prompt: str, max_tokens: int, temperature: float) -> ProviderResult: ...
