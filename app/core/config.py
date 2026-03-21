"""Configuração global (Pydantic Settings): chaves API, modelos por camada, DB e pastas de dados."""

from __future__ import annotations

import logging
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]


# Carrega variáveis de ambiente e `.env`; expõe chaves LLM, limites e caminhos padrão.
class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    OPENAI_API_KEY: str | None = None
    OPENROUTER_API_KEY: str | None = None
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    DEFAULT_MODEL: str = "meta-llama/llama-3-8b-instruct"

    # Modelos por camada (OpenRouter IDs). Por padrao todas as camadas usam o mesmo modelo barato
    # para funcionar com poucos creditos; para laudo "premium" defina MODEL_CTO no .env (ex.: Claude).
    MODEL_ASSISTANTS: str = "meta-llama/llama-3-8b-instruct"
    # Subcamadas de assistentes (AgentDefinition.assistant_model_tier). Por padrao iguais a MODEL_ASSISTANTS.
    MODEL_ASSISTANTS_TECHNICAL: str = "meta-llama/llama-3-8b-instruct"
    MODEL_ASSISTANTS_SOFT: str = "meta-llama/llama-3-8b-instruct"
    MODEL_ASSISTANTS_LEADERSHIP: str = "meta-llama/llama-3-8b-instruct"
    MODEL_ASSISTANTS_PSYCH: str = "meta-llama/llama-3-8b-instruct"
    MODEL_MIDDLE: str = "meta-llama/llama-3-8b-instruct"
    MODEL_CTO: str = "meta-llama/llama-3-8b-instruct"
    # Seleção dinâmica de agentes (meta). Pode ser um modelo maior que MODEL_ASSISTANTS para roteamento.
    MODEL_META: str = "meta-llama/llama-3-8b-instruct"

    # Paralelismo na camada de assistentes (ThreadPoolExecutor).
    AGENT_ENGINE_MAX_WORKERS: int = 8
    # Middle: deliberação só se spread > limiar ou conflitos não vazios.
    MIDDLE_DELIBERATION_SCORE_THRESHOLD: float = 1.5
    # Após 3 managers + deliberação, chama LLM consolidador pré-CTO (generic_consolidator).
    ENABLE_PRE_CTO_CONSOLIDATOR: bool = True
    # Teto de caracteres da KB injetada por assistente (arquivos grandes em `technical-questions/`).
    TECHNICAL_KB_MAX_CHARS: int = 24_000

    # Limite de tokens por resposta (menor = menos custo; ajuda em contas com poucos creditos)
    MAX_TOKENS: int = 2048

    # Log de uso de tokens por chamada (somente DEBUG; terminal da CLI mostra só Rich/`pipeline_events`).
    LLM_LOG_TOKEN_USAGE: bool = True

    LOG_LEVEL: str = "INFO"

    # API HTTP (FastAPI): se definido, exige header `X-API-Key` nas rotas protegidas.
    API_KEY: str | None = None
    # Limite global de requisições por minuto por IP (slowapi).
    API_RATE_LIMIT_PER_MINUTE: int = 60

    # Humanização de mensagens de UI: se True, mensagens sem mapeamento usam LLM (custo extra).
    HUMANIZE_UI_WITH_LLM: bool = False

    # Banco de histórico (SQLite)
    DATABASE_URL: str = Field(default_factory=lambda: f"sqlite:///{(BASE_DIR / 'data' / 'history.db').as_posix()}")

    # LinkedIn (opcional) — Proxycurl / Nubela API
    PROXYCURL_API_KEY: str | None = None
    PROXYCURL_BASE_URL: str = "https://nubela.co/proxycurl/api/v2/linkedin"

    # Base de perguntas técnicas (`data/technical-questions/*.md`) — ver `technical_questions_format`
    TECHNICAL_QUESTIONS_DIR: Path = Field(default_factory=lambda: BASE_DIR / "data" / "technical-questions")

    # Scorecard de alta precisão: exige lista de evidencias e justificativa minima por evidencia.
    SCORECARD_REQUIRE_EVIDENCE: bool = True
    MIN_EVIDENCE_JUSTIFICATION_CHARS: int = 20
    GOLDEN_DATASET_PATH: Path = Field(
        default_factory=lambda: BASE_DIR / "data" / "golden_dataset" / "golden_answers.json"
    )

    @property
    # Retorna a chave usada pelo cliente OpenAI (OpenRouter ou OpenAI direto).
    def active_api_key(self) -> str:
        key = self.OPENROUTER_API_KEY or self.OPENAI_API_KEY
        if not key:
            raise RuntimeError(
                "Chave nao configurada. Defina OPENROUTER_API_KEY (recomendado) ou OPENAI_API_KEY no .env"
            )
        return key

    @property
    # True se `OPENROUTER_API_KEY` estiver definida (base URL do OpenRouter).
    def is_openrouter(self) -> bool:
        return bool(self.OPENROUTER_API_KEY)

    # Resolve o modelo por camada: assistants | middle | cto | meta.
    def model_for_layer(self, layer: str) -> str:
        m = {
            "assistants": self.MODEL_ASSISTANTS,
            "middle": self.MODEL_MIDDLE,
            "cto": self.MODEL_CTO,
            "meta": self.MODEL_META,
        }.get(layer, self.DEFAULT_MODEL)
        return m or self.DEFAULT_MODEL

    # Resolve modelo por tier de assistente (ver `AssistantModelTier` em schemas).
    def model_for_assistant_tier(self, tier: str) -> str:
        mapping = {
            "default": self.MODEL_ASSISTANTS,
            "technical": self.MODEL_ASSISTANTS_TECHNICAL,
            "soft": self.MODEL_ASSISTANTS_SOFT,
            "leadership": self.MODEL_ASSISTANTS_LEADERSHIP,
            "psych": self.MODEL_ASSISTANTS_PSYCH,
        }
        return mapping.get(tier, self.MODEL_ASSISTANTS) or self.DEFAULT_MODEL


settings = Settings()


# Configura `logging` global. Em INFO, o terminal da CLI fica só com saída Rich do pipeline
# (`  • …` / `    …`); mensagens técnicas de etapas LLM ficam em DEBUG.
def setup_logging() -> logging.Logger:
    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(name)-25s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    # Evita linhas técnicas no terminal (HTTP, retries do cliente OpenAI SDK, etc.).
    for name in ("httpx", "httpcore", "urllib3", "openai"):
        logging.getLogger(name).setLevel(logging.WARNING)
    return logging.getLogger("entrevistataking")


logger = setup_logging()
