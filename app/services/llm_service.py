from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass

from openai import OpenAI


_JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)


@dataclass(frozen=True)
class LLMConfig:
    model: str
    temperature: float = 0.2
    max_tokens: int = 1500


class OpenAILLMService:
    """
    Chamada ao LLM com garantia pratica de JSON valido.
    """

    def __init__(self, model: str, *, temperature: float = 0.2, max_tokens: int = 1500) -> None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "OPENAI_API_KEY nao configurada. Crie um arquivo .env ou exporte a variavel de ambiente."
            )
        self.client = OpenAI(api_key=api_key)
        self.cfg = LLMConfig(model=model, temperature=temperature, max_tokens=max_tokens)

    def generate_json(self, *, prompt: str, context: str) -> dict:
        user_content = self._build_user_content(prompt=prompt, context=context)

        system_content = (
            "Responda com APENAS um objeto JSON valido. "
            "Nao inclua markdown, nao inclua texto fora do JSON."
        )

        # Alguns modelos suportam response_format, mas nao e garantido. Mantem fallback.
        try:
            resp = self.client.chat.completions.create(
                model=self.cfg.model,
                temperature=self.cfg.temperature,
                max_tokens=self.cfg.max_tokens,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_content},
                    {"role": "user", "content": user_content},
                ],
            )
        except Exception:
            resp = self.client.chat.completions.create(
                model=self.cfg.model,
                temperature=self.cfg.temperature,
                max_tokens=self.cfg.max_tokens,
                messages=[
                    {"role": "system", "content": system_content},
                    {"role": "user", "content": user_content},
                ],
            )

        content = (resp.choices[0].message.content or "").strip()
        json_str = self._extract_json_object(content)
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"Falha ao parsear JSON do LLM: {e}. Conteudo (trim): {content[:300]}") from e

    @staticmethod
    def _build_user_content(*, prompt: str, context: str) -> str:
        if context and context.strip():
            return f"{prompt}\n\n[CONTEXT]\n{context}"
        return prompt

    @staticmethod
    def _extract_json_object(content: str) -> str:
        # Remove fences ```json ... ```
        content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content.strip(), flags=re.IGNORECASE)
        match = _JSON_OBJECT_RE.search(content)
        if not match:
            raise ValueError("Nenhum objeto JSON encontrado na resposta do LLM.")
        return match.group(0)

