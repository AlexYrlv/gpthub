from __future__ import annotations

from hamcrest import (
    assert_that,
    close_to,
    contains_exactly,
    empty,
    every_item,
    greater_than_or_equal_to,
    has_length,
    is_,
    less_than_or_equal_to,
)
from pytest import mark

from gpthub.utils import chunk_text, cosine_similarity


class TestCosineSimilarity:

    @mark.parametrize(
        ("a", "b", "expected"),
        [
            ([1.0, 2.0, 3.0], [1.0, 2.0, 3.0], 1.0),
            ([1.0, 0.0], [0.0, 1.0], 0.0),
            ([1.0, 0.0], [-1.0, 0.0], -1.0),
            ([], [], 0.0),
            ([0.0, 0.0], [1.0, 1.0], 0.0),
            ([1.0, 2.0], [1.0, 2.0, 3.0], 0.0),
        ],
    )
    def test_cosine_similarity(self, a, b, expected):
        assert_that(cosine_similarity(a, b), is_(close_to(expected, 1e-6)))


class TestChunkText:

    def test_short_text_single_chunk(self):
        assert_that(chunk_text("hello", size=100, overlap=10), contains_exactly("hello"))

    def test_empty_text(self):
        assert_that(chunk_text("", size=100, overlap=10), is_(empty()))

    def test_exact_size(self):
        text = "a" * 50
        assert_that(chunk_text(text, size=50, overlap=10), contains_exactly(text))

    def test_chunking_with_overlap(self):
        chunks = chunk_text("a" * 100, size=40, overlap=10)
        assert_that(chunks, has_length(greater_than_or_equal_to(2)))
        assert_that(chunks, every_item(has_length(less_than_or_equal_to(40))))
