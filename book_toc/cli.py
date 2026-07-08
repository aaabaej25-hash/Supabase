import argparse
import os
import re
from datetime import date

from book_toc.analyzer import generate_toc, render_markdown
from book_toc.config import load_config
from book_toc.yes24 import Yes24Error, collect_books

PREVIEW_LINES = 20


def _sanitize_filename(topic: str) -> str:
    return re.sub(r'[\\/:*?"<>|\s]+', "_", topic.strip()).strip("_")


def run(topic: str, config_path: str = "config.toml") -> str:
    cfg = load_config(config_path)
    print(f'"{topic}" 베스트셀러를 검색합니다...')
    books = collect_books(topic, count=cfg.book_count)
    if len(books) < 2:
        raise Yes24Error(
            "목차를 확인할 수 있는 책이 2권 미만입니다. 더 일반적인 키워드를 시도해보세요."
        )
    print(f"{len(books)}권 수집 완료. 목차를 생성합니다... (Ollama {cfg.ollama_model})")
    toc_text = generate_toc(topic, books, cfg.ollama_model)
    md = render_markdown(topic, toc_text, books)

    os.makedirs(cfg.output_dir, exist_ok=True)
    filename = f"{_sanitize_filename(topic)}_{date.today():%Y%m%d}.md"
    path = os.path.join(cfg.output_dir, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(md)
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="book_toc", description="주제를 입력하면 베스트셀러 분석 기반 목차를 추천합니다."
    )
    parser.add_argument("topic", help='책 주제 (예: "재테크 입문")')
    parser.add_argument("--config", default="config.toml", help="config.toml 경로")
    args = parser.parse_args(argv)

    try:
        path = run(args.topic, config_path=args.config)
    except (Yes24Error, RuntimeError) as e:
        print(str(e))
        return 1

    print(f"\n저장 완료: {path}\n")
    with open(path, encoding="utf-8") as f:
        lines = f.read().splitlines()
    print("\n".join(lines[:PREVIEW_LINES]))
    if len(lines) > PREVIEW_LINES:
        print("...")
    return 0
