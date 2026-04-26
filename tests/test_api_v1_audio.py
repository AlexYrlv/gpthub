from __future__ import annotations

from unittest.mock import AsyncMock, patch

from hamcrest import assert_that, has_entries, is_
from pytest import mark

from gpthub.controls import AudioControl
from gpthub.structures import TranscriptionResult

from tests.constants import URL_AUDIO
from tests.mocks import MockStack

pytestmark = mark.configuration({"app": {}})


class TestAudioTranscriptionsPost:

    def test_ok(self, client):
        result = TranscriptionResult(text="Hello world", model="whisper-1")
        stack = MockStack(
            transcribe=patch.object(
                AudioControl, "transcribe", new_callable=AsyncMock, return_value=result,
            ),
        )
        with stack.activate() as mocks:  # noqa: F841
            response = client.post(
                URL_AUDIO,
                files={"file": ("audio.mp3", b"fake-audio-bytes", "audio/mpeg")},
                data={"model": "whisper-1"},
            )

        assert_that(response.status_code, is_(200))
        assert_that(response.json(), has_entries({"text": "Hello world", "model": "whisper-1"}))

    def test_no_file_returns_400(self, client):
        response = client.post(URL_AUDIO, data={"model": "whisper-1"})
        assert_that(response.status_code, is_(400))
