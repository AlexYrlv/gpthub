from __future__ import annotations

from config_fastapi import Config
from fastabc import App
from fastapi.testclient import TestClient
from pytest import fixture

from gpthub import create_app


@fixture(name="cfg")
def cfg(request) -> Config:
    marker = request.node.get_closest_marker("configuration")
    return Config(marker.args[0] if marker is not None else {})


@fixture(name="app")
def app(cfg: Config) -> App:
    return create_app(cfg)


@fixture(name="client")
def client(app: App) -> TestClient:
    return TestClient(app)
