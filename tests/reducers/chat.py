from __future__ import annotations

from dataclasses import replace

from gpthub.structures import ChatRequest, Message


def change_request_temperature(request: ChatRequest, temperature: float) -> ChatRequest:
    return replace(request, temperature=temperature)


def change_request_stream(request: ChatRequest, stream: bool) -> ChatRequest:
    return replace(request, stream=stream)


def change_request_user_id(request: ChatRequest, user_id: str) -> ChatRequest:
    return replace(request, user_id=user_id)


def change_message_role(message: Message, role: str) -> Message:
    return replace(message, role=role)


def change_message_content(message: Message, content: str | list[dict]) -> Message:
    return replace(message, content=content)
