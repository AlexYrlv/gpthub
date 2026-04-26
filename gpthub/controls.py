from __future__ import annotations

from asyncio import gather

from .baseclasses import BaseControl
from .clients import PPTXClient, S3Client, WebParserClient, WebSearchClient
from .constants import (
    DEFAULT_USER_ID,
    EXTENSION,
    EXTRACT_DIALOGUE_LIMIT,
    EXTRACT_MAX_TOKENS,
    EXTRACT_TEMPERATURE,
    IMAGE_GEN_MODELS,
    KEYWORD_ROUTING,
    MEMORY_DEDUP_THRESHOLD,
    MEMORY_TOP_K,
    MODEL_FALLBACK,
    MODEL_ROUTING,
    MODEL_TYPE,
    RAG_CHUNK_OVERLAP,
    RAG_CHUNK_SIZE,
    RAG_TOP_K,
    RESEARCH_MAX_SUBQUERIES,
    RESEARCH_RESULTS_PER_QUERY,
    TOOL_NAME,
    VISION_MODELS,
)
from .exceptions import ImageGenerationError
from .mongodb import find_files_by_user, find_memories_by_user
from .prompts import EXTRACT_FACTS, PRESENTATION_CONTEXT, RESEARCH_SUBQUERY
from .rest import LLMProviderAPI
from .tools import (
    BuildPresentation,
    ExtractedFact,
    GenerateSubqueries,
    ParseUrl,
    RecallMemory,
    SaveFacts,
    SearchFiles,
    WebSearch,
)
from .structures import (
    AudioUpload,
    ChatRequest,
    ChatResponse,
    File,
    FileContext,
    FileUpload,
    HealthStatus,
    Memory,
    Message,
    ModelList,
    RoutingResult,
    ToolCall,
    TraceEvent,
    TranscriptionResult,
)
from .utils import (
    build_dialogue,
    build_file_context,
    build_file_link,
    build_memory_context,
    build_research_context,
    build_web_context,
    chunk_text,
    extract_text_from_file,
    is_duplicate_memory,
    new_short_id,
    score_chunks,
    score_memories,
    serialize,
    to_data_url,
)


class MemoryControl(BaseControl):

    def __init__(self):
        self.llm = LLMProviderAPI()
        self.chat = ChatControl()

    async def recall(self, query: str, uid: str = DEFAULT_USER_ID) -> list[Memory]:
        return score_memories(
            await self.llm.get_embeddings(query),
            [Memory.from_mongo(m) for m in await find_memories_by_user(uid)],
            MEMORY_TOP_K,
        )

    async def memorize(self, request: ChatRequest, uid: str = DEFAULT_USER_ID) -> list[Memory]:
        existing = [Memory.from_mongo(m) for m in await find_memories_by_user(uid)]
        saved = []
        for extracted in await self.extract_facts(build_dialogue(request)):
            if not (emb := await self.llm.get_embeddings(extracted.fact)):
                continue
            if is_duplicate_memory(emb, existing, MEMORY_DEDUP_THRESHOLD):
                continue
            memory = await Memory.create({
                "user_id": uid,
                "fact": extracted.fact,
                "source": extracted.category,
            }).set_embedding(emb).save()
            saved.append(memory)
            existing.append(memory)

        self.logger.debug("Memorized %s facts", len(saved))
        return saved

    async def extract_facts(self, dialogue: str) -> list[ExtractedFact]:
        response = await self.llm.chat_completions_with_tools(
            ChatRequest.create({
                "model": await self.chat.pick_available(MODEL_TYPE.TOOL_CALL),
                "messages": [{"role": "user", "content": EXTRACT_FACTS.format(
                    dialogue=dialogue[:EXTRACT_DIALOGUE_LIMIT],
                )}],
                "temperature": EXTRACT_TEMPERATURE,
                "max_tokens": EXTRACT_MAX_TOKENS,
            }),
            (SaveFacts,),
        )
        if not response.has_tool_calls:
            return []
        return response.tool_calls[0].parse_as(SaveFacts).facts


class FileControl(BaseControl):

    def __init__(self):
        self.llm = LLMProviderAPI()

    async def ingest(self, upload: FileUpload) -> FileContext:
        if not (text := extract_text_from_file(upload.data, upload.filename, upload.content_type)):
            self.logger.warning("Empty file: %s", upload.filename)
            return FileContext.create({
                "user_id": upload.user_id,
                "filename": upload.filename,
                "content_type": upload.content_type,
            })

        chunks = chunk_text(text, RAG_CHUNK_SIZE, RAG_CHUNK_OVERLAP)
        self.logger.debug("Ingesting file: %s (%d chunks)", upload.filename, len(chunks))

        embeddings = await gather(*[self.llm.get_embeddings(chunk) for chunk in chunks])

        return await FileContext.create({
            "user_id": upload.user_id,
            "filename": upload.filename,
            "content_type": upload.content_type,
            "chunks": chunks,
            "embeddings": embeddings,
        }).save()

    async def search(self, query: str, uid: str = DEFAULT_USER_ID, top_k: int = RAG_TOP_K) -> list[str]:
        files = [FileContext.from_mongo(m) for m in await find_files_by_user(uid)]
        return score_chunks(await self.llm.get_embeddings(query), files, top_k)


