from __future__ import annotations

from logging import Logger, getLogger

from fastabc import App
from fastabc.middlewares import (
    add_request_id,
    log_request,
    log_response,
    set_request_id,
)
from fastapi.middleware.cors import CORSMiddleware


def init(app: App, logger: Logger | None = None) -> App:
    logger = logger if isinstance(logger, Logger) else getLogger("http")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(add_request_id())
    app.add_middleware(set_request_id())
    app.add_middleware(log_request(logger.getChild("request")))
    app.add_middleware(log_response(logger.getChild("response")))

    return app
