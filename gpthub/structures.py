from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, replace
from dataclasses import field as f
from datetime import datetime

from .constants import (
    EXTENSION,
    MODEL_ROUTING,
    MODEL_TYPE,
    PRESENTATION_KEYWORDS,
    RESEARCH_KEYWORDS,
    SINGLE_PURPOSE_MODEL_TYPES,
    TOOL_NAME,
)
from .models import ChatCompletionData, ChatMessageData
from .mongodb import FileContextModel, MemoryModel


@dataclass
class Message:
    role: str = f(default="")
    content: str | list = f(default="")
    name: str | None = f(default=None)
    tool_calls: list[ToolCall] | None = f(default=None)
    tool_call_id: str | None = f(default=None)

    @classmethod
    def create(cls, data: dict) -> Message:
        result = cls()
        if data.get("role") is not None:
            result = replace(result, role=data["role"])
        if data.get("content") is not None:
            result = replace(result, content=data["content"])
        if data.get("name") is not None:
            result = replace(result, name=data["name"])
        if data.get("tool_calls") is not None:
            result = replace(result, tool_calls=[ToolCall.create(tc) for tc in data["tool_calls"]])
        if data.get("tool_call_id") is not None:
            result = replace(result, tool_call_id=data["tool_call_id"])
        return result

    @classmethod
    def from_data(cls, data: ChatMessageData) -> Message:
        result = cls(role=data.role)
        if data.content is not None:
            result = replace(result, content=data.content)
        if data.name is not None:
            result = replace(result, name=data.name)
        return result

    def set_content(self, content: str | list) -> Message:
        if content == self.content:
            return self
        return replace(self, content=content)

    @property
    def has_image(self) -> bool:
        if isinstance(self.content, list):
            return any(
                item.get("type") == "image_url"
                for item in self.content
                if isinstance(item, dict)
            )
        return False

    @property
    def text(self) -> str:
        if isinstance(self.content, str):
            return self.content
        if isinstance(self.content, list):
            return " ".join(
                item.get("text", "")
                for item in self.content
                if isinstance(item, dict) and item.get("type") == "text"
            )
        return ""

    @property
    def image_urls(self) -> list[str]:
        if not isinstance(self.content, list):
            return []
        return [
            item.get("image_url", {}).get("url", "")
            for item in self.content
            if isinstance(item, dict) and item.get("type") == "image_url"
        ]

    @property
    def fetchable_image_urls(self) -> list[str]:
        return [url for url in self.image_urls if not url.startswith("data:")]

    def with_resolved_images(self, url_map: dict) -> Message:
        if not isinstance(self.content, list):
            return self
        parts = []
        for item in self.content:
            if isinstance(item, dict) and item.get("type") == "image_url":
                url = item.get("image_url", {}).get("url", "")
                parts.append({"type": "image_url", "image_url": {"url": url_map.get(url, url)}})
            elif isinstance(item, dict):
                parts.append(item)
        return self.set_content(parts)

    def to_dict(self) -> dict:
        result = {"role": self.role, "content": self.content}
        if self.name is not None:
            result["name"] = self.name
        if self.tool_calls is not None:
            result["tool_calls"] = [tc.to_dict() for tc in self.tool_calls]
        if self.tool_call_id is not None:
            result["tool_call_id"] = self.tool_call_id
        return result