class HealthControl(BaseControl):

    def __init__(self):
        self.llm = LLMProviderAPI()

    async def status(self) -> HealthStatus:
        if (models := await self.llm.safe_get_models()) is None or not models.data:
            return HealthStatus.degraded()
        return HealthStatus.ok(len(models.data))


class AudioControl(BaseControl):

    def __init__(self):
        self.llm = LLMProviderAPI()
        self.chat = ChatControl()

    async def transcribe(self, upload: AudioUpload) -> TranscriptionResult:
        model = upload.model or await self.chat.pick_available(MODEL_TYPE.ASR)
        return await self.llm.transcribe_audio(upload, model)


class PresentationControl(BaseControl):

    def __init__(self):
        self.pptx = PPTXClient()
        self.s3 = S3Client()

    async def generate(self, title: str, slides: list) -> File:
        return await self.s3.upload(File.create({
            "name": f"presentation-{new_short_id()}",
            "content": await self.pptx.build(title, slides),
            "extension": EXTENSION.PPTX,
        }))


class ChatControl(BaseControl):

    def __init__(self):
        self.llm = LLMProviderAPI()
        self.parser = WebParserClient()

    async def pick_available(self, model_type: MODEL_TYPE) -> str:
        ids = (await self.llm.get_models()).ids
        for candidate in MODEL_FALLBACK[model_type]:
            if candidate.value in ids:
                return candidate.value
        return MODEL_ROUTING[model_type].value

    async def resolve(self, request: ChatRequest) -> RoutingResult:
        if request.is_manual:
            if request.model in VISION_MODELS:
                return RoutingResult.manual(request.model, MODEL_TYPE.VISION)
            if request.model in IMAGE_GEN_MODELS:
                return RoutingResult.manual(request.model, MODEL_TYPE.IMAGE_GEN)
            return RoutingResult.manual(request.model)

        model_type = self.classify(request)
        model = await self.pick_available(model_type)
        self.logger.debug("Auto-route: %s → %s", model_type.value, model)
        return RoutingResult.auto(model_type, model)

    @staticmethod
    def classify(request: ChatRequest) -> MODEL_TYPE:
        if request.has_image:
            return MODEL_TYPE.VISION
        text = request.last_text.lower()
        for model_type, keywords in KEYWORD_ROUTING.items():
            if any(kw in text for kw in keywords):
                return model_type
        return MODEL_TYPE.TEXT

    async def chat(self, request: ChatRequest) -> ChatResponse:
        routing = await self.resolve(request)
        request = request.set_model(routing.model)

        match routing.model_type:
            case MODEL_TYPE.IMAGE_GEN:
                return await self.image_gen(request)
            case MODEL_TYPE.VISION:
                return await self.llm.chat_completions(await self.prepare_vision(request))

        if request.needs_presentation:
            request = request.with_context(PRESENTATION_CONTEXT)

        return await self.llm.chat_completions(request)

    async def chat_stream(self, request: ChatRequest):
        routing = await self.resolve(request)
        request = request.set_model(routing.model)

        if routing.model_type is MODEL_TYPE.IMAGE_GEN:
            yield serialize((await self.image_gen(request)).to_dict())
            return

        if routing.model_type is MODEL_TYPE.VISION:
            request = await self.prepare_vision(request)
        if request.needs_presentation:
            request = request.with_context(PRESENTATION_CONTEXT)

        async for chunk in self.llm.chat_completions_stream(request):
            yield chunk

    async def chat_with_tools(self, request: ChatRequest) -> ChatResponse:
        return await self.llm.chat_completions_with_tools(
            request.set_model(await self.pick_available(MODEL_TYPE.TOOL_CALL)),
            (WebSearch, RecallMemory, SearchFiles, ParseUrl, BuildPresentation),
        )

    async def list_models(self) -> ModelList:
        return (await self.llm.get_models()).with_auto()

    async def image_gen(self, request: ChatRequest) -> ChatResponse:
        if (image := await self.llm.generate_image(request)).is_empty:
            raise ImageGenerationError("Image generation returned empty result")
        return ChatResponse.from_image(image, request.model, request.last_text)

    async def prepare_vision(self, request: ChatRequest) -> ChatRequest:
        resolved = []
        for msg in request.messages:
            if not msg.has_image:
                resolved.append(msg)
                continue
            resolved.append(await self.resolve_images(msg))
        return request.set_messages(resolved)

    async def resolve_images(self, msg: Message) -> Message:
        for url in msg.fetchable_image_urls:
            page = await self.parser.fetch_bytes(url)
            msg = msg.with_resolved_images({url: to_data_url(page)})
        return msg


