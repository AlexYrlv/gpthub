from __future__ import annotations

from hamcrest import (
    assert_that,
    contains_exactly,
    contains_string,
    empty,
    has_entries,
    has_key,
    has_length,
    is_,
    is_not,
    none,
    same_instance,
)

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
        assert_that(msg.role, is_(""))
        assert_that(msg.content, is_(""))

    def test_create_from_dict(self):
        msg = Message.create({"role": "user", "content": "hi"})
        assert_that(msg.role, is_("user"))
        assert_that(msg.content, is_("hi"))

    def test_text_from_string(self):
        msg = Message(role="user", content="hello")
        assert_that(msg.text, is_("hello"))

    def test_text_from_multimodal_content(self):
        msg = Message(
            role="user",
            content=[
                {"type": "text", "text": "Describe this"},
                {"type": "image_url", "image_url": {"url": "data:..."}},
            ],
        )
        assert_that(msg.text, is_("Describe this"))
        assert_that(msg.has_image, is_(True))

    def test_has_image_false_for_text(self):
        msg = Message(role="user", content="just text")
        assert_that(msg.has_image, is_(False))

    def test_set_content_returns_same_when_unchanged(self):
        msg = Message(role="user", content="hi")
        assert_that(msg.set_content("hi"), is_(same_instance(msg)))

    def test_set_content_returns_new_when_changed(self):
        msg = Message(role="user", content="hi")
        new_msg = msg.set_content("hello")
        assert_that(new_msg, is_not(same_instance(msg)))
        assert_that(new_msg.content, is_("hello"))
        assert_that(msg.content, is_("hi"))

    def test_to_dict(self):
        msg = Message(role="assistant", content="response")
        assert_that(msg.to_dict(), is_({"role": "assistant", "content": "response"}))


class TestChatRequest:

    def test_create_empty(self):
        req = ChatRequest.create({})
        assert_that(req.messages, is_(empty()))
        assert_that(req.model, is_(""))

    def test_create_from_dict(self):
        req = ChatRequest.create({
            "model": "gpt-4",
            "messages": [{"role": "user", "content": "hi"}],
            "temperature": 0.5,
            "stream": True,
        })
        assert_that(req.model, is_("gpt-4"))
        assert_that(req.messages, has_length(1))
        assert_that(req.messages[0].role, is_("user"))
        assert_that(req.temperature, is_(0.5))
        assert_that(req.stream, is_(True))

    def test_last_message_empty(self):
        req = ChatRequest()
        assert_that(req.last_message, is_(none()))
        assert_that(req.last_text, is_(""))

    def test_last_message_and_text(self):
        req = ChatRequest(messages=[
            Message(role="user", content="first"),
            Message(role="user", content="second"),
        ])
        assert_that(req.last_message.content, is_("second"))
        assert_that(req.last_text, is_("second"))

    def test_has_image_false(self):
        req = ChatRequest(messages=[Message(role="user", content="text")])
        assert_that(req.has_image, is_(False))

    def test_has_image_true_with_multimodal(self):
        req = ChatRequest(messages=[
            Message(
                role="user",
                content=[
                    {"type": "text", "text": "what"},
                    {"type": "image_url", "image_url": {"url": "data:..."}},
                ],
            ),
        ])
        assert_that(req.has_image, is_(True))

    def test_set_model_returns_same_when_unchanged(self):
        req = ChatRequest(model="a")
        assert_that(req.set_model("a"), is_(same_instance(req)))

    def test_set_model_returns_new_when_changed(self):
        req = ChatRequest(model="a")
        assert_that(req.set_model("b").model, is_("b"))

    def test_set_messages(self):
        req = ChatRequest(messages=[Message(role="user", content="hi")])
        new_messages = [Message(role="system", content="you are"), Message(role="user", content="hi")]
        result = req.set_messages(new_messages)
        assert_that(result.messages, has_length(2))
        assert_that(result.messages[0].role, is_("system"))

    def test_to_dict_filters_none(self):
        req = ChatRequest(
            model="gpt-4",
            messages=[Message(role="user", content="hi")],
            temperature=0.7,
        )
        result = req.to_dict()
        assert_that(result, has_entries({"model": "gpt-4", "temperature": 0.7}))
        assert_that(result, is_not(has_key("max_tokens")))


