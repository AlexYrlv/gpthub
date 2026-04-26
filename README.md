# GPTHub

OpenAI-совместимый backend поверх любого LLM-провайдера: Ollama, OpenAI, vLLM, Anthropic. Чат, голос, vision, RAG, function calling, долгосрочная память — в одном API.

## Настройки

### Локально через Ollama (без ключей)

1. **Поднять стек:**

   ```bash
   cp .env.example .env
   docker compose --profile ollama up -d
   ```

2. **Скачать минимальный набор моделей** (текстовый чат + RAG):

   ```bash
   docker exec gpthub-ollama ollama pull qwen2.5:7b   # default
   docker exec gpthub-ollama ollama pull bge-m3       # эмбеддинги
   ```

3. **Дополнительные модели** (опционально):

   ```bash
   docker exec gpthub-ollama ollama pull qwen2.5vl:7b      # анализ изображений (VLM)
   docker exec gpthub-ollama ollama pull qwen2.5-coder:7b  # автомаршрутизация на код
   docker exec gpthub-ollama ollama pull deepseek-r1:7b    # reasoning
   ```

4. **Проверить готовность:**

   ```bash
   curl http://localhost:8000/v1/health
   ```

> ASR (whisper) и генерация изображений (sdxl, dall-e) не поддерживаются Ollama напрямую — они требуют внешних провайдеров. По умолчанию `config_docker.json` для них прописывает имена-плейсхолдеры; для рабочего ASR/image gen используйте сценарий "Внешний провайдер".

### С внешним OpenAI-совместимым провайдером

1. **Прописать URL и ключ в `.env`** — откройте файл и замените значения:

   ```ini
   LLM_API_BASE_URL=https://api.openai.com/v1
   LLM_API_KEY=sk-...
   ```

2. **Указать имена моделей провайдера** — отредактируйте секцию `api.llm` в `config_docker.json`:

   ```json
   "api": {
     "llm": {
       "url": "https://api.openai.com/v1",
       "key": "sk-...",
       "default_model": "gpt-4o-mini",
       "vision_model": "gpt-4o",
       "code_model": "gpt-4o",
       "reasoning_model": "o1-mini",
       "embedding_model": "text-embedding-3-small",
       "whisper_model": "whisper-1",
       "image_model": "dall-e-3"
     }
   }
   ```

3. **Запустить и проверить:**

   ```bash
   docker compose up -d
   curl http://localhost:8000/v1/health
   ```

После запуска доступно:

- Чат: <http://localhost:3000>
- API: <http://localhost:8000/v1>
- API docs: <https://alexyrlv.github.io/gpthub/>
- MinIO console: <http://localhost:9001>

## Документация

- Архитектура: [ARCHITECTURE.md](ARCHITECTURE.md)
- API спецификация: [docs/openapi.yml](docs/openapi.yml) · [интерактивный просмотр (Redoc)](https://alexyrlv.github.io/gpthub/)

## Troubleshooting

- **Порты заняты** — нужны свободные `3000`, `8000`, `9000-9001`, `6379`, `27017`, `11434`
- **Модель не найдена** — `docker exec gpthub-ollama ollama pull <имя>` или проверить `GET /v1/models`
- **Сброс памяти/истории** — `docker compose down -v` (флаг `-v` удаляет все volumes проекта)
- **Логи** — `docker compose logs backend memorize openwebui`
- **STT (микрофон)** — работает только на `http://localhost` или `https://`

## Лицензия

MIT. См. [LICENSE](LICENSE).

## Changelog

### 0.1.0

- Текстовый чат, multimodal (VLM), генерация изображений, ASR
- Загрузка файлов с RAG (PDF/DOCX/TXT, эмбеддинги bge-m3)
- Веб-поиск (DuckDuckGo) и парсинг URL через function calling
- Долгосрочная память: автоизвлечение фактов в фоновом Actor, дедупликация по cosine similarity
- Автомаршрутизация модели под задачу (code, reasoning, vision, image_gen, text)
- Deep Research с параллельными подзапросами
- Генерация PPTX через tool-call
- SSE-стриминг ответов
- Multi-user изоляция через `X-OpenWebUI-User-Id`
- OpenAI-совместимое API: `/v1/chat/completions`, `/v1/models`, `/v1/audio/transcriptions`, `/v1/files`, `/v1/health`
