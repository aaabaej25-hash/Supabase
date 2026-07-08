from unittest.mock import patch

import pytest

from book_toc.cli import main, run
from book_toc.models import Book
from book_toc.yes24 import Yes24Error

BOOKS = [
    Book(title="책1", author="저자1", intro="소개1", toc="1장", url="https://www.yes24.com/Product/Goods/1"),
    Book(title="책2", author="저자2", intro="소개2", toc="1부", url="https://www.yes24.com/Product/Goods/2"),
]


def _config(tmp_path):
    p = tmp_path / "config.toml"
    p.write_text(
        f"[book_toc]\noutput_dir = '{str(tmp_path / 'out').replace(chr(92), '/')}'\n",
        encoding="utf-8",
    )
    return str(p)


def test_run_saves_markdown_and_returns_path(tmp_path):
    cfg = _config(tmp_path)
    with patch("book_toc.cli.collect_books", return_value=BOOKS), \
         patch("book_toc.cli.generate_toc", return_value="## 추천 목차\n1장 시작"):
        path = run("재테크 입문", config_path=cfg)
    with open(path, encoding="utf-8") as f:
        content = f.read()
    assert "재테크 입문" in content
    assert "## 추천 목차" in content
    assert "책1" in content
    assert path.endswith(".md")


def test_run_sanitizes_topic_in_filename(tmp_path):
    cfg = _config(tmp_path)
    with patch("book_toc.cli.collect_books", return_value=BOOKS), \
         patch("book_toc.cli.generate_toc", return_value="목차"):
        path = run("재테크: 입문/기초", config_path=cfg)
    assert ":" not in path.split("out")[-1]
    assert "/" not in path.split("out")[-1].replace("\\", "")


def test_run_fewer_than_two_books_raises(tmp_path):
    cfg = _config(tmp_path)
    with patch("book_toc.cli.collect_books", return_value=BOOKS[:1]):
        with pytest.raises(Yes24Error, match="2권 미만"):
            run("희귀한 주제", config_path=cfg)


def test_main_returns_1_and_prints_message_on_error(tmp_path, capsys):
    with patch("book_toc.cli.collect_books", side_effect=Yes24Error("검색 결과가 없습니다.")):
        code = main(["없는주제"])
    assert code == 1
    assert "검색 결과가 없습니다" in capsys.readouterr().out


def test_main_success_prints_path(tmp_path, capsys):
    cfg = _config(tmp_path)
    with patch("book_toc.cli.collect_books", return_value=BOOKS), \
         patch("book_toc.cli.generate_toc", return_value="## 추천 목차"):
        code = main(["재테크", "--config", cfg])
    assert code == 0
    assert ".md" in capsys.readouterr().out
