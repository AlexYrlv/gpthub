ARG env=production
ARG package_target=/tmp/dist
ARG runtime=python:3.11-slim

FROM ${runtime} AS package

ARG env
ARG package_target

WORKDIR /build
COPY pyproject.toml poetry.lock* README.md ./
COPY gpthub/ gpthub/
COPY manage.py .

RUN pip install --no-cache-dir poetry && \
    poetry config virtualenvs.create false && \
    poetry build -f wheel -o ${package_target}

FROM ${runtime} AS runtime

ARG env
ARG package_target
ARG package_tmp=/usr/local/src/app

RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/* && \
    useradd -r -s /bin/false app

COPY --from=package ${package_target} ${package_tmp}

RUN pip install --no-cache-dir ${package_tmp}/*.whl && \
    rm -rf ${package_tmp}

WORKDIR /app
COPY --chown=app manage.py config_fastapi.json ./
COPY --chown=app gpthub/ gpthub/

USER app
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -fsS http://localhost:8000/v1/health || exit 1

ENTRYPOINT ["python", "manage.py"]
CMD ["run", "server"]
