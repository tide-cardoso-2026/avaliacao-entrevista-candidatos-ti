"""Hierarquia de exceções do domínio (LLM, documentos, formatos)."""

from __future__ import annotations


# Base exception for the application.
class EntrevistaTakingError(Exception):
    pass


# Raised when an LLM call fails after all retries.
class LLMError(EntrevistaTakingError):
    pass


# Raised when the LLM response cannot be parsed as valid JSON.
class LLMResponseParsingError(LLMError):
    pass


# Raised when a required document cannot be located.
class DocumentNotFoundError(EntrevistaTakingError):
    pass


# Raised when multiple documents match a single stem fragment.
class AmbiguousDocumentError(EntrevistaTakingError):
    pass


# Raised when a document has an unsupported file format.
class UnsupportedFormatError(EntrevistaTakingError):
    pass


# Evidencia obrigatoria ausente ou justificativa curta demais (avaliacao rejeitada).
class EvidenceValidationError(EntrevistaTakingError):
    pass
