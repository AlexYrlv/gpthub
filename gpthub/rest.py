from __future__ import annotations

from config_fastapi import Config
from frpclnt import AsyncRestClient

from .baseclasses import BaseAPI
from .constants import (
    CACHE_TTL_EMBEDDING,
    CACHE_TTL_MODELS,
    REST_DEFAULT_HEADERS,
    REST_DEFAULT_TIMEOUT,
    REST_ENDPOINTS_LLM,
)
from .models import pydantic_to_tool
from .structures import AudioUpload, ChatRequest, ChatResponse, GeneratedImage, ModelList, TranscriptionResult
from .utils import acached


class LLMProviderAPI(BaseAPI):
    config = Config(section="api.llm")
    routes = REST_ENDPOINTS_LLM

    @property
    def client(self) -> AsyncRestClient:
        return AsyncRestClient(
            address=self.config.url,
            endpoints=self.routes.to_routes(),
            headers={
                **REST_DEFAULT_HEADERS,
                "Authorization": f"Bearer {self.config.key}",
            },
            timeout=self.config.get("timeout", REST_DEFAULT_TIMEOUT),
        )

    async def chat_completions(self, request: ChatRequest) -> ChatResponse:
        self.logger.info("Chat completion: model=%s", request.model)
        response = await self.client(
            "post",
            self.routes.CHAT_COMPLETIONS.name,
            json=request.to_dict(),
        )
        return ChatResponse.create(response)

    async def chat_completions_with_tools(self, request: ChatRequest, tools: tuple) -> ChatResponse:
        data = request.to_dict()
        data["tools"] = [pydantic_to_tool(t) for t in tools]
        data["tool_choice"] = "auto"
        response = await self.client(
            "post",
            self.routes.CHAT_COMPLETIONS.name,
            json=data,
        )
        return ChatResponse.create(response)

    async def chat_completions_stream(self, request: ChatRequest):
        data = request.to_dict()
        data["stream"] = True
        async for chunk in self.client.stream(
            "post",
            self.routes.CHAT_COMPLETIONS.name,
            json=data,
        ):
            yield chunk

    @acached(ttl=CACHE_TTL_MODELS)
    async def get_models(self) -> ModelList:
        response = await self.client("get", self.routes.MODELS.name)
        return ModelList.create(response)

    async def is_available(self) -> bool:
        try:
            return bool((await self.get_models()).data)
        except Exception:
            return False

    @acached(ttl=CACHE_TTL_EMBEDDING)
    async def get_embeddings(self, text: str, model: str = "bge-m3") -> list[float]:
        response = await self.client(
            "post",
            self.routes.EMBEDDINGS.name,
            json={"model": model, "input": text},
        )
        return response["data"][0]["embedding"]

    async def transcribe_audio(self, upload: AudioUpload, model: str) -> TranscriptionResult:
        response = await self.client(
            "post",
            self.routes.AUDIO_TRANSCRIPTIONS.name,
            data={"model": model},
            files=[("file", (upload.filename, upload.data, upload.content_type))],
        )
        return TranscriptionResult.create({**response, "model": model})

    async def generate_image(self, request: ChatRequest) -> GeneratedImage:
        self.logger.info("Image generation: model=%s", request.model)
        response = await self.client(
            "post",
            self.routes.IMAGES_GENERATIONS.name,
            json={"model": request.model, "prompt": request.last_text, "n": 1, "size": "1024x1024"},
        )
        return GeneratedImage.create(response.get("data", [{}])[0])
