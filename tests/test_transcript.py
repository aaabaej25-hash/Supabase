from unittest.mock import patch
import pytest
from youtube_summarizer.transcript import fetch_transcript, TranscriptResult


def test_uses_captions_when_available():
    with patch("youtube_summarizer.transcript._fetch_captions", return_value="자막 텍스트"):
        result = fetch_transcript("vid", "base")
    assert result == TranscriptResult(text="자막 텍스트", source="자막")


def test_falls_back_to_whisper():
    with patch("youtube_summarizer.transcript._fetch_captions", side_effect=Exception("no captions")), \
         patch("youtube_summarizer.transcript._whisper_transcribe", return_value="전사 텍스트") as w:
        result = fetch_transcript("vid", "base")
    w.assert_called_once_with("vid", "base")
    assert result.source == "음성인식(whisper)"
    assert result.text == "전사 텍스트"


def test_whisper_failure_propagates():
    with patch("youtube_summarizer.transcript._fetch_captions", side_effect=Exception("no captions")), \
         patch("youtube_summarizer.transcript._whisper_transcribe", side_effect=RuntimeError("ffmpeg 없음")):
        with pytest.raises(RuntimeError):
            fetch_transcript("vid", "base")
