from __future__ import annotations

import typing as t

from pydantic import BaseModel, field_validator, model_validator

from .utils import new_short_id

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
        return cls(
            request_id=new_short_id(),
            messages=[m.to_dict() for m in request.messages],
            model=request.model,
            uid=request.user_id,
        )
