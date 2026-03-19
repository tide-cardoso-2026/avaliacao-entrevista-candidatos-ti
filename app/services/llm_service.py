from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass

from openai import OpenAI, APIConnectionError, RateLimitError, APIStatusError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, before_sleep_log

from app.core.config import settings
from app.core.exceptions import LLMError, LLMResponseParsingError

log = logging.getLogger(__name__)

_JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)


@dataclass(frozen=True)
class LLMConfig:
    model: str
    temperature: float = 0.2
    max_tokens: int = 2048


class OpenAILLMService:
    def __init__(self, model: str | None = None, *, temperature: float = 0.2, max_tokens: int = 2048) -> None:
        self.cfg = LLMConfig(
            model=model or settings.DEFAULT_MODEL,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        if settings.is_openrouter:
            self.client = OpenAI(api_key=settings.active_api_key, base_url=settings.OPENROUTER_BASE_URL)
        else:
            self.client = OpenAI(api_key=settings.active_api_key)

        log.info("LLM service initialized: model=%s, provider=%s", self.cfg.model, "openrouter" if settings.is_openrouter else "openai")

    @retry(
        retry=retry_if_exception_type((APIConnectionError, RateLimitError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        before_sleep=before_sleep_log(log, logging.WARNING),
        reraise=True,
    )
    def generate_json(self, *, prompt: str, context: str) -> dict:
        user_content = self._build_user_content(prompt=prompt, context=context)

        system_content = (
            "Responda com APENAS um objeto JSON valido. "
            "Nao inclua markdown, nao inclua texto fora do JSON."
        )

        try:
            resp = self._call_llm(system_content=system_content, user_content=user_content, structured=True)
        except APIStatusError as exc:
            if exc.status_code == 400:
                log.debug("response_format not supported, falling back to unstructured call")
                resp = self._call_llm(system_content=system_content, user_content=user_content, structured=False)
            else:
                raise LLMError(f"LLM API error (HTTP {exc.status_code}): {exc.message}") from exc

        content = (resp.choices[0].message.content or "").strip()
        if not content:
            raise LLMResponseParsingError("LLM returned empty content")

        json_str = self._extract_json_object(content)
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as exc:
            raise LLMResponseParsingError(
                f"Failed to parse LLM JSON: {exc}. Content (trimmed): {content[:300]}"
            ) from exc

    def _call_llm(self, *, system_content: str, user_content: str, structured: bool) -> object:
        kwargs: dict = {
            "model": self.cfg.model,
            "temperature": self.cfg.temperature,
            "max_tokens": self.cfg.max_tokens,
            "messages": [
                {"role": "system", "content": system_content},
                {"role": "user", "content": user_content},
            ],
        }
        if structured:
            kwargs["response_format"] = {"type": "json_object"}
        return self.client.chat.completions.create(**kwargs)

    @staticmethod
    def _build_user_content(*, prompt: str, context: str) -> str:
        if context and context.strip():
            return f"{prompt}\n\n[CONTEXT]\n{context}"
        return prompt

    @staticmethod
    def _extract_json_object(content: str) -> str:
        content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content.strip(), flags=re.IGNORECASE)
        match = _JSON_OBJECT_RE.search(content)
        if not match:
            raise LLMResponseParsingError("No JSON object found in LLM response.")
        return match.group(0)