@dataclass
class ChatRequest:
    messages: list[Message] = f(default_factory=list)
    model: str = f(default="")
    temperature: float | None = f(default=0.7)
    max_tokens: int | None = f(default=None)
    top_p: float | None = f(default=None)
    stream: bool = f(default=False)
    user_id: str = f(default="default")
    stop: list[str] | str | None = f(default=None)
    tool_choice: str | dict | None = f(default=None)

    @classmethod
    def create(cls, data: dict) -> ChatRequest:
        result = cls()
        if data.get("messages") is not None:
            result = replace(result, messages=[Message.create(m) for m in data["messages"]])
        if data.get("model") is not None:
            result = replace(result, model=data["model"])
        if data.get("temperature") is not None:
            result = replace(result, temperature=data["temperature"])
        if data.get("max_tokens") is not None:
            result = replace(result, max_tokens=data["max_tokens"])
        if data.get("top_p") is not None:
            result = replace(result, top_p=data["top_p"])
        if data.get("stream") is not None:
            result = replace(result, stream=data["stream"])
        if data.get("stop") is not None:
            result = replace(result, stop=data["stop"])
        return result

    @classmethod
    def from_data(cls, data: ChatCompletionData) -> ChatRequest:
        result = cls(
            model=data.model,
            messages=[Message.from_data(m) for m in data.messages],
            stream=data.stream,
        )
        if data.temperature is not None:
            result = replace(result, temperature=data.temperature)
        if data.max_tokens is not None:
            result = replace(result, max_tokens=data.max_tokens)
        if data.top_p is not None:
            result = replace(result, top_p=data.top_p)
        if data.stop is not None:
            result = replace(result, stop=data.stop)
        if data.tool_choice is not None:
            result = replace(result, tool_choice=data.tool_choice)
        return result

    def set_model(self, model: str) -> ChatRequest:
        if model == self.model:
            return self
        return replace(self, model=model)

    def set_messages(self, messages: list[Message]) -> ChatRequest:
        if messages == self.messages:
            return self
        return replace(self, messages=messages)

    def set_user_id(self, user_id: str | None) -> ChatRequest:
        if not user_id or user_id == self.user_id:
            return self
        return replace(self, user_id=user_id)

    @property
    def last_message(self) -> Message | None:
        return self.messages[-1] if self.messages else None

    @property
    def is_manual(self) -> bool:
        return bool(self.model) and self.model != "auto"

    @property
    def has_image(self) -> bool:
        return self.last_message.has_image if self.last_message else False

    @property
    def tools_disabled(self) -> bool:
        return self.tool_choice == "none"

    @property
    def needs_research(self) -> bool:
        return any(kw in self.last_text.lower() for kw in RESEARCH_KEYWORDS)

    @property
    def needs_presentation(self) -> bool:
        return any(kw in self.last_text.lower() for kw in PRESENTATION_KEYWORDS)

    def with_context(self, context: str) -> ChatRequest:
        if not context:
            return self
        messages = list(self.messages)
        if messages and messages[0].role == "system":
            messages[0] = messages[0].set_content(messages[0].text + context)
        else:
            messages.insert(0, Message(role="system", content=context))
        return self.set_messages(messages)

    def with_tool_results(self, assistant_msg: Message, results: list[Message]) -> ChatRequest:
        messages = list(self.messages)
        messages.append(assistant_msg)
        messages.extend(results)
        return self.set_messages(messages)

    @property
    def last_text(self) -> str:
        return self.last_message.text if self.last_message else ""

    def to_dict(self) -> dict:
        result = {
            "model": self.model,
            "messages": [m.to_dict() for m in self.messages],
            "stream": self.stream,
        }
        if self.temperature is not None:
            result["temperature"] = self.temperature
        if self.max_tokens is not None:
            result["max_tokens"] = self.max_tokens
        if self.top_p is not None:
            result["top_p"] = self.top_p
        if self.stop is not None:
            result["stop"] = self.stop
        return result


@dataclass
class ChatChoice:
    index: int = f(default=0)
    message: Message = f(default_factory=Message)
    finish_reason: str = f(default="stop")

    @classmethod
    def create(cls, data: dict) -> ChatChoice:
        result = cls()
        if data.get("index") is not None:
            result = replace(result, index=data["index"])
        if data.get("message") is not None:
            result = replace(result, message=Message.create(data["message"]))
        if data.get("finish_reason") is not None:
            result = replace(result, finish_reason=data["finish_reason"])
        return result

    def to_dict(self) -> dict:
        return {
            "index": self.index,
            "message": self.message.to_dict(),
            "finish_reason": self.finish_reason,
        }


