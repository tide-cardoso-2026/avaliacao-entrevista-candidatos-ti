"""Enriquecimento de CV com perfil LinkedIn (Proxycurl ou texto colado manualmente)."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.config import settings

log = logging.getLogger(__name__)


# Converte JSON da API Proxycurl em texto para o pipeline.
def _profile_json_to_text(data: dict[str, Any]) -> str:
    parts: list[str] = []
    if data.get("full_name"):
        parts.append(f"Nome: {data['full_name']}")
    if data.get("headline"):
        parts.append(f"Headline: {data['headline']}")
    if data.get("summary"):
        parts.append(f"Resumo:\n{data['summary']}")
    exp = data.get("experiences") or data.get("experience") or []
    if isinstance(exp, list) and exp:
        parts.append("Experiencias:")
        for e in exp[:8]:
            if isinstance(e, dict):
                title = e.get("title") or e.get("role")
                comp = e.get("company") or e.get("company_name")
                desc = e.get("description") or ""
                if title or comp:
                    parts.append(f"- {title or ''} @ {comp or ''}\n  {desc[:500]}")
    edu = data.get("education") or []
    if isinstance(edu, list) and edu:
        parts.append("Formacao:")
        for ed in edu[:5]:
            if isinstance(ed, dict):
                parts.append(f"- {ed.get('school', '')} {ed.get('degree', '')}")
    return "\n\n".join(p for p in parts if p)


# Busca perfil publico via Proxycurl (Nubela).
# Requer PROXYCURL_API_KEY no .env.
# Documentacao: https://nubela.co/proxycurl/docs
def fetch_linkedin_via_proxycurl(linkedin_profile_url: str) -> str:
    if not settings.PROXYCURL_API_KEY:
        raise RuntimeError(
            "LinkedIn automatico requer PROXYCURL_API_KEY no .env. "
            "Alternativa: use --linkedin-file no CLI com texto do perfil."
        )
    url = settings.PROXYCURL_BASE_URL.rstrip("/")
    with httpx.Client(timeout=90.0) as client:
        r = client.get(
            url,
            params={"linkedin_profile_url": linkedin_profile_url.strip()},
            headers={"Authorization": f"Bearer {settings.PROXYCURL_API_KEY}"},
        )
        r.raise_for_status()
        data = r.json()
    text = _profile_json_to_text(data)
    if not text.strip():
        log.warning("Proxycurl retornou payload vazio ou nao parseado")
        return str(data)[:8000]
    log.debug("LinkedIn Proxycurl: %d caracteres extraidos", len(text))
    return text


# Junta CV local com texto do LinkedIn (colagem e/ou Proxycurl); ordem: LinkedIn depois marcador e CV.
def enrich_candidate_cv(cv_text: str, *, linkedin_url: str | None, linkedin_paste: str | None) -> str:
    extra_parts: list[str] = []
    if linkedin_paste and linkedin_paste.strip():
        extra_parts.append("[Perfil LinkedIn (colado manualmente)]\n" + linkedin_paste.strip())
    if linkedin_url and linkedin_url.strip():
        try:
            li = fetch_linkedin_via_proxycurl(linkedin_url.strip())
            extra_parts.append("[Perfil LinkedIn (via Proxycurl)]\n" + li)
        except Exception:
            log.exception("Falha ao buscar LinkedIn; use colagem manual se necessario")
            raise
    if not extra_parts:
        return cv_text
    return "\n\n".join(extra_parts) + "\n\n---\n\n[CV / documento local]\n" + cv_text
