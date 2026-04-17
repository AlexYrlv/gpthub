from __future__ import annotations

import pytest

from gpthub.structures import ChatRequest, Message
from gpthub.utils import chunk_text, cosine_similarity


class TestCosineSimilarity:

    def test_identical_vectors(self):
        a = [1.0, 2.0, 3.0]
        assert cosine_similarity(a, a) == pytest.approx(1.0)

    def test_orthogonal_vectors(self):
        assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)

    def test_opposite_vectors(self):
        assert cosine_similarity([1.0, 0.0], [-1.0, 0.0]) == pytest.approx(-1.0)

    def test_empty_vectors(self):
        assert cosine_similarity([], []) == 0.0

    def test_zero_vectors(self):
        assert cosine_similarity([0.0, 0.0], [1.0, 1.0]) == 0.0

    def test_different_lengths(self):
        assert cosine_similarity([1.0, 2.0], [1.0, 2.0, 3.0]) == 0.0


class TestChunkText:

    def test_short_text_single_chunk(self):
        assert chunk_text("hello", size=100, overlap=10) == ["hello"]

    def test_empty_text(self):
        assert chunk_text("", size=100, overlap=10) == []

    def test_exact_size(self):
        text = "a" * 50
        assert chunk_text(text, size=50, overlap=10) == [text]

    def test_chunking_with_overlap(self):
        text = "a" * 100
        chunks = chunk_text(text, size=40, overlap=10)
        assert len(chunks) >= 2
        assert all(len(c) <= 40 for c in chunks)


class TestWithContext:

    def test_empty_context_returns_same_request(self):
        request = ChatRequest(messages=[Message(role="user", content="hi")])
        assert request.with_context("") is request

    def test_adds_system_message_if_missing(self):
        request = ChatRequest(messages=[Message(role="user", content="hi")])
        result = request.with_context("\nContext: test")

        assert len(result.messages) == 2
        assert result.messages[0].role == "system"
        assert "Context: test" in result.messages[0].text
        assert result.messages[1].role == "user"

    def test_extends_existing_system_message(self):
        request = ChatRequest(messages=[
            Message(role="system", content="You are helpful."),
            Message(role="user", content="hi"),
        ])
        result = request.with_context("\nExtra context")

        assert len(result.messages) == 2
        assert "You are helpful." in result.messages[0].text
        assert "Extra context" in result.messages[0].text