@dataclass
class ChatResponse:
    id: str = f(default="")
    model: str = f(default="")
    choices: list[ChatChoice] = f(default_factory=list)
    created: int = f(default=0)
    object: str = f(default="chat.completion")
    usage: dict = f(default_factory=dict)

    @classmethod
    def create(cls, data: dict) -> ChatResponse:
        result = cls()
        if data.get("id") is not None:
            result = replace(result, id=data["id"])
        if data.get("model") is not None:
            result = replace(result, model=data["model"])
        if data.get("choices") is not None:
            result = replace(result, choices=[ChatChoice.create(c) for c in data["choices"]])
        if data.get("created") is not None:
            result = replace(result, created=data["created"])
        if data.get("object") is not None:
            result = replace(result, object=data["object"])
        if data.get("usage") is not None:
            result = replace(result, usage=data["usage"])
        return result

    @classmethod
    def from_error(cls, msg: str) -> ChatResponse:
        return cls(
            id="error",
            choices=[ChatChoice(message=Message(role="assistant", content=msg))],
        )

    @classmethod
    def from_text(cls, content: str, model: str) -> ChatResponse:
        return cls(
            model=model,
            choices=[ChatChoice(message=Message(role="assistant", content=content))],
        )

    @classmethod
    def from_image(cls, image: GeneratedImage, model: str, prompt: str) -> ChatResponse:
        src = image.url or f"data:image/png;base64,{image.b64_json}"
        return cls(
            id=f"imggen-{uuid.uuid4().hex[:8]}",
            model=model,
            choices=[ChatChoice(message=Message(
                role="assistant",
                content=f"![generated]({src})\n\n*{image.revised_prompt or prompt}*",
            ))],
        )

    @property
    def content(self) -> str:
        if self.choices:
            return self.choices[0].message.text
        return ""

    @property
    def has_tool_calls(self) -> bool:
        if not self.choices:
            return False
        return bool(self.choices[0].message.tool_calls)

    @property
    def tool_calls(self) -> list[ToolCall]:
        if not self.choices:
            return []
        return self.choices[0].message.tool_calls or []

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "object": self.object,
            "created": self.created,
            "model": self.model,
            "choices": [c.to_dict() for c in self.choices],
            "usage": self.usage,
        }


@dataclass
class RoutingResult:
    model: str = f(default="")
    model_type: MODEL_TYPE = f(default=MODEL_TYPE.TEXT)
    auto_routed: bool = f(default=False)

    @classmethod
    def manual(cls, model: str, model_type: MODEL_TYPE = MODEL_TYPE.TEXT) -> RoutingResult:
        return cls(model=model, model_type=model_type, auto_routed=False)

    @classmethod
    def auto(cls, model_type: MODEL_TYPE, model: str | None = None) -> RoutingResult:
        return cls(
            model=model or MODEL_ROUTING[model_type].value,
            model_type=model_type,
            auto_routed=True,
        )

    @classmethod
    def create(cls, data: dict) -> RoutingResult:
        result = cls()
        if data.get("model") is not None:
            result = replace(result, model=data["model"])
        if data.get("model_type") is not None:
            result = replace(result, model_type=data["model_type"])
        if data.get("auto_routed") is not None:
            result = replace(result, auto_routed=data["auto_routed"])
        return result

    @property
    def is_single_purpose(self) -> bool:
        return self.model_type in SINGLE_PURPOSE_MODEL_TYPES

    def to_dict(self) -> dict:
        return {
            "model": self.model,
            "model_type": self.model_type.value,
            "auto_routed": self.auto_routed,
        }


@dataclass
class Memory:
    model: MemoryModel | None = f(default=None)
    user_id: str = f(default="")
    fact: str = f(default="")
    source: str = f(default="chat")
    embedding: list[float] = f(default_factory=list)
    created_at: datetime = f(default_factory=datetime.now)

    @classmethod
    def create(cls, data: dict) -> Memory:
        result = cls()
        if data.get("user_id") is not None:
            result = replace(result, user_id=data["user_id"])
        if data.get("fact") is not None:
            result = replace(result, fact=data["fact"])
        if data.get("source") is not None:
            result = replace(result, source=data["source"])
        if data.get("embedding") is not None:
            result = replace(result, embedding=list(data["embedding"]))
        return result

    @classmethod
    def from_mongo(cls, model: MemoryModel) -> Memory:
        return cls(
            model=model,
            user_id=model.user_id,
            fact=model.fact,
            source=model.source,
            embedding=list(model.embedding or []),
            created_at=model.created_at,
        )

    def set_fact(self, fact: str) -> Memory:
        if fact == self.fact:
            return self
        return replace(self, fact=fact)

    def set_embedding(self, embedding: list[float]) -> Memory:
        return replace(self, embedding=embedding)

    def to_dict(self) -> dict:
        return {
            "id": self.oid,
            "user_id": self.user_id,
            "fact": self.fact,
            "source": self.source,
            "created_at": self.created_at.isoformat(),
        }

    def to_mongo(self) -> MemoryModel:
        return MemoryModel(
            user_id=self.user_id,
            fact=self.fact,
            source=self.source,
            embedding=self.embedding,
        )

    @property
    def oid(self) -> str | None:
        return str(self.model.pk) if self.model else None

    async def save(self) -> Memory:
        model = await self.to_mongo().save()
        return replace(self, model=model)


