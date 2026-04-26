from __future__ import annotations

from unittest.mock import AsyncMock, patch

from hamcrest import assert_that, has_entries, is_
from pytest import mark

from gpthub.controls import FileControl
from gpthub.structures import FileContext

from tests.constants import URL_FILES, USER_ID
from tests.mocks import MockStack

pytestmark = mark.configuration({"app": {}})


class TestFilesPost:

    def test_ok(self, client):
        ctx = FileContext(
            user_id=USER_ID,
            filename="doc.txt",
            content_type="text/plain",
            chunks=["chunk1", "chunk2", "chunk3"],
        )
        stack = MockStack(
            ingest=patch.object(
                FileControl, "ingest", new_callable=AsyncMock, return_value=ctx,
            ),
        )
        with stack.activate() as mocks:  # noqa: F841
            response = client.post(
                URL_FILES,
                files={"file": ("doc.txt", b"hello world", "text/plain")},
                headers={"x-openwebui-user-id": USER_ID},
            )

        assert_that(response.status_code, is_(201))
        assert_that(response.json(), has_entries({
            "filename": "doc.txt",
            "chunks": 3,
            "status": "processed",
        }))

    def test_no_file_returns_400(self, client):
        response = client.post(URL_FILES, headers={"x-openwebui-user-id": USER_ID})
        assert_that(response.status_code, is_(400))
