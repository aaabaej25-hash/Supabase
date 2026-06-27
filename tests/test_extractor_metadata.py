from unittest.mock import patch
import pytest
from youtube_summarizer.extractor import fetch_metadata, Metadata, _format_duration


def test_format_duration():
    assert _format_duration(75) == "01:15"
    assert _format_duration(3725) == "1:02:05"


def test_fetch_metadata_success():
    fake_info = {"title": "테스트 영상", "uploader": "채널A", "duration": 754}
    with patch("youtube_summarizer.extractor._extract_info", return_value=fake_info):
        md = fetch_metadata("dQw4w9WgXcQ")
    assert isinstance(md, Metadata)
    assert md.title == "테스트 영상"
    assert md.channel == "채널A"
    assert md.duration == "12:34"
    assert md.url == "https://youtu.be/dQw4w9WgXcQ"


def test_fetch_metadata_failure_raises():
    with patch("youtube_summarizer.extractor._extract_info", side_effect=Exception("private")):
        with pytest.raises(RuntimeError):
            fetch_metadata("dQw4w9WgXcQ")
