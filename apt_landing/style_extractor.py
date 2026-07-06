import re
from collections import Counter

import httpx
from bs4 import BeautifulSoup

from .models import DEFAULT_SECTION_ORDER, StyleGuide
from .ollama_client import ollama_chat

_HEX_RE = re.compile(r"#[0-9a-fA-F]{6}\b")

# 회색조(채도 낮음)·순백/순흑 계열은 브랜드 색이 아니므로 제외
def _is_chromatic(hex_color: str) -> bool:
    r, g, b = (int(hex_color[i : i + 2], 16) for i in (1, 3, 5))
    return (max(r, g, b) - min(r, g, b)) >= 24


_SECTION_KEYWORDS = {
    "info": ["세대", "평형", "가격", "타입", "분양가", "공급"],
    "location": ["입지", "위치", "교통", "학군", "인프라"],
    "gallery": ["갤러리", "사진", "전경", "조감도", "투시도"],
}

_TONE_PROMPT = (
    "다음은 부동산 랜딩페이지의 텍스트입니다. 이 카피의 톤(분위기)을 "
    "한국어 한 문장으로 요약하세요. 문장만 출력하세요.\n\n{text}"
)


def _fetch(url: str) -> str:
    resp = httpx.get(url, timeout=15, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()
    return resp.text


def _extract_colors(html: str) -> list[str]:
    counts = Counter(c.lower() for c in _HEX_RE.findall(html) if _is_chromatic(c.lower()))
    return [c for c, _ in counts.most_common(2)]


def _guess_section_order(soup: BeautifulSoup) -> list[str]:
    order = []
    for h in soup.find_all(["h1", "h2", "h3"]):
        text = h.get_text()
        for section, keywords in _SECTION_KEYWORDS.items():
            if section not in order and any(k in text for k in keywords):
                order.append(section)
    order += [s for s in DEFAULT_SECTION_ORDER if s not in order]
    return order


def extract_style(url: str, model: str, chat=ollama_chat, fetch=None) -> StyleGuide:
    try:
        html = (fetch or _fetch)(url)
        colors = _extract_colors(html)
        if not colors:
            return StyleGuide()  # 추출 빈약 → 폴백
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(" ", strip=True)[:2000]
        tone = chat(model, _TONE_PROMPT.format(text=text)).strip() or StyleGuide().tone
        return StyleGuide(
            primary_color=colors[0],
            accent_color=colors[1] if len(colors) > 1 else StyleGuide().accent_color,
            section_order=_guess_section_order(soup),
            tone=tone,
            extracted=True,
        )
    except Exception:
        return StyleGuide()  # 어떤 실패든 기본 스타일 폴백 (UI가 extracted로 표시)
