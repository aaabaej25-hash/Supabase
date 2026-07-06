import pytest

from book_toc.models import Book
from book_toc.yes24 import Yes24Error, parse_book_detail, parse_search_results

# 실제 예스24 검색 결과 페이지(Step 1에서 curl로 확인) 구조를 축약한 픽스처.
# href는 실제로 소문자 /product/goods/{id} 형태로 내려온다.
SEARCH_HTML = """
<html><body>
<ul id="yesSchList">
  <li><a class="gd_name" href="/product/goods/101">부자의 습관</a></li>
  <li><a class="gd_name" href="/product/goods/102">월급쟁이 재테크</a></li>
</ul>
</body></html>
"""

# 실제 0건 검색 결과 페이지에는 #yesSchList 자체가 없고,
# <div class="noData schData"> 안에 "검색결과가 없습니다" 문구가 나온다.
NO_RESULT_HTML = """
<html><body>
<div id="ySchContSec">
<div class="noData schData">
  <p class="txt_tit">"asdkjhqwkjehqwe"에<br/>대한 검색결과가 없습니다.</p>
</div>
</div>
</body></html>
"""

BROKEN_HTML = "<html><body><div>완전히 다른 페이지</div></body></html>"

# 실제 상세 페이지(Step 1에서 curl로 확인) 구조를 축약한 픽스처.
DETAIL_HTML = """
<html><body>
<h2 class="gd_name">부자의 습관</h2>
<span class="gd_auth"><a href="#">김부자</a></span>
<div id="infoset_introduce">
  <textarea class="txtContentText">평범한 직장인이 부자가 되는 법.</textarea>
</div>
<div id="infoset_toc">
  <textarea class="txtContentText">1장 돈의 심리&lt;br/&gt;2장 저축의 기술&lt;br/&gt;3장 투자의 시작</textarea>
</div>
</body></html>
"""

DETAIL_NO_TOC_HTML = """
<html><body>
<h2 class="gd_name">그림책</h2>
<span class="gd_auth"><a href="#">이그림</a></span>
<div id="infoset_introduce">
  <textarea class="txtContentText">아이들을 위한 그림책.</textarea>
</div>
</body></html>
"""


def test_parse_search_results_returns_absolute_urls_in_order():
    urls = parse_search_results(SEARCH_HTML)
    assert urls == [
        "https://www.yes24.com/product/goods/101",
        "https://www.yes24.com/product/goods/102",
    ]


def test_parse_search_results_no_results_returns_empty():
    assert parse_search_results(NO_RESULT_HTML) == []


def test_parse_search_results_broken_page_raises():
    with pytest.raises(Yes24Error, match="구조가 변경"):
        parse_search_results(BROKEN_HTML)


def test_parse_book_detail_extracts_fields():
    book = parse_book_detail(DETAIL_HTML, "https://www.yes24.com/product/goods/101")
    assert book == Book(
        title="부자의 습관",
        author="김부자",
        intro="평범한 직장인이 부자가 되는 법.",
        toc="1장 돈의 심리\n2장 저축의 기술\n3장 투자의 시작",
        url="https://www.yes24.com/product/goods/101",
    )


def test_parse_book_detail_without_toc_returns_empty_toc():
    book = parse_book_detail(DETAIL_NO_TOC_HTML, "https://www.yes24.com/product/goods/103")
    assert book.toc == ""
    assert book.title == "그림책"
