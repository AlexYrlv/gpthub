from __future__ import annotations

from hamcrest import assert_that, is_
from pytest import mark

from gpthub.constants import MODEL_ROUTING, MODEL_TYPE
from gpthub.controls import ChatControl
from gpthub.structures import ChatRequest, Message, RoutingResult


def make_request(content, model: str = "auto") -> ChatRequest:
    return ChatRequest(
        model=model,
        messages=[Message(role="user", content=content)],
    )


class TestChatControlClassify:

    def test_plain_text_routes_to_text(self):
        assert_that(ChatControl.classify(make_request("Привет как дела")), is_(MODEL_TYPE.TEXT))

    @mark.parametrize("prompt", [
        "напиши код на python",
        "write code in javascript",
        "реши баг в функции",
        "нужен regex для email",
    ])
    def test_code_keyword_routes_to_code(self, prompt):
        assert_that(ChatControl.classify(make_request(prompt)), is_(MODEL_TYPE.CODE))

    @mark.parametrize("prompt", [
        "объясни почему небо голубое",
        "пошагово разбери задачу",
        "проанализируй плюсы и минусы",
    ])
    def test_reasoning_keyword_routes_to_reasoning(self, prompt):
        assert_that(ChatControl.classify(make_request(prompt)), is_(MODEL_TYPE.REASONING))

    @mark.parametrize("prompt", [
        "нарисуй кота",
        "сгенерируй изображение горы",
        "draw a sunset",
        "picture of a dog",
    ])
    def test_image_gen_keyword_routes_to_image_gen(self, prompt):
        assert_that(ChatControl.classify(make_request(prompt)), is_(MODEL_TYPE.IMAGE_GEN))

    def test_image_in_message_routes_to_vision(self):
        request = ChatRequest(
            model="auto",
            messages=[Message(
                role="user",
                content=[
                    {"type": "text", "text": "что на картинке"},
                    {"type": "image_url", "image_url": {"url": "data:..."}},
                ],
            )],
        )
        assert_that(ChatControl.classify(request), is_(MODEL_TYPE.VISION))

    def test_empty_message_routes_to_text(self):
        assert_that(ChatControl.classify(make_request("")), is_(MODEL_TYPE.TEXT))

    def test_empty_messages_list_routes_to_text(self):
        assert_that(ChatControl.classify(ChatRequest(model="auto", messages=[])), is_(MODEL_TYPE.TEXT))


class TestRoutingResult:

    def test_manual_default_model_type_is_text(self):
        result = RoutingResult.manual("llama-3.3-70b-instruct")
        assert_that(result.model, is_("llama-3.3-70b-instruct"))
        assert_that(result.model_type, is_(MODEL_TYPE.TEXT))
        assert_that(result.auto_routed, is_(False))

    def test_manual_vision_model_sets_vision_type(self):
        result = RoutingResult.manual("qwen2.5-vl-72b", MODEL_TYPE.VISION)
        assert_that(result.model, is_("qwen2.5-vl-72b"))
        assert_that(result.model_type, is_(MODEL_TYPE.VISION))
        assert_that(result.auto_routed, is_(False))

    def test_auto_resolves_model_from_routing(self):
        result = RoutingResult.auto(MODEL_TYPE.TEXT)
        assert_that(result.model, is_(MODEL_ROUTING[MODEL_TYPE.TEXT].value))
        assert_that(result.model_type, is_(MODEL_TYPE.TEXT))
        assert_that(result.auto_routed, is_(True))
