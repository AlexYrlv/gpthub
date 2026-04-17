from __future__ import annotations

from gpthub.constants import MODEL_TYPE
from gpthub.structures import (
    ChatChoice,
    ChatRequest,
    ChatResponse,
    FileContext,
    GeneratedImage,
    Memory,
    Message,
    RoutingResult,
    WebPage,
)


class TestMessage:

    def test_create_empty(self):
        msg = Message.create({})
        assert msg.role == ""
        assert msg.content == ""

    def test_create_from_dict(self):
        msg = Message.create({"role": "user", "content": "hi"})
        assert msg.role == "user"
        assert msg.content == "hi"

    def test_text_from_string(self):
        msg = Message(role="user", content="hello")
        assert msg.text == "hello"

    def test_text_from_multimodal_content(self):
        msg = Message(
            role="user",
            content=[
                {"type": "text", "text": "Describe this"},
                {"type": "image_url", "image_url": {"url": "data:..."}},
            ],
        )
        assert msg.text == "Describe this"
        assert msg.has_image is True

    def test_has_image_false_for_text(self):
        msg = Message(role="user", content="just text")
        assert msg.has_image is False

    def test_set_content_returns_same_when_unchanged(self):
        msg = Message(role="user", content="hi")
        assert msg.set_content("hi") is msg

    def test_set_content_returns_new_when_changed(self):
        msg = Message(role="user", content="hi")
        new_msg = msg.set_content("hello")
        assert new_msg is not msg
        assert new_msg.content == "hello"
        assert msg.content == "hi"

    def test_to_dict(self):
        msg = Message(role="assistant", content="response")
        assert msg.to_dict() == {"role": "assistant", "content": "response"}


class TestChatRequest:

    def test_create_empty(self):
        req = ChatRequest.create({})
        assert req.messages == []
        assert req.model == ""

    def test_create_from_dict(self):
        req = ChatRequest.create({
            "model": "gpt-4",
            "messages": [{"role": "user", "content": "hi"}],
            "temperature": 0.5,
            "stream": True,
        })
        assert req.model == "gpt-4"
        assert len(req.messages) == 1
        assert req.messages[0].role == "user"
        assert req.temperature == 0.5
        assert req.stream is True

    def test_last_message_empty(self):
        req = ChatRequest()
        assert req.last_message is None
        assert req.last_text == ""

    def test_last_message_and_text(self):
        req = ChatRequest(messages=[
            Message(role="user", content="first"),
            Message(role="user", content="second"),
        ])
        assert req.last_message.content == "second"
        assert req.last_text == "second"

    def test_has_image_false(self):
        req = ChatRequest(messages=[Message(role="user", content="text")])
        assert req.has_image is False

    def test_has_image_true_with_multimodal(self):
        req = ChatRequest(messages=[
            Message(
                role="user",
                content=[
                    {"type": "text", "text": "what"},
                    {"type": "image_url", "image_url": {"url": "data:..."}},
                ],
            )
        ])
        assert req.has_image is True

    def test_set_model(self):
        req = ChatRequest(model="a")
        assert req.set_model("a") is req
        assert req.set_model("b").model == "b"

    def test_set_messages(self):
        req = ChatRequest(messages=[Message(role="user", content="hi")])
        new_messages = [Message(role="system", content="you are"), Message(role="user", content="hi")]
        result = req.set_messages(new_messages)
        assert len(result.messages) == 2
        assert result.messages[0].role == "system"

    def test_to_dict_filters_none(self):
        req = ChatRequest(
            model="gpt-4",
            messages=[Message(role="user", content="hi")],
            temperature=0.7,
        )
        result = req.to_dict()
        assert result["model"] == "gpt-4"
        assert result["temperature"] == 0.7
        assert "max_tokens" not in result


class TestChatResponse:

    def test_from_error(self):
        resp = ChatResponse.from_error("Oops")
        assert resp.id == "error"
        assert resp.content == "Oops"

    def test_content_from_choices(self):
        resp = ChatResponse(choices=[
            ChatChoice(message=Message(role="assistant", content="answer"))
        ])
        assert resp.content == "answer"

    def test_content_empty_when_no_choices(self):
        resp = ChatResponse()
        assert resp.content == ""

    def test_to_dict(self):
        resp = ChatResponse(
            id="id-1",
            model="gpt-4",
            choices=[ChatChoice(message=Message(role="assistant", content="hi"))],
        )
        d = resp.to_dict()
        assert d["id"] == "id-1"
        assert d["model"] == "gpt-4"
        assert d["object"] == "chat.completion"
        assert len(d["choices"]) == 1


class TestMemory:

    def test_create_from_dict(self):
        mem = Memory.create({"user_id": "u", "fact": "имя: Алекс", "embedding": [0.1, 0.2]})
        assert mem.user_id == "u"
        assert mem.fact == "имя: Алекс"
        assert mem.embedding == [0.1, 0.2]

    def test_oid_none_without_model(self):
        mem = Memory(user_id="u", fact="test")
        assert mem.oid is None

    def test_to_dict(self):
        mem = Memory(user_id="u", fact="имя: Алекс")
        d = mem.to_dict()
        assert d["user_id"] == "u"
        assert d["fact"] == "имя: Алекс"
        assert d["source"] == "chat"

    def test_set_fact_unchanged(self):
        mem = Memory(fact="hi")
        assert mem.set_fact("hi") is mem

    def test_set_fact_changed(self):
        mem = Memory(fact="hi")
        assert mem.set_fact("hello").fact == "hello"

    def test_set_embedding(self):
        mem = Memory()
        result = mem.set_embedding([0.1, 0.2])
        assert result.embedding == [0.1, 0.2]


class TestFileContext:

    def test_create_from_dict(self):
        ctx = FileContext.create({
            "filename": "test.txt",
            "chunks": ["a", "b"],
            "embeddings": [[0.1], [0.2]],
        })
        assert ctx.filename == "test.txt"
        assert ctx.chunks == ["a", "b"]
        assert ctx.embeddings == [[0.1], [0.2]]

    def test_oid_none_without_model(self):
        ctx = FileContext(filename="f.txt")
        assert ctx.oid is None

    def test_to_dict(self):
        ctx = FileContext(filename="f.txt", chunks=["text"], embeddings=[[0.5]])
        d = ctx.to_dict()
        assert d["filename"] == "f.txt"
        assert d["chunks"] == ["text"]
        assert d["embeddings"] == [[0.5]]


class TestRoutingResult:

    def test_create(self):
        result = RoutingResult(model="gpt-4", model_type=MODEL_TYPE.TEXT, auto_routed=True)
        assert result.model == "gpt-4"
        assert result.model_type is MODEL_TYPE.TEXT


class TestGeneratedImage:

    def test_create(self):
        img = GeneratedImage.create({
            "url": "https://example.com/img.png",
            "b64_json": None,
            "revised_prompt": "a cat",
        })
        assert img.url == "https://example.com/img.png"
        assert img.revised_prompt == "a cat"


class TestWebPage:

    def test_create(self):
        page = WebPage.create({"url": "https://a.com", "title": "Title", "text": "Body"})
        assert page.url == "https://a.com"
        assert page.title == "Title"
