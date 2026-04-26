from __future__ import annotations

import typing as t

from pydantic import BaseModel, Field


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
