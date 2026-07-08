import time

import httpx
from bs4 import BeautifulSoup

from book_toc.models import Book

BASE_URL = "https://www.yes24.com"
SEARCH_URL = BASE_URL + "/Product/Search"

# 검색 결과 없음 페이지에서 관찰되는 마커.
# 실제 예스24 0건 페이지에는 #yesSchList 자체가 없고
# <div class="noData ..."> 안에 "검색결과가 없습니다" 문구가 나온다. (Step 1에서 curl로 확인)
NO_RESULT_MARKERS = ["검색결과가 없습니다", "noData"]

STRUCTURE_CHANGED_MSG = (
    "예스24 페이지 구조가 변경된 것 같습니다. book_toc/yes24.py의 셀렉터를 확인하세요."
)


class Yes24Error(Exception):
    """검색 0건, 페이지 구조 변경, 네트워크 오류 등 예스24 수집 실패."""


def parse_search_results(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    container = soup.select_one("#yesSchList")
    if container is None:
        if any(marker in html for marker in NO_RESULT_MARKERS):
            return []
        raise Yes24Error(STRUCTURE_CHANGED_MSG)
    urls = []
    for a in container.select("a.gd_name"):
        href = a.get("href", "")
        if href.startswith("/"):
            urls.append(BASE_URL + href)
    return urls


def _section_text(soup: BeautifulSoup, section_id: str) -> str:
    section = soup.select_one(f"#{section_id}")
    if section is None:
        return ""
    node = section.select_one("textarea.txtContentText") or section
    raw = node.get_text("\n", strip=True)
    # 예스24는 textarea 안에 HTML을 넣어두므로 한 번 더 파싱해 태그 제거
    return BeautifulSoup(raw, "html.parser").get_text("\n", strip=True)


def parse_book_detail(html: str, url: str) -> Book:
    soup = BeautifulSoup(html, "html.parser")
    title_el = soup.select_one("h2.gd_name")
    author_el = soup.select_one("span.gd_auth a")
    return Book(
        title=title_el.get_text(strip=True) if title_el else "",
        author=author_el.get_text(strip=True) if author_el else "",
        intro=_section_text(soup, "infoset_introduce"),
        toc=_section_text(soup, "infoset_toc"),
        url=url,
    )


USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"


def _fetch(client, url: str) -> str:
    resp = client.get(url, headers={"User-Agent": USER_AGENT}, follow_redirects=True)
    resp.raise_for_status()
    return resp.text


def collect_books(
    topic: str,
    count: int = 5,
    max_try: int = 15,
    delay: float = 1.0,
    client=None,
) -> list[Book]:
    own_client = client is None
    if own_client:
        client = httpx.Client(timeout=15)
    try:
        search_url = httpx.URL(
            SEARCH_URL, params={"domain": "BOOK", "query": topic, "order": "SALE_WEIGHT"}
        )
        try:
            search_html = _fetch(client, str(search_url))
        except Exception as e:
            raise Yes24Error(f"예스24 검색 요청 실패: {e}") from e

        urls = parse_search_results(search_html)
        if not urls:
            raise Yes24Error("검색 결과가 없습니다. 더 일반적인 키워드를 시도해보세요.")

        books: list[Book] = []
        for url in urls[:max_try]:
            if len(books) >= count:
                break
            # 요청 간 대기: 성공/실패와 무관하게 매 상세 요청 전에 적용
            # (루프의 첫 반복에서는 검색 요청과 첫 상세 요청 사이의 대기 역할도 함)
            if delay:
                time.sleep(delay)
            try:
                html = _fetch(client, url)
                book = parse_book_detail(html, url)
            except Yes24Error:
                raise
            except Exception:
                continue  # 개별 책 실패는 건너뜀
            if book.toc.strip():
                books.append(book)
        return books
    finally:
        if own_client:
            client.close()
