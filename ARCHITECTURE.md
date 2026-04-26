# Архитектура GPTHub

## Контур сервисов

```mermaid
flowchart LR
    User((Пользователь))

    subgraph Docker["Docker Compose"]
        UI[OpenWebUI<br/>:3000]
        API[Backend API<br/>FastAPI :8000]
        Worker[Memorize Worker<br/>Actor]
        Mongo[(MongoDB<br/>memory, files)]
        Redis[(Redis<br/>cache, RPC)]
    end

    subgraph External["Внешние сервисы"]
        LLM[LLM-провайдер<br/>]
        DDG[DuckDuckGo]
        Web[Любые URL<br/>из запроса]
    end

    User -->|HTTPS| UI
    UI -->|OpenAI-compatible<br/>POST /v1/*| API
    API -->|LLM / VLM / ASR /<br/>Image / Embeddings| LLM
    API -->|RPC publish| Redis
    Redis -->|RPC subscribe| Worker
    Worker --> Mongo
    Worker -->|extract facts| LLM
    API --> Mongo
    API --> Redis
    API -->|web search| DDG
    API -->|url fetch| Web
```

## User Flow — общий чат

```mermaid
sequenceDiagram
    participant U as Пользователь
    participant W as OpenWebUI
    participant A as Backend API
    participant R as Router
    participant M as LLM

    U->>W: сообщение
    W->>A: POST /v1/chat/completions
    A->>A: Pydantic валидация
    A->>R: resolve(request)
    R->>R: ключевые слова / image_url / URL / файлы
    R-->>A: RoutingResult(model, model_type)

    alt long-term memory
        A->>A: recall_facts(user_id)
        A->>A: inject system_context
    end

    alt RAG контекст
        A->>A: rag.find_relevant(chunks)
        A->>A: inject system_context
    end

    alt web search / url
        A->>A: search / fetch
        A->>A: inject system_context
    end

    A->>M: chat_completions(tools=[web_search, recall_memory, parse_url])
    M-->>A: ChatResponse

    alt tool_calls в ответе
        A->>A: execute_tools (web_search / recall_memory / parse_url)
        A->>M: chat_completions (с результатами инструментов)
        M-->>A: финальный ChatResponse
    end

    A->>A: RPC publish → MemorizeWorker (фоновое извлечение фактов)
    A-->>W: JSON / SSE stream
    W-->>U: render markdown
```

## Layer architecture

```mermaid
flowchart TB
    subgraph Input["Входной слой"]
        API[api_v1.py<br/>Resources]
    end

    subgraph Coord["Координация"]
        CTRL[controls.py<br/>GPTHubControl<br/>ChatControl<br/>MemoryControl<br/>FileControl<br/>AudioControl]
    end

    subgraph Background["Фоновые процессы"]
        RPC[rpc.py<br/>MemorizeRPC]
        ACTOR[actors/memorize.py<br/>MemorizeWorker]
    end

    subgraph Output["Выходной слой"]
        REST[rest.py<br/>LLMProviderAPI]
        CLI[clients.py<br/>WebParserClient<br/>WebSearchClient]
    end

    subgraph Storage
        MONGO[mongodb.py<br/>Document + query functions]
        CACHE[rediscache<br/>@acached]
    end

    subgraph Shared
        STRUCT[structures.py<br/>dataclass]
        MODELS[models.py<br/>Pydantic]
        CONST[constants.py<br/>Enum, routing, TTL]
    end

    API --> CTRL
    API --> RPC
    RPC --> ACTOR
    ACTOR --> CTRL
    CTRL --> REST
    CTRL --> CLI
    CTRL --> MONGO
    REST -.-> CACHE
    CLI -.-> CACHE

    API -.-> MODELS
    CTRL -.-> STRUCT
    REST -.-> STRUCT
    CTRL -.-> CONST
```

### Правила взаимодействия слоёв

| Может                          | Нельзя                                |
|--------------------------------|---------------------------------------|
| `api_v1` → `controls`          | `api_v1` → `rest` (обход controls)    |
| `controls` → `rest`            | `rest` → `rest`                       |
| `controls` → `clients`         | `rest` → `controls` (обратный вызов)  |
| `controls` → `mongodb`         |                                       |
| `controls` → `controls`        |                                       |

## Роутер

```mermaid
flowchart TB
    Start[ChatRequest] --> Manual{model != auto?}
    Manual -->|да| ManualType{тип модели}
    ManualType --> Return1[RoutingResult<br/>auto_routed=false]

    Manual -->|нет| Image{есть image_url?}
    Image -->|да| Vision[MODEL_TYPE.VISION<br/>qwen3-vl-30b]

    Image -->|нет| Keywords{ключевые слова}
    Keywords -->|нарисуй/draw/image| ImgGen[MODEL_TYPE.IMAGE_GEN<br/>qwen-image-lightning]
    Keywords -->|код/python/...| Code[MODEL_TYPE.CODE<br/>qwen3-coder-480b]
    Keywords -->|почему/объясни/...| Reason[MODEL_TYPE.REASONING<br/>deepseek-r1]
    Keywords -->|ничего не сработало| Text[MODEL_TYPE.TEXT<br/>qwen2.5-72b]

    Vision --> Return2[RoutingResult<br/>auto_routed=true]
    ImgGen --> Return2
    Code --> Return2
    Reason --> Return2
    Text --> Return2
```

## Долгосрочная память

```mermaid
flowchart LR
    subgraph Chat["Фоновый Actor-процесс"]
        A[RPC message] --> B[извлечение фактов<br/>function calling qwen3-32b]
        B --> C{дедупликация<br/>cosine > 0.85?}
        C -->|новый факт| D[embedding через bge-m3]
        D --> E[(MongoDB<br/>memories<br/>category + fact + embedding)]
        C -->|дубликат| F[skip]
    end

    subgraph Recall["Перед запросом"]
        F[сообщение пользователя] --> G[embedding]
        G --> H[(MongoDB<br/>cosine similarity)]
        H --> I[топ-N фактов]
        I --> J[system prompt addon]
    end
```

Хранение: `MongoDB.memories` — коллекция с `user_id`, `fact`, `embedding`, `source` (category: name/job/location/interest/...), `created_at`. Дедупликация по cosine similarity > 0.85. Извлечение фактов через function calling (Pydantic schema → tool_calls).

## RAG

```mermaid
flowchart LR
    subgraph Upload["POST /v1/files"]
        F[PDF / DOCX / TXT] --> T[extract text]
        T --> CK[chunk_text<br/>семантический по абзацам, 500 chars]
        CK --> EMB[bge-m3 embedding]
        EMB --> M[(MongoDB<br/>files)]
    end

    subgraph Query["chat_completions"]
        Q[user message] --> QE[embedding]
        QE --> S[cosine similarity<br/>top-4 chunks]
        S --> CTX[инъекция в system prompt]
    end
```

## Кэширование

`rediscache.@acached` с TTL:

| Кэш                     | TTL         | Функция                             |
|-------------------------|-------------|-------------------------------------|
| Список моделей          | 10 минут    | `LLMProviderAPI.get_models`              |
| Embeddings              | 24 часа     | `LLMProviderAPI.get_embeddings`          |
| Веб-страница по URL     | 1 час       | `WebParserClient.get`               |
| Результаты веб-поиска   | 15 минут    | `WebSearchClient.search`            |

Ключи формируются как `gpthub/<sha1(func_name + args + kwargs)>` — стабильны между перезапусками процесса благодаря `Cacheable` mixin и явным `__repr__`.
