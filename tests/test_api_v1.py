from __future__ import annotations

from unittest.mock import AsyncMock, patch

from duckduckgo_search.exceptions import DuckDuckGoSearchException
from hamcrest import assert_that, is_
from pytest import mark
from webparser.exceptions import WebParserError

from gpthub.controls import GPTHubControl
from gpthub.exceptions import (
    FileContextNotFoundError,
    FileParseError,
    ImageGenerationError,
    LLMProviderError,
    MemoryNotFoundError,
    ModelNotAvailableError,
)
from gpthub.rpc import MemorizeRPC

from tests.constants import URL_CHAT
from tests.mocks import MockStack

pytestmark = mark.configuration({"app": {}})


class TestErrorResponse:

    @mark.parametrize(
        ("exception", "code"),
        [
            (ModelNotAvailableError("auto"), 400),
            (MemoryNotFoundError("memory"), 404),
            (FileContextNotFoundError("file"), 404),
            (FileParseError("cannot parse"), 400),
            (ImageGenerationError("empty"), 400),
            (LLMProviderError("upstream down"), 400),
            (WebParserError("parse failed"), 400),
            (DuckDuckGoSearchException("rate limited"), 400),
        ],
    )
    def test_exception_to_http_code(self, exception, code, client):
        payload = {"model": "auto", "messages": [{"role": "user", "content": "hi"}]}
        stack = MockStack(
            process_chat=patch.object(
                GPTHubControl, "process_chat", new_callable=AsyncMock, side_effect=exception,
            ),
            rpc_send=patch.object(MemorizeRPC, "send", new_callable=AsyncMock, return_value=None),
        )
        with stack.activate() as mocks:  # noqa: F841
            response = client.post(URL_CHAT, json=payload)

        assert_that(response.status_code, is_(code))
