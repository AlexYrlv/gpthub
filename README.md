# GPTHub

OpenAI-совместимый backend поверх любого LLM-провайдера: Ollama, OpenAI, vLLM, Anthropic. Чат, голос, vision, RAG, function calling, долгосрочная память — в одном API.

## Настройки

### Локально через Ollama (без ключей)

```bash
cp .env.example .env
docker compose --profile ollama up -d

docker exec gpthub-ollama ollama pull qwen2.5:7b
docker exec gpthub-ollama ollama pull bge-m3
```

### С внешним OpenAI-совместимым провайдером

```bash
cp .env.example .env
# В .env:
#   LLM_API_BASE_URL=https://api.openai.com/v1
#   LLM_API_KEY=sk-...

docker compose up -d
```

После запуска:

- Чат: <http://localhost:3000>
- API: <http://localhost:8000/v1>
- Health: `curl http://localhost:8000/v1/health`

## Документация

- Архитектура: [docs/architecture.md](docs/architecture.md)
- API спецификация: [docs/openapi.yml](docs/openapi.yml)

## Troubleshooting

- **Порты заняты** — нужны свободные `3000`, `8000`, `9000-9001`, `6379`, `27017`, `11434`
- **Модель не найдена** — `docker exec gpthub-ollama ollama pull <имя>` или проверить `GET /v1/models`
- **Сброс памяти/истории** — `docker compose down && docker volume rm gpthub_mongodb_data gpthub_openwebui_data`
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
