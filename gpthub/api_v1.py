from __future__ import annotations

from logging import getLogger

from fastabc import Api, App
from fastapi import Request
from fastapi.responses import JSONResponse as Response
from fastapilib import abort, json, sse

from .baseclasses import BaseResource
from .controls import AudioControl, ChatControl, FileControl, GPTHubControl, HealthControl
from .exceptions import (
    BadRequestHTTPError,
    DuckDuckGoSearchException,
    FileContextNotFoundError,
    FileParseError,
    ImageGenerationError,
    LLMProviderError,
    MemoryNotFoundError,
    ModelNotAvailableError,
    NotFoundHTTPError,
    ValidationError,
    WebParserError,
)
from .models import ChatCompletionData, MemorizeData
from .rpc import MemorizeRPC
from .structures import AudioUpload, ChatRequest, FileUpload, FileUploadResult

API_PREFIX = "v1"
LOGGER = getLogger(f"api.{API_PREFIX}")


def init(app: App) -> Api:
    api = Api(f"api-{API_PREFIX}", url_prefix=f"/{API_PREFIX}")

    api.new_routes({
        "/chat/completions": ChatCompletionsResource,
        "/models": ModelsResource,
        "/audio/transcriptions": AudioTranscriptionsResource,
        "/files": FilesResource,
        "/health": HealthResource,
    })

    return api.init_app(app)


class HealthResource(BaseResource):
    logger = LOGGER

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.health = HealthControl()

    async def get(self, _: Request) -> Response:
        return json((await self.health.status()).to_dict())


class ChatCompletionsResource(BaseResource):
    logger = LOGGER

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.control = GPTHubControl()
        self.rpc = MemorizeRPC()

    async def post(self, request: Request) -> Response:
        if not isinstance(data := await request.json(), dict):
            raise BadRequestHTTPError("Invalid request data")

        chat_request = ChatRequest.from_data(ChatCompletionData(**data)).set_user_id(
            request.headers.get("x-openwebui-user-id"),
        )
        await self.rpc.send(MemorizeData.from_request(chat_request))

        if chat_request.stream:
            return sse(self.control.process_chat_stream(chat_request))

        return json((await self.control.process_chat(chat_request)).to_dict())


class ModelsResource(BaseResource):
    logger = LOGGER

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.chat = ChatControl()

    async def get(self, _: Request) -> Response:
        return json((await self.chat.list_models()).to_dict())


class AudioTranscriptionsResource(BaseResource):
    logger = LOGGER

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.audio = AudioControl()

    async def post(self, request: Request) -> Response:
        form = await request.form()
        if (file := form.get("file")) is None:
            raise BadRequestHTTPError("file is required")

        return json((await self.audio.transcribe(
            await AudioUpload.from_form(file, form.get("model")),
        )).to_dict())


class FilesResource(BaseResource):
    logger = LOGGER

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.files = FileControl()

    async def post(self, request: Request) -> Response:
        form = await request.form()
        if (file := form.get("file")) is None:
            raise BadRequestHTTPError("file is required")

        return json(FileUploadResult.from_context(
            await self.files.ingest(
                await FileUpload.from_form(file, request.headers.get("x-openwebui-user-id")),
            ),
        ).to_dict(), 201)


def error_response(request: Request, exception: BaseException):
    LOGGER.getChild("abort").info("Abort: %s %s", type(exception).__name__, exception)

    match exception:
        case ValidationError():
            return abort(
                exception=BadRequestHTTPError(f"Неверные данные в запросе (ошибок: {exception.error_count()})"),
                description="\n".join([err["msg"] for err in exception.errors()]),
            )
        case ModelNotAvailableError():
            return abort(BadRequestHTTPError(str(exception)))
        case MemoryNotFoundError():
            return abort(NotFoundHTTPError("Memory not found"))
        case FileContextNotFoundError():
            return abort(NotFoundHTTPError("File not found"))
        case FileParseError():
            return abort(BadRequestHTTPError(f"Cannot parse file: {exception}"))
        case ImageGenerationError():
            return abort(BadRequestHTTPError(str(exception)))
        case LLMProviderError():
            return abort(BadRequestHTTPError(f"LLM provider error: {exception}"))
        case WebParserError():
            return abort(BadRequestHTTPError(f"Web parsing error: {exception}"))
        case DuckDuckGoSearchException():
            return abort(BadRequestHTTPError(f"Search error: {exception}"))

    return abort(exception)
