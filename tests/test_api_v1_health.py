from __future__ import annotations

from unittest.mock import AsyncMock, patch

from hamcrest import assert_that, has_entries, is_
from pytest import mark

from gpthub.controls import HealthControl
from gpthub.structures import HealthStatus

from tests.constants import URL_HEALTH
from tests.mocks import MockStack

pytestmark = mark.configuration({"app": {}})


class TestHealthGet:

    def test_ok(self, client):
        stack = MockStack(
            status=patch.object(HealthControl, "status", new_callable=AsyncMock, return_value=HealthStatus.ok(5)),
        )
        with stack.activate() as mocks:  # noqa: F841
            response = client.get(URL_HEALTH)

        assert_that(response.status_code, is_(200))
        assert_that(response.json(), has_entries({"status": "ok", "llm": True, "models_available": 5}))

    def test_degraded(self, client):
        stack = MockStack(
            status=patch.object(HealthControl, "status", new_callable=AsyncMock, return_value=HealthStatus.degraded()),
        )
        with stack.activate() as mocks:  # noqa: F841
            response = client.get(URL_HEALTH)

        assert_that(response.status_code, is_(200))
        assert_that(response.json(), has_entries({"status": "degraded", "llm": False, "models_available": 0}))
