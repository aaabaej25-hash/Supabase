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