class GPTHubControl(BaseControl):

    def __init__(self):
        self.llm = LLMProviderAPI()
        self.chat = ChatControl()
        self.memory = MemoryControl()
        self.parser = WebParserClient()
        self.search = WebSearchClient()
        self.files = FileControl()
        self.presentation = PresentationControl()

    async def process_chat(self, request: ChatRequest) -> ChatResponse:
        if request.needs_research and not request.tools_disabled:
            request = await self.enrich_with_research(request)

        routing = await self.chat.resolve(request)
        if request.tools_disabled or (not request.needs_presentation and routing.is_single_purpose):
            return await self.chat.chat(request)

        if (response := await self.chat.chat_with_tools(request)).has_tool_calls:
            return await self.llm.chat_completions(request.with_tool_results(
                response.choices[0].message,
                await self.execute_tools(response.tool_calls, request.user_id),
            ).set_model(await self.chat.pick_available(MODEL_TYPE.TOOL_CALL)))

        return response

    async def process_chat_stream(self, request: ChatRequest):
        if request.needs_research and not request.tools_disabled:
            yield serialize(TraceEvent.research_start(request.model).to_dict())
            subqueries = await self.plan_research(request.last_text)
            for i, q in enumerate(subqueries, 1):
                yield serialize(TraceEvent.subquery(i, q, request.model).to_dict())
            pages = await self.fetch_research(subqueries)
            yield serialize(TraceEvent.research_done(len(pages), request.model).to_dict())
            request = request.with_context(build_research_context(subqueries, pages))

        routing = await self.chat.resolve(request)
        yield serialize(TraceEvent.route(routing, request.model).to_dict())

        if request.tools_disabled or (not request.needs_presentation and routing.is_single_purpose):
            async for chunk in self.chat.chat_stream(request):
                yield chunk
            return

        if (response := await self.chat.chat_with_tools(request)).has_tool_calls:
            for call in response.tool_calls:
                yield serialize(TraceEvent.tool_call(call, request.model).to_dict())
            tool_results = await self.execute_tools(response.tool_calls, request.user_id)
            yield serialize(TraceEvent.tools_done(len(tool_results), request.model).to_dict())
            request = request.with_tool_results(
                response.choices[0].message, tool_results,
            ).set_model(await self.chat.pick_available(MODEL_TYPE.TOOL_CALL))
            async for chunk in self.chat.chat_stream(request):
                yield chunk
            return

        yield serialize(response.to_dict())

    async def enrich_with_research(self, request: ChatRequest) -> ChatRequest:
        subqueries = await self.plan_research(request.last_text)
        self.logger.info("Deep research: %d subqueries", len(subqueries))
        pages = await self.fetch_research(subqueries)
        return request.with_context(build_research_context(subqueries, pages))

    async def plan_research(self, last_text: str) -> list[str]:
        return (await self.research_subqueries(last_text))[:RESEARCH_MAX_SUBQUERIES]

    async def fetch_research(self, subqueries: list[str]) -> list:
        results = await gather(*[
            self.search.search(q, max_results=RESEARCH_RESULTS_PER_QUERY) for q in subqueries
        ])
        return [page for batch in results for page in batch]

    async def research_subqueries(self, query: str) -> list[str]:
        response = await self.llm.chat_completions_with_tools(
            ChatRequest.create({
                "model": await self.chat.pick_available(MODEL_TYPE.TOOL_CALL),
                "messages": [{"role": "user", "content": RESEARCH_SUBQUERY.format(query=query)}],
                "temperature": EXTRACT_TEMPERATURE,
                "max_tokens": EXTRACT_MAX_TOKENS,
            }),
            (GenerateSubqueries,),
        )
        if not response.has_tool_calls:
            return []
        return response.tool_calls[0].parse_as(GenerateSubqueries).queries

    async def execute_tools(self, tool_calls: list[ToolCall], uid: str) -> list[Message]:
        return [
            Message(role="tool", content=await self.dispatch_tool(call, uid), tool_call_id=call.id)
            for call in tool_calls
        ]

    async def dispatch_tool(self, call: ToolCall, uid: str) -> str:
        match call.tool_name:
            case TOOL_NAME.WebSearch:
                return await self.run_web_search(call)
            case TOOL_NAME.RecallMemory:
                return await self.run_recall_memory(call, uid)
            case TOOL_NAME.SearchFiles:
                return await self.run_search_files(call, uid)
            case TOOL_NAME.ParseUrl:
                return await self.run_parse_url(call)
            case TOOL_NAME.BuildPresentation:
                return await self.run_build_presentation(call)
            case _:
                self.logger.warning("Unknown tool: %s", call.name)
                return ""

    async def run_web_search(self, call: ToolCall) -> str:
        return build_web_context(await self.search.search(call.parsed_arguments["query"]))

    async def run_recall_memory(self, call: ToolCall, uid: str) -> str:
        return build_memory_context(await self.memory.recall(call.parsed_arguments["query"], uid))

    async def run_search_files(self, call: ToolCall, uid: str) -> str:
        return build_file_context(await self.files.search(call.parsed_arguments["query"], uid))

    async def run_parse_url(self, call: ToolCall) -> str:
        return (await self.parser.get(call.parsed_arguments["url"])).text

    async def run_build_presentation(self, call: ToolCall) -> str:
        params = call.parse_as(BuildPresentation)
        return build_file_link(await self.presentation.generate(params.title, params.slides))
