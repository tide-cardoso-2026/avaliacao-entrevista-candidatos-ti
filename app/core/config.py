from __future__ import annotations

import logging
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[2]


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
    LOG_LEVEL: str = "INFO"

    @property
    def active_api_key(self) -> str:
        key = self.OPENROUTER_API_KEY or self.OPENAI_API_KEY
        if not key:
            raise RuntimeError(
                "Chave nao configurada. Defina OPENROUTER_API_KEY (recomendado) ou OPENAI_API_KEY no .env"
            )
        return key

    @property
    def is_openrouter(self) -> bool:
        return bool(self.OPENROUTER_API_KEY)


settings = Settings()


def setup_logging() -> logging.Logger:
    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(name)-25s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    return logging.getLogger("entrevistataking")


logger = setup_logging()
