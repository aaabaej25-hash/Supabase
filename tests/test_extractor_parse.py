import pytest
from youtube_summarizer.extractor import parse_video_id


@pytest.mark.parametrize("url,expected", [
    ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
    ("https://youtu.be/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
    ("https://www.youtube.com/shorts/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
    ("https://youtube.com/watch?v=dQw4w9WgXcQ&t=10s", "dQw4w9WgXcQ"),
])
def test_parse_valid_urls(url, expected):
    assert parse_video_id(url) == expected


def test_parse_invalid_url_raises():
    with pytest.raises(ValueError):
        parse_video_id("https://example.com/notyoutube")
