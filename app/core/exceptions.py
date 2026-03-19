from __future__ import annotations


class EntrevistaTakingError(Exception):
    """Base exception for the application."""


class LLMError(EntrevistaTakingError):
    """Raised when an LLM call fails after all retries."""


class LLMResponseParsingError(LLMError):
    """Raised when the LLM response cannot be parsed as valid JSON."""


class DocumentNotFoundError(EntrevistaTakingError):
    """Raised when a required document cannot be located."""


class AmbiguousDocumentError(EntrevistaTakingError):
    """Raised when multiple documents match a single stem fragment."""


class UnsupportedFormatError(EntrevistaTakingError):
    """Raised when a document has an unsupported file format."""
