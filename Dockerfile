FROM python:3.11-slim AS base

RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/* && \
    curl -sL https://taskfile.dev/install.sh | sh -s -- -d -b /usr/local/bin && \
    pip install --no-cache-dir poetry uv

WORKDIR /tmp/deps
COPY pyproject.toml poetry.lock ./
RUN poetry config virtualenvs.create false && \
    poetry install --no-root --only main && \
    rm -rf /tmp/deps

FROM base AS package
WORKDIR /build
COPY dist/ .

FROM base AS runtime
WORKDIR /app
COPY --from=package /build/*.whl /tmp/
RUN uv pip install --system --no-deps /tmp/*.whl && rm -rf /tmp/*.whl

COPY Taskfile.yml manage.py pyproject.toml config_fastapi.json ./
EXPOSE 8000
ENTRYPOINT ["task"]
CMD ["server"]
