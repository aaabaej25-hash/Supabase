from unittest.mock import patch
from youtube_summarizer.summarizer import chunk_text, summarize, Summary, Section


def test_chunk_text_splits_by_size():
    text = "word " * 1000  # 5000자
    chunks = chunk_text(text, 1000)
    assert len(chunks) > 1
    assert all(len(c) <= 1100 for c in chunks)  # 단어 경계 여유


def test_chunk_text_short_returns_single():
    chunks = chunk_text("짧은 텍스트", 1000)
    assert chunks == ["짧은 텍스트"]


def test_summarize_builds_summary():
    fake_json = (
        '{"overview": ["핵심1", "핵심2"], '
        '"sections": [{"heading": "도입", "bullets": ["a", "b"]}]}'
    )
    with patch("youtube_summarizer.summarizer._ollama_chat", return_value=fake_json):
        result = summarize("어떤 긴 텍스트", "llama3.1", 1000)
    assert isinstance(result, Summary)
    assert result.overview == ["핵심1", "핵심2"]
    assert result.sections[0] == Section(heading="도입", bullets=["a", "b"])
