from __future__ import annotations

from enum import Enum, StrEnum
from types import MappingProxyType

REST_DEFAULT_HEADERS = MappingProxyType({"Content-Type": "application/json;charset=utf-8"})
REST_DEFAULT_TIMEOUT = 120

CACHE_PREFIX = "gpthub/{}"
CACHE_TTL_MODELS = 600
CACHE_TTL_EMBEDDING = 86400
CACHE_TTL_WEB_PAGE = 3600
CACHE_TTL_WEB_SEARCH = 900


class ACTOR(Enum):
    memorize = "worker.memorize"


class TOOL_NAME(Enum):
    WebSearch = "WebSearch"
    RecallMemory = "RecallMemory"
    SearchFiles = "SearchFiles"
    ParseUrl = "ParseUrl"
    BuildPresentation = "BuildPresentation"
    unknown = ""

    @staticmethod
    def get(name: str) -> TOOL_NAME:
        try:
            return TOOL_NAME(name)
        except ValueError:
            return TOOL_NAME.unknown


class REST_ENDPOINTS_LLM(Enum):  # noqa: N801
    CHAT_COMPLETIONS = "chat/completions"
    MODELS = "models"
    EMBEDDINGS = "embeddings"
    AUDIO_TRANSCRIPTIONS = "audio/transcriptions"
    IMAGES_GENERATIONS = "images/generations"

    @classmethod
    def to_routes(cls) -> dict[str, str]:
        return {route.name: route.value for route in cls}


class LLM_MODEL(StrEnum):  # noqa: N801
    # Text LLMs (opensource)
    QWEN_72B = "qwen2.5-72b-instruct"
    QWEN3_32B = "qwen3-32b"
    QWEN3_235B = "Qwen3-235B-A22B-Instruct-2507-FP8"
    DEEPSEEK_R1 = "deepseek-r1-distill-qwen-32b"
    QWQ_32B = "QwQ-32B"
    LLAMA_70B = "llama-3.3-70b-instruct"
    LLAMA_8B = "llama-3.1-8b-instruct"
    GEMMA_27B = "gemma-3-27b-it"
    GPT_OSS_20B = "gpt-oss-20b"
    GPT_OSS_120B = "gpt-oss-120b"
    GLM_357B = "glm-4.6-357b"
    KIMI_K2 = "kimi-k2-instruct"

    # Code
    QWEN3_CODER = "qwen3-coder-480b-a35b"

    # Vision (VLM)
    COTYPE_VL = "cotype-pro-vl-32b"
    QWEN_VL = "qwen2.5-vl"
    QWEN_VL_72B = "qwen2.5-vl-72b"
    QWEN3_VL = "qwen3-vl-30b-a3b-instruct"

    # ASR
    WHISPER_MEDIUM = "whisper-medium"
    WHISPER_TURBO = "whisper-turbo-local"

    # Embeddings
    BGE_M3 = "bge-m3"
    BGE_GEMMA = "BAAI/bge-multilingual-gemma2"
    QWEN3_EMB = "qwen3-embedding-8b"

    # Image Generation
    QWEN_IMAGE = "qwen-image"
    QWEN_IMAGE_FAST = "qwen-image-lightning"


class MODEL_TYPE(StrEnum):  # noqa: N801
    TEXT = "text"
    CODE = "code"
    REASONING = "reasoning"
    VISION = "vision"
    ASR = "asr"
    EMBEDDING = "embedding"
    IMAGE_GEN = "image_gen"
    TOOL_CALL = "tool_call"


class EXTENSION(Enum):
    PPTX = "pptx"

    @property
    def mime(self) -> str:
        return MIME[self]


MIME = MappingProxyType({
    EXTENSION.PPTX: "application/vnd.openxmlformats-officedocument.presentationml.presentation",
})


MODEL_ROUTING = MappingProxyType({
    MODEL_TYPE.TEXT: LLM_MODEL.QWEN_72B,
    MODEL_TYPE.CODE: LLM_MODEL.QWEN3_CODER,
    MODEL_TYPE.REASONING: LLM_MODEL.DEEPSEEK_R1,
    MODEL_TYPE.VISION: LLM_MODEL.QWEN3_VL,
    MODEL_TYPE.ASR: LLM_MODEL.WHISPER_TURBO,
    MODEL_TYPE.EMBEDDING: LLM_MODEL.BGE_M3,
    MODEL_TYPE.IMAGE_GEN: LLM_MODEL.QWEN_IMAGE_FAST,
    MODEL_TYPE.TOOL_CALL: LLM_MODEL.QWEN3_235B,
})

