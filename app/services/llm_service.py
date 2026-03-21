"""Cliente LLM via OpenAI SDK (OpenRouter ou OpenAI direto): chat, JSON estruturado e retries."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass

from openai import APIConnectionError, APIStatusError, OpenAI, RateLimitError
from tenacity import before_sleep_log, retry, retry_if_exception, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.core.exceptions import LLMError, LLMResponseParsingError

log = logging.getLogger(__name__)

_JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)


# Formata inteiro para leitura (ex.: 2454 → "2.454") sem depender de locale.
def _format_int_pt(n: int) -> str:
    return f"{n:,}".replace(",", ".")


# True se a exceção for considerada transitória (retry com backoff).
def _is_transient_llm_error(exc: BaseException) -> bool:
    if isinstance(exc, (APIConnectionError, RateLimitError)):
        return True
    if isinstance(exc, APIStatusError):
        return exc.status_code >= 500 or exc.status_code == 429
    return False


# Parâmetros fixos de temperatura e teto de tokens por chamada.
@dataclass(frozen=True)
class LLMConfig:
    temperature: float = 0.2
    max_tokens: int = 4096


# Camada LLM com modelo por função (assistants / middle / cto / meta).
# Use `force_model` para CLI --model (sobrescreve todas as camadas).
class OpenAILLMService:
    # Inicializa cliente; `force_model` sobrescreve todos os `MODEL_*` por camada (ex.: CLI `--model`).
    def __init__(
        self,
        *,
        force_model: str | None = None,
        temperature: float = 0.2,
        max_tokens: int | None = None,
    ) -> None:
        self._force_model = force_model
        mt = max_tokens if max_tokens is not None else settings.MAX_TOKENS
        self.cfg = LLMConfig(temperature=temperature, max_tokens=mt)

        if settings.is_openrouter:
            self.client = OpenAI(api_key=settings.active_api_key, base_url=settings.OPENROUTER_BASE_URL)
        else:
            self.client = OpenAI(api_key=settings.active_api_key)

        log.debug(
            "LLM service: provider=%s, assistants=%s, tech_tier=%s, middle=%s, cto=%s, meta=%s",
            "openrouter" if settings.is_openrouter else "openai",
            self._resolve_model("assistants", assistant_model_tier=None),
            settings.model_for_assistant_tier("technical"),
            self._resolve_model("middle", assistant_model_tier=None),
            self._resolve_model("cto", assistant_model_tier=None),
            self._resolve_model("meta", assistant_model_tier=None),
        )

    # Escolhe o id do modelo para `assistants` | `middle` | `cto` | `meta` ou o forçado.
    def _resolve_model(self, layer: str, *, assistant_model_tier: str | None = None) -> str:
        if self._force_model:
            return self._force_model
        if layer == "assistants" and assistant_model_tier:
            return settings.model_for_assistant_tier(assistant_model_tier)
        return settings.model_for_layer(layer)

    # Envia prompt (+ contexto opcional) e devolve o primeiro objeto JSON da resposta.
    def generate_json(
        self,
        *,
        prompt: str,
        context: str,
        layer: str = "assistants",
        assistant_model_tier: str | None = None,
        system_preamble: str | None = None,
    ) -> dict:
        model = self._resolve_model(layer, assistant_model_tier=assistant_model_tier)
        log.debug(
            "LLM call layer=%s model=%s tier=%s",
            layer,
            model,
            assistant_model_tier or "-",
        )

        user_content = self._build_user_content(prompt=prompt, context=context)

        json_rule = (
            "Responda com APENAS um objeto JSON valido. Nao inclua markdown, nao inclua texto fora do JSON."
        )
        if system_preamble and system_preamble.strip():
            system_content = system_preamble.strip() + "\n\n" + json_rule
        else:
            system_content = json_rule

        try:
            resp = self._call_llm_with_retry(
                model=model,
                system_content=system_content,
                user_content=user_content,
                structured=True,
            )
        except RateLimitError as exc:
            raise LLMError(
                "Limite de requisicoes da API (429). Aguarde alguns minutos, reduza paralelismo "
                "(AGENT_ENGINE_MAX_WORKERS), troque de modelo no .env ou use BYOK no OpenRouter: "
                "https://openrouter.ai/settings/integrations — "
                f"Detalhe: {exc}"
            ) from exc
        except APIStatusError as exc:
            if exc.status_code == 429:
                raise LLMError(
                    "Limite de requisicoes da API (429). Aguarde ou ajuste modelo/creditos. "
                    f"Detalhe: {exc.message}"
                ) from exc
            if exc.status_code == 400:
                log.debug("response_format not supported, falling back to unstructured call")
                resp = self._call_llm_with_retry(
                    model=model,
                    system_content=system_content,
                    user_content=user_content,
                    structured=False,
                )
            elif exc.status_code == 402:
                raise LLMError(
                    "OpenRouter: creditos insuficientes para este modelo/tokens. "
                    "Opcoes: (1) adicionar creditos em https://openrouter.ai/settings/credits ; "
                    "(2) no .env usar o mesmo modelo em todas as camadas, ex.: "
                    "MODEL_CTO=meta-llama/llama-3-8b-instruct ; "
                    "(3) reduzir MAX_TOKENS=1024 . "
                    f"Detalhe da API: {exc.message}"
                ) from exc
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

    @retry(
        retry=retry_if_exception(_is_transient_llm_error),
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=2, max=90),
        before_sleep=before_sleep_log(log, logging.WARNING),
        reraise=True,
    )
    # Chamada com retry em falhas transitórias (rede, 429, 5xx).
    def _call_llm_with_retry(
        self,
        *,
        model: str,
        system_content: str,
        user_content: str,
        structured: bool,
        max_tokens: int | None = None,
    ) -> object:
        resp = self._call_llm(
            model=model,
            system_content=system_content,
            user_content=user_content,
            structured=structured,
            max_tokens=max_tokens,
        )
        self._log_token_usage(resp)
        return resp

    def _log_token_usage(self, resp: object) -> None:
        if not settings.LLM_LOG_TOKEN_USAGE:
            return
        usage = getattr(resp, "usage", None)
        if not usage:
            return
        pt = getattr(usage, "prompt_tokens", None)
        ct = getattr(usage, "completion_tokens", None)
        tt_raw = getattr(usage, "total_tokens", None)
        tt = tt_raw
        if tt is None and isinstance(pt, int) and isinstance(ct, int):
            tt = pt + ct

        if isinstance(tt, int):
            log.debug(
                "Tokens (~%s no total; estimativa API). Detalhe: entrada=%s saída=%s total=%s",
                _format_int_pt(tt),
                pt,
                ct,
                tt_raw,
            )
        else:
            log.debug(
                "Tokens sem estimativa da API. Detalhe: entrada=%s saída=%s total=%s",
                pt,
                ct,
                tt_raw,
            )

    # Chamada bruta à API; `structured=True` usa `response_format=json_object` quando suportado.
    def _call_llm(
        self,
        *,
        model: str,
        system_content: str,
        user_content: str,
        structured: bool,
        max_tokens: int | None = None,
    ) -> object:
        mt = max_tokens if max_tokens is not None else self.cfg.max_tokens
        kwargs: dict = {
            "model": model,
            "temperature": self.cfg.temperature,
            "max_tokens": mt,
            "messages": [
                {"role": "system", "content": system_content},
                {"role": "user", "content": user_content},
            ],
        }
        if structured:
            kwargs["response_format"] = {"type": "json_object"}
        return self.client.chat.completions.create(**kwargs)

    # Texto plano (ex.: humanização de mensagens); sem JSON estruturado.
    def generate_text(
        self,
        *,
        prompt: str,
        layer: str = "meta",
        max_tokens: int = 200,
    ) -> str:
        model = self._resolve_model(layer, assistant_model_tier=None)
        system_content = (
            "Voce reescreve mensagens tecnicas em portugues do Brasil, claras e profissionais. "
            "Responda com UMA unica linha curta, sem aspas, sem prefixo."
        )
        resp = self._call_llm_with_retry(
            model=model,
            system_content=system_content,
            user_content=prompt,
            structured=False,
            max_tokens=min(max(32, max_tokens), 512),
        )
        content = (resp.choices[0].message.content or "").strip()
        return content.split("\n")[0].strip() if content else ""

    # Delega para a camada de humanização (mapeamento + fallback LLM).
    def humanize_message(self, raw_message: str) -> str:
        from app.services import pipeline_ui_messages

        return pipeline_ui_messages.humanize_message(raw_message, llm=self)

    @staticmethod
    # Concatena prompt principal e bloco [CONTEXT] para a mensagem user.
    def _build_user_content(*, prompt: str, context: str) -> str:
        if context and context.strip():
            return f"{prompt}\n\n[CONTEXT]\n{context}"
        return prompt

    @staticmethod
    # Remove fences ```json e extrai o primeiro objeto `{...}` da string do modelo.
    def _extract_json_object(content: str) -> str:
        content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content.strip(), flags=re.IGNORECASE)
        match = _JSON_OBJECT_RE.search(content)
        if not match:
            raise LLMResponseParsingError("No JSON object found in LLM response.")
        return match.group(0)
