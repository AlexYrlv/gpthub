#!/usr/bin/env python
from __future__ import annotations

from http.client import HTTPConnection
from pprint import pformat
from urllib.parse import urlparse

from commandlinestart import Cli, Command, Option, echo
from commandlinestart.commands import shell
from commandlinestart.output import table_print
from commandlinestart.utils import enable_debug
from toml import load

import gpthub as service


def create_cli() -> Cli:
    cli = Cli(service=service)

    if (ctx := getattr(service, "change_cli_context", None)) is not None:
        ctx(cli)

    cli.add_command("shell", shell(welcome=getattr(service, "welcome", None), context=cli.context))
    cli.add_subcommand(
        name="run",
        commands=custom_run(cli) if (custom_run := getattr(service, "custom_run_command", None)) is not None else run(cli),
        help="Run application parts",
    )
    cli.add_subcommand(
        name="debug",
        commands=custom_dbg(cli) if (custom_dbg := getattr(service, "custom_debug_command", None)) is not None else debug(cli),
        help="Run debugger for parts",
    )
    cli.add_subcommand(
        name="show",
        commands=custom_show(cli) if (custom_show := getattr(service, "custom_show_command", None)) is not None else show(cli),
        help="Display information about application",
    )
    cli.add_subcommand(
        name="health",
        commands=custom_health(cli) if (custom_health := getattr(service, "custom_health_command", None)) is not None else health(cli),
        help="Health checks",
    )
    if (subcommands := getattr(service, "create_extra_commands", None)) is not None:
        subcommands(cli)

    return cli


def run(cli: Cli) -> dict[str, Command]:
    def server():
        app = cli.context["app"] if isinstance(cli.context.get("app"), service.App) else service.create_app()
        echo(f"[{app.name}] Start server in production mode")
        return service.start_app(app)

    return {"server": Command(name="server", callback=server, help="Start Web Server")}


def debug(cli: Cli) -> dict[str, Command]:
    wait_option = Option(param_decls=["--wait"], is_flag=True, help="Wait debugger before start")

    def server(wait: bool = False):
        app = cli.context["app"] if isinstance(cli.context.get("app"), service.App) else service.create_app()
        echo(f"[{app.name}] Start server in debug mode (Waiting: {wait})")
        enable_debug(wait=wait)
        return service.start_app(app, reload=True)

    return {"server": Command(name="server", callback=server, params=[wait_option], help="Start Web Server")}


def show(cli: Cli) -> dict[str, Command]:
    def config():
        """Application config"""
        app = cli.context["app"] if isinstance(cli.context.get("app"), service.App) else service.create_app()

        table_print("App Config")
        echo(pformat(app.config.to_dict()))

    def description():
        """Base information"""
        project = load("pyproject.toml")["project"]
        urls = project.get("urls", {})

        table_print(project["name"])
        echo(
            f"Version: {project['version']}\n"
            f"Description: {project.get('description', 'unknown')}\n"
            f"Repository: {urls.get('repository', 'unset')}"
        )

    def routes():
        """Print routes information"""
        app = cli.context["app"] if isinstance(cli.context.get("app"), service.App) else service.create_app()

        string_size = 90
        headers = ("Uri", "Name")
        echo(f"{headers[0]}{(' ' * (string_size // 2 - len(headers[0])))}{headers[1]}")
        echo("".ljust(string_size, "-"))
        for route in app.routes:
            line = (route.path, route.name or "")
            echo(f"{line[0]}{(' ' * (string_size // 2 - len(line[0])))}{line[1]}")

    return {
        "config": Command(name="config", callback=config, help="Prints application config"),
        "description": Command(name="description", callback=description, help="Base information"),
        "routes": Command(name="routes", callback=routes, help="Print http routes"),
    }


def health(cli: Cli) -> dict[str, Command]:  # noqa: ARG001
    def alive(address: str, timeout: int):
        parsed_url = urlparse(address)

        try:
            conn = HTTPConnection(parsed_url.netloc, timeout=timeout)
            conn.request("GET", parsed_url.path or "/")
            result = conn.getresponse()
        except OSError as ex:
            echo(f"Address '{address}' is not alive. Reason: {ex}")
            raise SystemExit(1) from ex
        else:
            echo(f"Address '{address}' is alive. Status: {result.status}")
            raise SystemExit(0)
        finally:
            conn.close()

    return {
        "alive": Command(
            name="alive",
            callback=alive,
            params=[
                Option(param_decls=["-a", "--address"], help="Check address is alive", required=True),
                Option(param_decls=["-t", "--timeout"], help="Response timeout", default=60),
            ],
            help="Test service HTTP alive status",
        )
    }


if __name__ == "__main__":
    create_cli().start()
