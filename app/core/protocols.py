from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class LLMService(Protocol):
    """Contract that any LLM backend must satisfy."""

    def generate_json(self, *, prompt: str, context: str) -> dict: ...