MODEL_FALLBACK = MappingProxyType({
    MODEL_TYPE.TEXT: (LLM_MODEL.QWEN_72B, LLM_MODEL.LLAMA_70B, LLM_MODEL.GEMMA_27B),
    MODEL_TYPE.CODE: (LLM_MODEL.QWEN3_CODER, LLM_MODEL.QWEN3_235B, LLM_MODEL.QWEN_72B),
    MODEL_TYPE.REASONING: (LLM_MODEL.DEEPSEEK_R1, LLM_MODEL.QWQ_32B, LLM_MODEL.QWEN3_235B),
    MODEL_TYPE.VISION: (LLM_MODEL.QWEN3_VL, LLM_MODEL.QWEN_VL_72B, LLM_MODEL.QWEN_VL),
    MODEL_TYPE.ASR: (LLM_MODEL.WHISPER_TURBO, LLM_MODEL.WHISPER_MEDIUM),
    MODEL_TYPE.EMBEDDING: (LLM_MODEL.BGE_M3, LLM_MODEL.BGE_GEMMA, LLM_MODEL.QWEN3_EMB),
    MODEL_TYPE.IMAGE_GEN: (LLM_MODEL.QWEN_IMAGE_FAST, LLM_MODEL.QWEN_IMAGE),
    MODEL_TYPE.TOOL_CALL: (LLM_MODEL.QWEN3_235B, LLM_MODEL.GPT_OSS_120B, LLM_MODEL.QWEN_72B),
})



VISION_MODELS = frozenset({
    LLM_MODEL.COTYPE_VL.value,
    LLM_MODEL.QWEN_VL.value,
    LLM_MODEL.QWEN_VL_72B.value,
    LLM_MODEL.QWEN3_VL.value,
})

IMAGE_GEN_MODELS = frozenset({
    LLM_MODEL.QWEN_IMAGE.value,
    LLM_MODEL.QWEN_IMAGE_FAST.value,
})

CODE_KEYWORDS = frozenset({
    "код", "code", "функци", "function", "class", "def ", "import ",
    "баг", "bug", "fix", "ошибк", "error", "debug", "рефактор",
    "python", "javascript", "typescript", "rust", "golang", "java",
    "sql", "html", "css", "react", "fastapi", "django", "flask",
    "алгоритм", "algorithm", "regex", "api", "endpoint",
    "напиши код", "напиши скрипт", "напиши программ",
    "write code", "write script", "implement",
})

REASONING_KEYWORDS = frozenset({
    "почему", "why", "объясни", "explain", "проанализируй", "analyze",
    "сравни", "compare", "оцени", "evaluate", "разбери", "подумай",
    "think", "reason", "step by step", "пошагово", "логик",
    "плюсы и минусы", "pros and cons", "за и против",
    "стратеги", "strategy", "план", "plan",
})

IMAGE_GEN_KEYWORDS = frozenset({
    "нарисуй", "draw", "сгенерируй изображ", "generate image",
    "создай картин", "create image", "создай изображ",
    "нарисуй мне", "покажи как выглядит", "визуализируй",
    "illustrate", "сделай картин", "сделай изображ",
    "image of", "picture of", "photo of",
})

KEYWORD_ROUTING = MappingProxyType({
    MODEL_TYPE.IMAGE_GEN: IMAGE_GEN_KEYWORDS,
    MODEL_TYPE.CODE: CODE_KEYWORDS,
    MODEL_TYPE.REASONING: REASONING_KEYWORDS,
})

SINGLE_PURPOSE_MODEL_TYPES = frozenset({
    MODEL_TYPE.IMAGE_GEN,
    MODEL_TYPE.VISION,
    MODEL_TYPE.CODE,
    MODEL_TYPE.REASONING,
})

WEB_SEARCH_MAX_RESULTS = 5

RESEARCH_KEYWORDS = frozenset({
    "исследуй", "исследовани", "research", "deep research",
    "подробно изучи", "проведи анализ", "подробный анализ",
    "обзор темы", "разбери тему", "всесторонн",
})

RESEARCH_SUBQUERY_PROMPT = (
    "Разбей вопрос пользователя на 3-5 поисковых подзапросов для глубокого исследования. "
    "Каждый подзапрос должен раскрывать отдельный аспект темы.\n\n"
    "Вопрос: {query}"
)

RESEARCH_MAX_SUBQUERIES = 5
RESEARCH_RESULTS_PER_QUERY = 3

RAG_CHUNK_SIZE = 500
RAG_CHUNK_OVERLAP = 50
RAG_TOP_K = 4
DEFAULT_USER_ID = "default"

MEMORY_TOP_K = 5
MEMORY_DEDUP_THRESHOLD = 0.92
EXTRACT_DIALOGUE_LIMIT = 2000
EXTRACT_TEMPERATURE = 0.1
EXTRACT_MAX_TOKENS = 500
EXTRACT_PROMPT = (
    "Проанализируй диалог и вызови save_facts для сохранения всех найденных фактов о пользователе. "
    "Извлекай только конкретные факты: имя, профессию, город, интересы, предпочтения, навыки.\n\n"
    "Диалог:\n{dialogue}"
)

PRESENTATION_KEYWORDS = frozenset({
    "презентаци", "слайд", "presentation", "slides",
    "сделай презентацию", "подготовь презентацию",
    "создай презентацию", "make a presentation",
})

PRESENTATION_CONTEXT = (
    "\n\nПользователь просит создать презентацию. Оформи ответ как набор слайдов:\n"
    "- Каждый слайд начинается с заголовка '## Слайд N: Название'\n"
    "- Разделяй слайды горизонтальной линией '---'\n"
    "- На каждом слайде 3-5 тезисов в виде списка\n"
    "- Первый слайд — титульный (заголовок + подзаголовок)\n"
    "- Последний слайд — выводы или итоги\n"
    "- Используй emoji для визуального акцента\n"
    "- Оптимально 5-8 слайдов\n"
)
