from gpthub.constants import MODEL_ROUTING, MODEL_TYPE
from gpthub.controls import ChatControl
from gpthub.structures import ChatRequest, Message


class TestChatControlResolve:

    def setup_method(self):
        self.chat = ChatControl()

    def _make_request(self, content, model: str = "auto") -> ChatRequest:
        return ChatRequest(
            model=model,
            messages=[Message(role="user", content=content)],
        )

    def test_plain_text_routes_to_text(self):
        result = self.chat.resolve(self._make_request("Привет как дела"))
        assert result.model_type is MODEL_TYPE.TEXT
        assert result.model == MODEL_ROUTING[MODEL_TYPE.TEXT].value
        assert result.auto_routed is True

    def test_code_keyword_routes_to_code(self):
        for prompt in [
            "напиши код на python",
            "write code in javascript",
            "реши баг в функции",
            "нужен regex для email",
        ]:
            result = self.chat.resolve(self._make_request(prompt))
            assert result.model_type is MODEL_TYPE.CODE, f"Failed for: {prompt}"

    def test_reasoning_keyword_routes_to_reasoning(self):
        for prompt in [
            "объясни почему небо голубое",
            "пошагово разбери задачу",
            "проанализируй плюсы и минусы",
        ]:
            result = self.chat.resolve(self._make_request(prompt))
            assert result.model_type is MODEL_TYPE.REASONING, f"Failed for: {prompt}"

    def test_image_gen_keyword_routes_to_image_gen(self):
        for prompt in [
            "нарисуй кота",
            "сгенерируй изображение горы",
            "draw a sunset",
            "picture of a dog",
        ]:
            result = self.chat.resolve(self._make_request(prompt))
            assert result.model_type is MODEL_TYPE.IMAGE_GEN, f"Failed for: {prompt}"

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
        result = self.chat.resolve(request)
        assert result.model_type is MODEL_TYPE.VISION

    def test_manual_model_not_overridden(self):
        result = self.chat.resolve(self._make_request("привет", model="llama-3.3-70b-instruct"))
        assert result.model == "llama-3.3-70b-instruct"
        assert result.auto_routed is False

    def test_manual_vision_model_sets_vision_type(self):
        result = self.chat.resolve(self._make_request("hi", model="qwen2.5-vl-72b"))
        assert result.model == "qwen2.5-vl-72b"
        assert result.model_type is MODEL_TYPE.VISION

    def test_empty_message_routes_to_text(self):
        result = self.chat.resolve(self._make_request(""))
        assert result.model_type is MODEL_TYPE.TEXT

    def test_empty_messages_list_routes_to_text(self):
        result = self.chat.resolve(ChatRequest(model="auto", messages=[]))
        assert result.model_type is MODEL_TYPE.TEXT