class TestChatResponse:

    def test_from_error(self):
        resp = ChatResponse.from_error("Oops")
        assert_that(resp.id, is_("error"))
        assert_that(resp.content, is_("Oops"))

    def test_content_from_choices(self):
        resp = ChatResponse(choices=[
            ChatChoice(message=Message(role="assistant", content="answer")),
        ])
        assert_that(resp.content, is_("answer"))

    def test_content_empty_when_no_choices(self):
        resp = ChatResponse()
        assert_that(resp.content, is_(""))

    def test_to_dict(self):
        resp = ChatResponse(
            id="id-1",
            model="gpt-4",
            choices=[ChatChoice(message=Message(role="assistant", content="hi"))],
        )
        d = resp.to_dict()
        assert_that(d, has_entries({"id": "id-1", "model": "gpt-4", "object": "chat.completion"}))
        assert_that(d["choices"], has_length(1))


class TestMemory:

    def test_create_from_dict(self):
        mem = Memory.create({"user_id": "u", "fact": "имя: Алекс", "embedding": [0.1, 0.2]})
        assert_that(mem.user_id, is_("u"))
        assert_that(mem.fact, is_("имя: Алекс"))
        assert_that(mem.embedding, contains_exactly(0.1, 0.2))

    def test_oid_none_without_model(self):
        mem = Memory(user_id="u", fact="test")
        assert_that(mem.oid, is_(none()))

    def test_to_dict(self):
        mem = Memory(user_id="u", fact="имя: Алекс")
        assert_that(mem.to_dict(), has_entries({"user_id": "u", "fact": "имя: Алекс", "source": "chat"}))

    def test_set_fact_unchanged(self):
        mem = Memory(fact="hi")
        assert_that(mem.set_fact("hi"), is_(same_instance(mem)))

    def test_set_fact_changed(self):
        mem = Memory(fact="hi")
        assert_that(mem.set_fact("hello").fact, is_("hello"))

    def test_set_embedding(self):
        mem = Memory()
        assert_that(mem.set_embedding([0.1, 0.2]).embedding, contains_exactly(0.1, 0.2))


class TestFileContext:

    def test_create_from_dict(self):
        ctx = FileContext.create({
            "filename": "test.txt",
            "chunks": ["a", "b"],
            "embeddings": [[0.1], [0.2]],
        })
        assert_that(ctx.filename, is_("test.txt"))
        assert_that(ctx.chunks, contains_exactly("a", "b"))
        assert_that(ctx.embeddings, contains_exactly([0.1], [0.2]))

    def test_oid_none_without_model(self):
        ctx = FileContext(filename="f.txt")
        assert_that(ctx.oid, is_(none()))

    def test_to_dict(self):
        ctx = FileContext(filename="f.txt", chunks=["text"], embeddings=[[0.5]])
        assert_that(ctx.to_dict(), has_entries({"filename": "f.txt", "chunks": ["text"], "embeddings": [[0.5]]}))


class TestRoutingResult:

    def test_create(self):
        result = RoutingResult(model="gpt-4", model_type=MODEL_TYPE.TEXT, auto_routed=True)
        assert_that(result.model, is_("gpt-4"))
        assert_that(result.model_type, is_(MODEL_TYPE.TEXT))


class TestGeneratedImage:

    def test_create(self):
        img = GeneratedImage.create({
            "url": "https://example.com/img.png",
            "b64_json": None,
            "revised_prompt": "a cat",
        })
        assert_that(img.url, is_("https://example.com/img.png"))
        assert_that(img.revised_prompt, is_("a cat"))


class TestWebPage:

    def test_create(self):
        page = WebPage.create({"url": "https://a.com", "title": "Title", "text": "Body"})
        assert_that(page.url, is_("https://a.com"))
        assert_that(page.title, is_("Title"))


class TestWithContext:

    def test_empty_context_returns_same_request(self):
        request = ChatRequest(messages=[Message(role="user", content="hi")])
        assert_that(request.with_context(""), is_(same_instance(request)))

    def test_adds_system_message_if_missing(self):
        request = ChatRequest(messages=[Message(role="user", content="hi")])
        result = request.with_context("\nContext: test")

        assert_that(result.messages, has_length(2))
        assert_that(result.messages[0].role, is_("system"))
        assert_that(result.messages[0].text, contains_string("Context: test"))
        assert_that(result.messages[1].role, is_("user"))

    def test_extends_existing_system_message(self):
        request = ChatRequest(messages=[
            Message(role="system", content="You are helpful."),
            Message(role="user", content="hi"),
        ])
        result = request.with_context("\nExtra context")

        assert_that(result.messages, has_length(2))
        assert_that(result.messages[0].text, contains_string("You are helpful."))
        assert_that(result.messages[0].text, contains_string("Extra context"))
