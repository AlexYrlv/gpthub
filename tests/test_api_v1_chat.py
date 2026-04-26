from __future__ import annotations

from unittest.mock import AsyncMock, patch

from hamcrest import assert_that, is_, starts_with
from pytest import mark

from gpthub.controls import GPTHubControl
from gpthub.rpc import MemorizeRPC
from gpthub.structures import ChatChoice, ChatResponse, Message

from tests.api.responses import ChatResponseAPI
from tests.constants import URL_CHAT
from tests.mocks import MockStack

pytestmark = mark.configuration({"app": {}})


class TestChatCompletionsPost:

    def test_ok(self, client):
        response_data = ChatResponse(
            id="r-1",
            model="gpt-4",
            choices=[ChatChoice(message=Message(role="assistant", content="hi back"))],
        )
        stack = MockStack(
            process_chat=patch.object(
                GPTHubControl, "process_chat", new_callable=AsyncMock, return_value=response_data,
            ),
            rpc_send=patch.object(MemorizeRPC, "send", new_callable=AsyncMock, return_value=None),
        )
        with stack.activate() as mocks:  # noqa: F841
            response = client.post(
                URL_CHAT,
                json={"model": "auto", "messages": [{"role": "user", "content": "hi"}]},
            )

        assert_that(response.status_code, is_(200))
        parsed = ChatResponseAPI.create(response.json())
        assert_that(parsed.id, is_("r-1"))
        assert_that(parsed.model, is_("gpt-4"))
        assert_that(parsed.content, is_("hi back"))

    def test_stream_returns_sse(self, client):
        async def stream_chunks(_):
            yield "data: hello\n\n"
            yield "data: [DONE]\n\n"

        stack = MockStack(
            process_chat_stream=patch.object(
                GPTHubControl, "process_chat_stream", new=stream_chunks,
            ),
            rpc_send=patch.object(MemorizeRPC, "send", new_callable=AsyncMock, return_value=None),
        )
        with stack.activate() as mocks:  # noqa: F841
            response = client.post(
                URL_CHAT,
                json={"model": "auto", "messages": [{"role": "user", "content": "hi"}], "stream": True},
            )

        assert_that(response.status_code, is_(200))
        assert_that(response.headers["content-type"], starts_with("text/event-stream"))

    @mark.parametrize(
        ("payload", "code"),
        [
            (None, 400),
            ([], 400),
            ({"messages": [{"role": "user", "content": "hi"}]}, 400),
            ({"model": "auto"}, 400),
            ({"model": "auto", "messages": "not a list"}, 400),
        ],
    )
    def test_bad_request(self, payload, code, client):
        stack = MockStack(
            rpc_send=patch.object(MemorizeRPC, "send", new_callable=AsyncMock, return_value=None),
        )
        with stack.activate() as mocks:  # noqa: F841
            response = client.post(URL_CHAT, json=payload)

        assert_that(response.status_code, is_(code))


class TestChatHeaderUserId:

    def test_user_id_propagated(self, client):
        response_data = ChatResponse(
            id="r-1", model="gpt-4",
            choices=[ChatChoice(message=Message(role="assistant", content="ok"))],
        )
        stack = MockStack(
            process_chat=patch.object(
                GPTHubControl, "process_chat", new_callable=AsyncMock, return_value=response_data,
            ),
            rpc_send=patch.object(MemorizeRPC, "send", new_callable=AsyncMock, return_value=None),
        )
        with stack.activate() as mocks:
            client.post(
                URL_CHAT,
                json={"model": "auto", "messages": [{"role": "user", "content": "hi"}]},
                headers={"x-openwebui-user-id": "user-42"},
            )

        chat_request_arg = mocks["process_chat"].call_args.args[0]
        assert_that(chat_request_arg.user_id, is_("user-42"))
