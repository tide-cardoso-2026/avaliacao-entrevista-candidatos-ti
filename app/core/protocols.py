"""Contrato `LLMService`: qualquer backend de LLM usado pelo pipeline deve expor `generate_json`."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


# Contrato que implementações de LLM (OpenRouter/OpenAI) devem satisfazer.
@runtime_checkable
class LLMService(Protocol):
    # Chama o modelo da camada indicada e devolve um único objeto JSON parseado.
    # `assistant_model_tier` aplica-se quando `layer` é `assistants` (ver `Settings.model_for_assistant_tier`).
    def generate_json(
        self,
        *,
        prompt: str,
        context: str,
        layer: str = "assistants",
        assistant_model_tier: str | None = None,
        system_preamble: str | None = None,
    ) -> dict:
        ...
