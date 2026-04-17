from __future__ import annotations

from duckduckgo_search.exceptions import DuckDuckGoSearchException
from fastapilib import (
    BadRequestHTTPError,
    ForbiddenHTTPError,
    InternalHTTPError,
    NotAllowHTTPError,
    NotFoundHTTPError,
    UnauthorizedHTTPError,
)
from pydantic import ValidationError
from webparser.exceptions import WebParserError


class AppError(Exception):
    """Базовое исключение приложения."""


class ModelNotAvailableError(AppError):
    """Запрошенная LLM-модель недоступна."""


class LLMProviderError(AppError):
    """Ошибка внешнего LLM API."""


class ImageGenerationError(AppError):
    """Не удалось сгенерировать изображение."""


class FileParseError(AppError):
    """Не удалось распарсить загруженный файл."""


class MemoryNotFoundError(AppError):
    """Memory не найдена по id / user_id."""


class FileContextNotFoundError(AppError):
    """FileContext не найден по id."""


__all__ = [
    "AppError",
    "BadRequestHTTPError",
    "DuckDuckGoSearchException",
    "FileContextNotFoundError",
    "FileParseError",
    "ForbiddenHTTPError",
    "ImageGenerationError",
    "InternalHTTPError",
    "LLMProviderError",
    "MemoryNotFoundError",
    "ModelNotAvailableError",
    "NotAllowHTTPError",
    "NotFoundHTTPError",
    "UnauthorizedHTTPError",
    "ValidationError",
    "WebParserError",
]
