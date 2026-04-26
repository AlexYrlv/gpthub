from __future__ import annotations

from unittest.mock import AsyncMock, patch

from hamcrest import assert_that, has_item, has_length, is_
from pytest import mark

from gpthub.controls import ChatControl
from gpthub.structures import ModelInfo, ModelList

from tests.api.responses import ModelListAPI
from tests.constants import URL_MODELS
from tests.mocks import MockStack

pytestmark = mark.configuration({"app": {}})


class TestModelsGet:

    def test_ok(self, client):
        models = ModelList(data=[ModelInfo(id="gpt-4", owned_by="openai")])
        stack = MockStack(
            list_models=patch.object(ChatControl, "list_models", new_callable=AsyncMock, return_value=models),
        )
        with stack.activate() as mocks:  # noqa: F841
            response = client.get(URL_MODELS)

        assert_that(response.status_code, is_(200))
        parsed = ModelListAPI.create(response.json())
        assert_that(parsed.data, has_length(1))
        assert_that(parsed.ids, has_item("gpt-4"))

    def test_empty(self, client):
        stack = MockStack(
            list_models=patch.object(ChatControl, "list_models", new_callable=AsyncMock, return_value=ModelList()),
        )
        with stack.activate() as mocks:  # noqa: F841
            response = client.get(URL_MODELS)

        assert_that(response.status_code, is_(200))
        assert_that(ModelListAPI.create(response.json()).data, has_length(0))
