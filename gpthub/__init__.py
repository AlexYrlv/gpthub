from __future__ import annotations

from asyncio import AbstractEventLoop
from logging.config import dictConfig

import motorengine
import red_mng as redis_manager
import rediscache
import redislock
from commandlinestart import Cli, Command, echo
from config_fastapi import Config
from fastabc import App, start_server
from fastapi import Request
from fastapilib import abort
from fpiaioact import ActorApp

from . import actors, api_v1, middlewares
from .constants import ACTOR

__version__ = "0.1.0"


def start_app(app: App, **kwargs) -> None:
    return start_server(app, create_app, **kwargs)


def create_app(config: Config = None) -> App:
    config = config if config is not None else application_config()

    app = App(
        name=config.extract("app").get("name", __name__),
        log_config=config.get("logging", {}),
    )
    app.config.update_config(config.extract("app", uppercase=True))
    app.exception(BaseException)(error_response)
    app.signal("server.shutdown.after")(shutdown_server)

    middlewares.init(app)
    api_v1.init(app)

    return app


def create_actors() -> ActorApp:
    application_config()
    return actors.init(__name__)


def application_config() -> Config:
    config = Config(file_path="config_fastapi.json")

    if config.get("logging") is not None:
        dictConfig(config.extract("logging").to_dict())

    motorengine.register_connection(**config.extract("mongodb").to_dict())

    redis_cfg = config.extract("redis")
    redis_manager.register(
        alias=redis_cfg.get("alias"),
        **redis_cfg.extract("connection").to_dict(),
    )
    rediscache.register(
        alias=redis_cfg.get("alias"),
        redis=redis_manager.get(redis_cfg.get("alias")),
    )
    redislock.register(
        alias=redis_cfg.get("alias"),
        redis=redis_manager.get(redis_cfg.get("alias")),
    )

    return config


def custom_run_command(cli: Cli) -> dict[str, Command]:
    def server():
        app = cli.context["app"] if isinstance(cli.context.get("app"), App) else create_app()
        echo(f"[{app.name}] Start server in production mode")
        return start_app(app)

    def worker(cmd: ACTOR):
        app = cli.context["workers"] if isinstance(cli.context.get("workers"), ActorApp) else create_actors()

        def start_worker():
            echo(f"[{app.name}] Start worker '{cmd.value}' in production mode")
            return app(cmd.name).start()

        return start_worker

    return {
        "server": Command(name="server", callback=server, help="Start Web Server"),
        ACTOR.memorize.value: Command(
            name=ACTOR.memorize.name, callback=worker(ACTOR.memorize), help="Run memorize worker",
        ),
    }


def error_response(request: Request, exception: BaseException):
    if request.url.path.startswith("/v1"):
        return api_v1.error_response(request, exception)
    return abort(exception)


async def shutdown_server(app: App, loop: AbstractEventLoop):  # noqa: ARG001
    motorengine.disconnect(Config().extract("mongodb").get("alias"))
    await redis_manager.close(Config().extract("redis").get("alias"))
