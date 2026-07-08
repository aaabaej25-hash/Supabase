import pytest

from book_toc.yes24 import Yes24Error, collect_books

SEARCH_HTML = """
<ul id="yesSchList">
  <li><a class="gd_name" href="/Product/Goods/1">책1</a></li>
  <li><a class="gd_name" href="/Product/Goods/2">책2</a></li>
  <li><a class="gd_name" href="/Product/Goods/3">책3</a></li>
</ul>
"""

NO_RESULT_HTML = '<ul id="yesSchList"></ul><div class="srch_no_result">검색결과가 없습니다</div>'


def detail_html(title, toc):
    toc_div = f'<div id="infoset_toc"><textarea class="txtContentText">{toc}</textarea></div>' if toc else ""
    return f"""
    <h2 class="gd_name">{title}</h2>
    <span class="gd_auth"><a href="#">저자</a></span>
    <div id="infoset_introduce"><textarea class="txtContentText">소개</textarea></div>
    {toc_div}
    """


class FakeResponse:
    def __init__(self, text, status=200):
        self.text = text
        self.status = status

    def raise_for_status(self):
        if self.status >= 400:
            raise RuntimeError(f"HTTP {self.status}")


class FakeClient:
    def __init__(self, pages):
        self.pages = pages  # url -> FakeResponse
        self.requested = []

    def get(self, url, **kwargs):
        self.requested.append(url)
        if url not in self.pages:
            raise RuntimeError("연결 실패")
        return self.pages[url]


def test_collect_books_skips_books_without_toc():
    client = FakeClient({
        "https://www.yes24.com/Product/Goods/1": FakeResponse(detail_html("책1", "")),
        "https://www.yes24.com/Product/Goods/2": FakeResponse(detail_html("책2", "1장")),
        "https://www.yes24.com/Product/Goods/3": FakeResponse(detail_html("책3", "1장")),
    })
    client.pages["SEARCH"] = FakeResponse(SEARCH_HTML)
    # collect_books는 검색 URL을 SEARCH_URL로 시작하는 하나의 GET으로 호출
    orig_get = client.get

    def get(url, **kwargs):
        if url.startswith("https://www.yes24.com/Product/Search"):
            return client.pages["SEARCH"]
        return orig_get(url, **kwargs)

    client.get = get
    books = collect_books("재테크", count=2, delay=0, client=client)
    assert [b.title for b in books] == ["책2", "책3"]


def test_collect_books_no_search_results_raises():
    class C:
        def get(self, url, **kwargs):
            return FakeResponse(NO_RESULT_HTML)

    with pytest.raises(Yes24Error, match="검색 결과가 없습니다"):
        collect_books("ㅁㄴㅇㄹ없는주제", delay=0, client=C())


def test_collect_books_skips_failed_detail_pages():
    client = FakeClient({
        # Goods/1 은 pages에 없어서 get이 예외 발생 → 건너뜀
        "https://www.yes24.com/Product/Goods/2": FakeResponse(detail_html("책2", "1장")),
        "https://www.yes24.com/Product/Goods/3": FakeResponse(detail_html("책3", "1장")),
    })
    orig_get = client.get

    def get(url, **kwargs):
        if url.startswith("https://www.yes24.com/Product/Search"):
            return FakeResponse(SEARCH_HTML)
        return orig_get(url, **kwargs)

    client.get = get
    books = collect_books("재테크", count=5, delay=0, client=client)
    assert [b.title for b in books] == ["책2", "책3"]
