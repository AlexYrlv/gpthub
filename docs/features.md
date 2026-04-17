# Матрица фич

Все 12 обязательных + 3 дополнительных фичи реализованы.

## Обязательные (12)

| #  | Фича                   | Модель LLM-провайдер                        | Эндпоинт / UI                       | Триггер                                  | Статус |
|----|------------------------|---------------------------------------|-------------------------------------|------------------------------------------|--------|
| 1  | Текстовый чат          | `qwen2.5:7b` / `Qwen3-235B`        | `POST /v1/chat/completions`         | дефолт / `model=auto`                    | ✅     |
| 2  | Голосовой чат          | `whisper-turbo-local` → LLM           | OpenWebUI микрофон                  | запись через UI                          | ✅     |
| 3  | Генерация изображений  | `qwen-image-lightning`                | `POST /v1/images/generations`       | tool-call `BuildImage` или ключевые слова| ✅     |
| 4  | Аудиофайлы + ASR       | `whisper-turbo-local`                 | `POST /v1/audio/transcriptions`     | multipart file upload                    | ✅     |
| 5  | Изображения (VLM)      | `qwen3-vl-30b-a3b-instruct`           | `POST /v1/chat/completions`         | наличие `image_url` в сообщении          | ✅     |
| 6  | Файлы + RAG            | `bge-m3` embeddings + LLM             | `POST /v1/files`                    | tool-call `SearchFiles`                  | ✅     |
| 7  | Поиск в интернете      | DuckDuckGo через tool-call            | tool-call `WebSearch`               | LLM решает по контексту запроса          | ✅     |
| 8  | Веб-парсинг            | httpx + BS4 через tool-call           | tool-call `ParseUrl`                | LLM решает по URL в запросе              | ✅     |
| 9  | Долгосрочная память    | function calling + MongoDB + `bge-m3` | фоновый Actor + tool-call `RecallMemory` | автоизвлечение фактов из диалога   | ✅     |
| 10 | Автовыбор модели       | keyword routing + function calling    | `model=auto`                        | по контенту запроса                      | ✅     |
| 11 | Ручной выбор модели    | любая из доступные на провайдере              | OpenWebUI dropdown / `model=<id>`   | пользователь                             | ✅     |
| 12 | Markdown / код / SSE   | OpenAI-compatible stream              | `POST /v1/chat/completions`         | `stream=true`                            | ✅     |

## Дополнительные (3)

| #  | Фича                         | Модель / Инструмент               | Триггер                                       | Статус |
|----|------------------------------|-----------------------------------|-----------------------------------------------|--------|
| 13 | Deep Research                | `Qwen3-235B` + `gather` + DuckDuckGo | «исследуй», «research», «подробно изучи»   | ✅     |
| 14 | Генерация презентаций (PPTX) | `Qwen3-235B` + `python-pptx` + MinIO S3 | tool-call `BuildPresentation`            | ✅     |
| 15 | Function Calling             | `Qwen3-235B` + 5 инструментов     | LLM решает: web_search, recall_memory, search_files, parse_url, build_presentation | ✅ |

## Критерии оценки ↔ фичи

### Полнота функциональности (50 баллов)
Все 12 обязательных + 3 дополнительных реализованы и протестированы.

### Качество автоматизации и памяти (25 баллов)
- **Авто-роутер моделей** — keyword routing под специализированные задачи (code, reasoning, vision, image_gen) + function calling для текста
- **Долгосрочная память** — извлечение структурированных фактов через function calling (Pydantic `SaveFacts`), категоризация (name/job/location/interest/...), дедупликация по cosine similarity, фоновый Actor-воркер
- **RAG** — семантический chunking по абзацам, tool-call `SearchFiles` позволяет модели самостоятельно искать в файлах
- **Web search / parsing** — модель сама решает когда использовать, никаких rule-based триггеров
- **Кэширование** — Redis TTL для моделей, эмбеддингов, веб-поиска, парсинга URL

### UX/UI (25 баллов)
- OpenWebUI как готовый интерфейс (брендирован GPTHub)
- Streaming (SSE) — ответ выводится по мере генерации
- Markdown и подсветка кода из коробки
- Одна команда запуска: `docker compose up -d`
- Голосовой ввод через микрофон, TTS ответов
- Отдельные кнопки для image generation, code interpreter, channels

## Используемые модели LLM-провайдер

| Тип             | Модель                                 | Обоснование                                   |
|-----------------|----------------------------------------|-----------------------------------------------|
| Text (default)  | `qwen2.5:7b`                        | Универсальный чат                    |
| Tool-calls      | `Qwen3-235B-A22B-Instruct-2507-FP8`    | 235B параметров, параллельные tool calls      |
| Code            | `qwen3-coder-480b-a35b`                | Специализированная для кода                   |
| Reasoning       | `deepseek-r1-distill-qwen-32b`         | Быстрее QwQ-32B                               |
| Vision          | `qwen3-vl-30b-a3b-instruct`            | Быстрая VLM (1.3с отклик)                     |
| ASR             | `whisper-turbo-local`                  | Быстрее whisper-medium                        |
| Embeddings      | `bge-m3`                               | Мультиязычная, 1024-dim                       |
| Image gen       | `qwen-image-lightning`                 | Быстрая генерация                             |