@dataclass
class FileContext:
    model: FileContextModel | None = f(default=None)
    user_id: str = f(default="default")
    filename: str = f(default="")
    content_type: str = f(default="")
    chunks: list[str] = f(default_factory=list)
    embeddings: list[list[float]] = f(default_factory=list)
    created_at: datetime = f(default_factory=datetime.now)

    @classmethod
    def create(cls, data: dict) -> FileContext:
        result = cls()
        if data.get("user_id") is not None:
            result = replace(result, user_id=data["user_id"])
        if data.get("filename") is not None:
            result = replace(result, filename=data["filename"])
        if data.get("content_type") is not None:
            result = replace(result, content_type=data["content_type"])
        if data.get("chunks") is not None:
            result = replace(result, chunks=list(data["chunks"]))
        if data.get("embeddings") is not None:
            result = replace(result, embeddings=[list(e) for e in data["embeddings"]])
        return result

    @classmethod
    def from_mongo(cls, model: FileContextModel) -> FileContext:
        return cls(
            model=model,
            user_id=model.user_id,
            filename=model.filename,
            content_type=model.content_type or "",
            chunks=list(model.chunks or []),
            embeddings=[list(e) for e in (model.embeddings or [])],
            created_at=model.created_at,
        )

    def set_chunks(self, chunks: list[str]) -> FileContext:
        return replace(self, chunks=chunks)

    def set_embeddings(self, embeddings: list[list[float]]) -> FileContext:
        return replace(self, embeddings=embeddings)

    def to_dict(self) -> dict:
        return {
            "id": self.oid,
            "filename": self.filename,
            "content_type": self.content_type,
            "chunks": self.chunks,
            "embeddings": self.embeddings,
            "created_at": self.created_at.isoformat(),
        }

    def to_mongo(self) -> FileContextModel:
        return FileContextModel(
            user_id=self.user_id,
            filename=self.filename,
            content_type=self.content_type,
            chunks=self.chunks,
            embeddings=self.embeddings,
        )

    @property
    def oid(self) -> str | None:
        return str(self.model.pk) if self.model else None

    async def save(self) -> FileContext:
        model = await self.to_mongo().save()
        return replace(self, model=model)


@dataclass
class ToolCall:
    id: str = f(default="")
    name: str = f(default="")
    arguments: str = f(default="{}")

    @classmethod
    def create(cls, data: dict) -> ToolCall:
        result = cls()
        if data.get("id") is not None:
            result = replace(result, id=data["id"])
        if data.get("function") is not None:
            if data["function"].get("name") is not None:
                result = replace(result, name=data["function"]["name"])
            if data["function"].get("arguments") is not None:
                result = replace(result, arguments=data["function"]["arguments"])
        return result

    @property
    def tool_name(self) -> TOOL_NAME:
        return TOOL_NAME.get(self.name)

    @property
    def parsed_arguments(self) -> dict:
        return json.loads(self.arguments)

    @property
    def trace_summary(self) -> str:
        args = self.parsed_arguments
        return args.get("query") or args.get("url") or self.name

    def parse_as(self, model: type):
        return model.model_validate_json(self.arguments)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": "function",
            "function": {"name": self.name, "arguments": self.arguments},
        }


