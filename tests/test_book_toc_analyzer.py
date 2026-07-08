from unittest.mock import patch

from book_toc.analyzer import build_prompt, generate_toc, render_markdown
from book_toc.models import Book

BOOKS = [
    Book(title="책1", author="저자1", intro="소개1", toc="1장 돈\n2장 투자", url="https://www.yes24.com/Product/Goods/1"),
    Book(title="책2", author="저자2", intro="소개2", toc="1부 기초\n2부 실전", url="https://www.yes24.com/Product/Goods/2"),
]


def test_build_prompt_contains_topic_and_all_books():
    prompt = build_prompt("재테크 입문", BOOKS)
    assert "재테크 입문" in prompt
    for book in BOOKS:
        assert book.title in prompt
        assert book.toc.splitlines()[0] in prompt


def test_generate_toc_passes_prompt_to_ollama():
    with patch("book_toc.analyzer.ollama_chat", return_value="## 추천 목차\n1장") as mock:
        result = generate_toc("재테크 입문", BOOKS, model="llama3.1")
    assert result == "## 추천 목차\n1장"
    model_arg, prompt_arg = mock.call_args[0]
    assert model_arg == "llama3.1"
    assert "재테크 입문" in prompt_arg


def test_render_markdown_includes_toc_and_references():
    md = render_markdown("재테크 입문", "## 추천 목차\n1장 시작", BOOKS)
    assert "# 재테크 입문" in md
    assert "2권 기준" in md
    assert "## 추천 목차" in md
    assert "[책1](https://www.yes24.com/Product/Goods/1)" in md
    assert "저자2" in md
