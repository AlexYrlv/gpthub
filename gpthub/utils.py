from __future__ import annotations

import base64
import json
import logging
import re
import uuid
from functools import partial
from io import BytesIO

import rediscache
from config_fastapi import Config
from docx import Document
from pypdf import PdfReader

from .constants import CACHE_PREFIX
from .structures import ChatRequest, WebPage

acached = partial(
    rediscache.acached,
    alias=Config(section="redis").get("alias"),
    key_prefix=CACHE_PREFIX,
    cleanup=True,
)


_logger = logging.getLogger("utils")


def extract_pdf_text(data: bytes) -> str:
    try:
        reader = PdfReader(BytesIO(data))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as e:
        _logger.error("PDF parse error: %s", e)
        return ""


def extract_docx_text(data: bytes) -> str:
    try:
        doc = Document(BytesIO(data))
        return "\n".join(p.text for p in doc.paragraphs)
    except Exception as e:
        _logger.error("DOCX parse error: %s", e)
        return ""


def extract_text_from_file(data: bytes, filename: str, content_type: str = "") -> str:
    lower = filename.lower()
    if lower.endswith(".pdf") or "pdf" in content_type:
        return extract_pdf_text(data)
    if lower.endswith(".docx") or "wordprocessingml" in content_type:
        return extract_docx_text(data)
    try:
        return data.decode("utf-8", errors="ignore")
    except Exception as e:
        _logger.warning("Failed to decode %s: %s", filename, e)
        return ""


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if len(a) != len(b) or not a:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def chunk_text(text: str, size: int, overlap: int) -> list[str]:
    if not text:
        return []
    if len(text) <= size:
        return [text]

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks = []
    current = ""

    for paragraph in paragraphs:
        if len(current) + len(paragraph) + 1 <= size:
            current = f"{current}\n{paragraph}" if current else paragraph
            continue
        if current:
            chunks.append(current)
        if len(paragraph) <= size:
            current = paragraph
            continue
        for i in range(0, len(paragraph), size - overlap):
            chunks.append(paragraph[i:i + size])
        current = ""

    if current:
        chunks.append(current)
    return chunks


def to_data_url(page: WebPage) -> str:
    return f"data:{page.content_type};base64,{base64.b64encode(page.content).decode()}"


def build_dialogue(request: ChatRequest) -> str:
    return "\n".join(f"{msg.role}: {msg.text}" for msg in request.messages[-3:] if msg.role != "system")


def build_memory_context(memories) -> str:
    if not memories:
        return ""
    facts = "\n".join(f"- {m.fact}" for m in memories)
    return (
        "\n\nИзвестные факты о пользователе:\n%s\n"
        "Используй эти факты в ответе, если они релевантны." % facts
    )


def build_web_context(pages) -> str:
    if not pages:
        return ""
    parts = []
    for page in pages:
        if page.title:
            parts.append(f"### {page.title}")
        if page.url:
            parts.append(f"URL: {page.url}")
        if page.text:
            parts.append(page.text)
        parts.append("")
    return "\n\nКонтекст из интернета:\n%s\nИспользуй этот контекст в ответе." % "\n".join(parts)


def build_research_context(subqueries: list[str], pages) -> str:
    if not pages:
        return ""
    parts = ["Направления исследования:"]
    parts.extend(f"- {q}" for q in subqueries)
    parts.append("")
    for page in pages:
        if page.title:
            parts.append(f"### {page.title}")
        if page.url:
            parts.append(f"URL: {page.url}")
        if page.text:
            parts.append(page.text)
        parts.append("")
    return (
        "\n\nРезультаты глубокого исследования:\n%s\n"
        "Составь развёрнутый ответ на основе собранных данных. Указывай источники." % "\n".join(parts)
    )


def is_duplicate_memory(embedding: list[float], existing: list, threshold: float) -> bool:
    return any(cosine_similarity(embedding, m.embedding) > threshold for m in existing if m.embedding)


def score_memories(query_emb: list[float], memories, top_k: int = 5) -> list:
    scored = [(cosine_similarity(query_emb, m.embedding), m) for m in memories if m.embedding]
    scored.sort(key=lambda x: x[0], reverse=True)
    return [m for _, m in scored[:top_k]]


def score_chunks(query_emb: list[float], files, top_k: int = 4) -> list[str]:
    scored = []
    for ctx in files:
        for chunk, emb in zip(ctx.chunks, ctx.embeddings):
            scored.append((cosine_similarity(query_emb, emb), ctx.filename, chunk))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [f"[{fn}] {chunk}" for _, fn, chunk in scored[:top_k]]


def serialize(data: dict) -> str:
    return json.dumps(data)


def new_short_id() -> str:
    return uuid.uuid4().hex[:8]


def parse_tool_args(raw: str) -> dict:
    return json.loads(raw)


def build_file_context(chunks) -> str:
    if not chunks:
        return ""
    return "\n\nКонтекст из загруженных файлов:\n%s\nИспользуй этот контекст в ответе." % "\n\n".join(chunks)


def build_file_link(file) -> str:
    return "📊 Презентация готова: [%s](%s)" % (file.with_extension, file.url)