@dataclass
class File:
    name: str = f(default="")
    content: bytes = f(default=b"", repr=False)
    extension: EXTENSION = f(default=EXTENSION.PPTX)
    url: str = f(default="")

    @classmethod
    def create(cls, data: dict) -> File:
        return cls(
            name=data["name"],
            content=data["content"],
            extension=EXTENSION(data["extension"]) if isinstance(data["extension"], str) else data["extension"],
        )

    def set_url(self, url: str) -> File:
        return replace(self, url=url)

    @property
    def with_extension(self) -> str:
        return f"{self.name}.{self.extension.value}"


@dataclass
class GeneratedImage:
    url: str = f(default="")
    b64_json: str = f(default="")
    revised_prompt: str = f(default="")

    @property
    def is_empty(self) -> bool:
        return not self.url and not self.b64_json

    @classmethod
    def create(cls, data: dict) -> GeneratedImage:
        result = cls()
        if data.get("url") is not None:
            result = replace(result, url=data["url"])
        if data.get("b64_json") is not None:
            result = replace(result, b64_json=data["b64_json"])
        if data.get("revised_prompt") is not None:
            result = replace(result, revised_prompt=data["revised_prompt"])
        return result

    def to_dict(self) -> dict:
        return {
            "url": self.url,
            "b64_json": self.b64_json,
            "revised_prompt": self.revised_prompt,
        }


@dataclass
class HealthStatus:
    llm_available: bool = f(default=False)
    models_count: int = f(default=0)

    @classmethod
    def ok(cls, models_count: int) -> HealthStatus:
        return cls(llm_available=True, models_count=models_count)

    @classmethod
    def degraded(cls) -> HealthStatus:
        return cls(llm_available=False, models_count=0)

    def to_dict(self) -> dict:
        return {
            "status": "ok" if self.llm_available else "degraded",
            "llm": self.llm_available,
            "models_available": self.models_count,
        }


@dataclass
class TraceEvent:
    text: str = f(default="")
    model: str = f(default="auto")

    @classmethod
    def research_start(cls, model: str) -> TraceEvent:
        return cls(text="🔍 Deep Research запущен", model=model)

    @classmethod
    def subquery(cls, index: int, query: str, model: str) -> TraceEvent:
        return cls(text=f"   → Подзапрос {index}: {query}", model=model)

    @classmethod
    def research_done(cls, pages: int, model: str) -> TraceEvent:
        return cls(text=f"✅ Обработано {pages} источников", model=model)

    @classmethod
    def route(cls, routing: RoutingResult, model: str) -> TraceEvent:
        return cls(text=f"🧠 Маршрут: {routing.model_type.value} → {routing.model}", model=model)

    @classmethod
    def tool_call(cls, call: ToolCall, model: str) -> TraceEvent:
        return cls(text=f"🔧 {call.tool_name.value}: {call.trace_summary}", model=model)

    @classmethod
    def tools_done(cls, count: int, model: str) -> TraceEvent:
        return cls(text=f"✅ Выполнено инструментов: {count}", model=model)

    def to_dict(self) -> dict:
        return {
            "id": f"chatcmpl-trace-{uuid.uuid4().hex[:8]}",
            "object": "chat.completion.chunk",
            "created": int(datetime.now().timestamp()),
            "model": self.model,
            "choices": [{
                "index": 0,
                "delta": {"role": "assistant", "content": f"> {self.text}\n"},
                "finish_reason": None,
            }],
        }


@dataclass
class WebPage:
    url: str = f(default="")
    title: str = f(default="")
    text: str = f(default="")
    content: bytes = f(default=b"")
    content_type: str = f(default="")
    fetched_at: datetime = f(default_factory=datetime.now)

    @classmethod
    def create(cls, data: dict) -> WebPage:
        result = cls()
        if data.get("url") is not None:
            result = replace(result, url=data["url"])
        if data.get("title") is not None:
            result = replace(result, title=data["title"])
        if data.get("text") is not None:
            result = replace(result, text=data["text"])
        if data.get("content") is not None:
            result = replace(result, content=data["content"])
        if data.get("content_type") is not None:
            result = replace(result, content_type=data["content_type"])
        return result

    def set_text(self, text: str) -> WebPage:
        return replace(self, text=text)

    def set_content(self, content: bytes, content_type: str = "") -> WebPage:
        return replace(self, content=content, content_type=content_type)

    def to_dict(self) -> dict:
        return {
            "url": self.url,
            "title": self.title,
            "text": self.text,
            "fetched_at": self.fetched_at.isoformat(),
        }


