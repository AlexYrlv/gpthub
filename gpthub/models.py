from __future__ import annotations

import typing as t

from pydantic import BaseModel, Field, field_validator, model_validator

ALLOWED_ROLES: t.Final = frozenset({"system", "user", "assistant", "tool"})


class ChatMessageData(BaseModel):
    role: str
    content: str | list | None = None
    name: str | None = None

    @field_validator("role", mode="after")
    @classmethod
    def validate_role(cls, value: str) -> str:
        if value not in ALLOWED_ROLES:
            raise ValueError(f"Недопустимая роль: {value}. Разрешённые: {sorted(ALLOWED_ROLES)}")
        return value

    @model_validator(mode="after")
    def content_required(self) -> t.Self:
        if self.content is None:
            raise ValueError("Поле content обязательно для message")
        return self


class ChatCompletionData(BaseModel):
    model: str
    messages: list[ChatMessageData]
    temperature: float | None = 0.7
    max_tokens: int | None = None
    top_p: float | None = None
    stream: bool = False
    stop: list[str] | str | None = None
    tool_choice: str | dict | None = None

    @field_validator("messages", mode="after")
    @classmethod
    def validate_messages(cls, value: list[ChatMessageData]) -> list[ChatMessageData]:
        if not value:
            raise ValueError("messages не должен быть пустым")
        return value

    @field_validator("temperature", mode="after")
    @classmethod
    def validate_temperature(cls, value: float | None) -> float | None:
        if value is not None and not (0.0 <= value <= 2.0):
            raise ValueError("temperature должен быть в диапазоне [0.0, 2.0]")
        return value

    @field_validator("top_p", mode="after")
    @classmethod
    def validate_top_p(cls, value: float | None) -> float | None:
        if value is not None and not (0.0 <= value <= 1.0):
            raise ValueError("top_p должен быть в диапазоне [0.0, 1.0]")
        return value

    @field_validator("max_tokens", mode="after")
    @classmethod
    def validate_max_tokens(cls, value: int | None) -> int | None:
        if value is not None and value <= 0:
            raise ValueError("max_tokens должен быть положительным")
        return value


class MemorizeData(BaseModel):
    request_id: str
    messages: list[dict]
    model: str
    uid: str = "default"

    @classmethod
    def from_request(cls, request) -> MemorizeData:
        import uuid

        return cls(
            request_id=uuid.uuid4().hex[:8],
            messages=[m.to_dict() for m in request.messages],
            model=request.model,
            uid=request.user_id,
        )


def pydantic_to_tool(model: type[BaseModel]) -> dict:
    return {
        "type": "function",
        "function": {
            "name": model.__name__,
            "description": (model.__doc__ or "").strip(),
            "parameters": model.model_json_schema(),
        },
    }


class WebSearch(BaseModel):
    """Поиск актуальной информации в интернете"""
    query: str = Field(description="Поисковый запрос")


class RecallMemory(BaseModel):
    """Вспомнить сохранённые факты о пользователе"""
    query: str = Field(description="Что нужно вспомнить")


class SearchFiles(BaseModel):
    """Поиск по загруженным документам пользователя (PDF, DOCX, TXT)"""
    query: str = Field(description="Поисковый запрос по содержимому файлов")


class ParseUrl(BaseModel):
    """Получить содержимое веб-страницы по URL"""
    url: str = Field(description="URL страницы")


class Slide(BaseModel):
    title: str = Field(description="Заголовок слайда")
    bullets: list[str] = Field(description="3-5 тезисов слайда")


class BuildPresentation(BaseModel):
    """Сгенерировать презентацию PowerPoint по теме пользователя"""
    title: str = Field(description="Общий заголовок презентации")
    slides: list[Slide] = Field(description="6-10 слайдов включая титульный и выводы")


class ExtractedFact(BaseModel):
    category: t.Literal["name", "job", "location", "education", "interest", "preference", "skill"]
    fact: str = Field(description="Конкретный факт одним предложением")


class SaveFacts(BaseModel):
    """Сохранить извлечённые факты о пользователе"""
    facts: list[ExtractedFact] = Field(default_factory=list)


class GenerateSubqueries(BaseModel):
    """Разбить вопрос на поисковые подзапросы для глубокого исследования"""
    queries: list[str] = Field(description="3-5 поисковых подзапросов по разным аспектам темы")


