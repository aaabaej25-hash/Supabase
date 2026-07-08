from datetime import date

from book_toc.models import Book
from book_toc.ollama_client import ollama_chat

MAX_INTRO_CHARS = 500
MAX_TOC_CHARS = 2000

PROMPT_TEMPLATE = """당신은 출판 기획 전문가입니다. 아래는 "{topic}" 주제의 베스트셀러 {n}권의 소개와 목차입니다.

{books_block}

위 자료를 근거로 다음 형식의 한국어 마크다운으로만 답하세요.

## 베스트셀러 공통 패턴
(위 책들의 목차 구성 방식에서 발견한 공통점 3~5개를 불릿으로)

## 추천 목차
"{topic}" 주제로 새 책을 쓴다고 할 때의 목차. 부/장/절 구조로 작성.
각 장 제목 아래에 `> 근거:` 한 줄로 어떤 책의 어떤 패턴을 참고했는지 명시.
"""


def build_prompt(topic: str, books: list[Book]) -> str:
    blocks = []
    for i, b in enumerate(books, 1):
        blocks.append(
            f"### {i}. {b.title} — {b.author}\n"
            f"[소개]\n{b.intro[:MAX_INTRO_CHARS]}\n"
            f"[목차]\n{b.toc[:MAX_TOC_CHARS]}"
        )
    return PROMPT_TEMPLATE.format(topic=topic, n=len(books), books_block="\n\n".join(blocks))


def generate_toc(topic: str, books: list[Book], model: str) -> str:
    return ollama_chat(model, build_prompt(topic, books))


def render_markdown(topic: str, toc_text: str, books: list[Book]) -> str:
    refs = "\n".join(
        f"- [{b.title}]({b.url}) — {b.author}" for b in books
    )
    return (
        f"# {topic} — 목차 추천\n\n"
        f"- 생성일: {date.today().isoformat()}\n"
        f"- 분석: 예스24 판매량순 베스트셀러 {len(books)}권 기준\n\n"
        f"{toc_text}\n\n"
        f"## 참고 도서\n\n{refs}\n"
    )