@dataclass
class ModelInfo:
    id: str = f(default="")
    object: str = f(default="model")
    created: int = f(default=1677610602)
    owned_by: str = f(default="gpthub")

    @classmethod
    def create(cls, data: dict) -> ModelInfo:
        result = cls()
        if data.get("id") is not None:
            result = replace(result, id=data["id"])
        if data.get("object") is not None:
            result = replace(result, object=data["object"])
        if data.get("created") is not None:
            result = replace(result, created=data["created"])
        if data.get("owned_by") is not None:
            result = replace(result, owned_by=data["owned_by"])
        return result

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "object": self.object,
            "created": self.created,
            "owned_by": self.owned_by,
        }


@dataclass
class ModelList:
    object: str = f(default="list")
    data: list[ModelInfo] = f(default_factory=list)

    @classmethod
    def create(cls, data: dict) -> ModelList:
        result = cls()
        if data.get("object") is not None:
            result = replace(result, object=data["object"])
        if data.get("data") is not None:
            result = replace(result, data=[ModelInfo.create(m) for m in data["data"]])
        return result

    def with_auto(self) -> ModelList:
        return replace(self, data=[ModelInfo(id="auto", owned_by="gpthub"), *self.data])

    @property
    def ids(self) -> set[str]:
        return {m.id for m in self.data}

    def to_dict(self) -> dict:
        return {
            "object": self.object,
            "data": [m.to_dict() for m in self.data],
        }


@dataclass
class AudioUpload:
    data: bytes = f(default=b"")
    filename: str = f(default="audio.wav")
    content_type: str = f(default="audio/wav")
    model: str | None = f(default=None)

    @classmethod
    async def from_form(cls, file, model: str | None = None) -> AudioUpload:
        return cls(
            data=await file.read(),
            filename=file.filename or "audio.wav",
            content_type=file.content_type or "audio/wav",
            model=model,
        )

    @classmethod
    def create(cls, data: dict) -> AudioUpload:
        result = cls()
        if data.get("data") is not None:
            result = replace(result, data=data["data"])
        if data.get("filename") is not None:
            result = replace(result, filename=data["filename"])
        if data.get("content_type") is not None:
            result = replace(result, content_type=data["content_type"])
        if data.get("model") is not None:
            result = replace(result, model=data["model"])
        return result


@dataclass
class FileUpload:
    data: bytes = f(default=b"")
    filename: str = f(default="")
    content_type: str = f(default="")
    user_id: str = f(default="default")

    @classmethod
    async def from_form(cls, file, user_id: str | None = None) -> FileUpload:
        result = cls(
            data=await file.read(),
            filename=file.filename or "",
            content_type=file.content_type or "",
        )
        if user_id:
            result = replace(result, user_id=user_id)
        return result

    @classmethod
    def create(cls, data: dict) -> FileUpload:
        result = cls()
        if data.get("data") is not None:
            result = replace(result, data=data["data"])
        if data.get("filename") is not None:
            result = replace(result, filename=data["filename"])
        if data.get("content_type") is not None:
            result = replace(result, content_type=data["content_type"])
        return result


@dataclass
class TranscriptionResult:
    text: str = f(default="")
    model: str = f(default="")

    @classmethod
    def create(cls, data: dict) -> TranscriptionResult:
        result = cls()
        if data.get("text") is not None:
            result = replace(result, text=data["text"])
        if data.get("model") is not None:
            result = replace(result, model=data["model"])
        return result

    def to_dict(self) -> dict:
        return {"text": self.text}


@dataclass
class FileUploadResult:
    id: str = f(default="")
    filename: str = f(default="")
    chunks: int = f(default=0)
    status: str = f(default="processed")

    @classmethod
    def from_context(cls, ctx: FileContext) -> FileUploadResult:
        return cls(
            id=ctx.oid or "",
            filename=ctx.filename,
            chunks=len(ctx.chunks),
            status="processed",
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "filename": self.filename,
            "chunks": self.chunks,
            "status": self.status,
        }
