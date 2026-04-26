from __future__ import annotations

from unittest.mock import AsyncMock, patch

from hamcrest import assert_that, has_item, is_
from pytest import mark

from gpthub.controls import ChatControl, HealthControl
from gpthub.rest import LLMProviderAPI
from gpthub.structures import ModelInfo, ModelList

from tests.mocks import MockStack

pytestmark = mark.asyncio


class TestHealthControl:

    async def test_status_ok_when_models_available(self):
        stack = MockStack(
            safe_get_models=patch.object(
                LLMProviderAPI, "safe_get_models",
                new_callable=AsyncMock,
                return_value=ModelList(data=[ModelInfo(id="gpt-4")]),
            ),
        )
        with stack.activate() as mocks:  # noqa: F841
            status = await HealthControl().status()

        assert_that(status.llm_available, is_(True))
        assert_that(status.models_count, is_(1))

    async def test_status_degraded_when_no_models(self):
        stack = MockStack(
            safe_get_models=patch.object(
                LLMProviderAPI, "safe_get_models",
                new_callable=AsyncMock,
                return_value=None,
            ),
        )
        with stack.activate() as mocks:  # noqa: F841
            status = await HealthControl().status()

        assert_that(status.llm_available, is_(False))
        assert_that(status.models_count, is_(0))


class TestChatControlListModels:

    async def test_list_models_prepends_auto(self):
        models = ModelList(data=[ModelInfo(id="gpt-4", owned_by="openai")])
        stack = MockStack(
            get_models=patch.object(
                LLMProviderAPI, "get_models",
                new_callable=AsyncMock,
                return_value=models,
            ),
        )
        with stack.activate() as mocks:  # noqa: F841
            result = await ChatControl().list_models()

        assert_that(result.ids, has_item("auto"))
        assert_that(result.ids, has_item("gpt-4"))
