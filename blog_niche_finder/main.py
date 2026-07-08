# -*- coding: utf-8 -*-
"""
blog_niche_finder / main.py

경쟁 네이버 블로그 분석 + 틈새 주제 추천 프로그램
실행: python main.py
"""

import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import os
import re
import time
import random
import subprocess
import importlib
from datetime import datetime, timedelta


# ---------------------------------------------------------------------------
# 0. 라이브러리 자동 설치
# ---------------------------------------------------------------------------

REQUIRED_PACKAGES = {
    "feedparser": "feedparser",
    "pandas": "pandas",
    "matplotlib": "matplotlib",
    "wordcloud": "wordcloud",
    "requests": "requests",
    "bs4": "beautifulsoup4",
    "reportlab": "reportlab",
}


def ensure_packages_installed():
    """필요 라이브러리 import 시도, 없으면 pip install 후 재import."""
    missing = []
    for module_name in REQUIRED_PACKAGES:
        try:
            importlib.import_module(module_name)
        except ImportError:
            missing.append(REQUIRED_PACKAGES[module_name])

    if missing:
        print(f"[0/5] 필요한 라이브러리 설치 중... ({', '.join(missing)})")
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", *missing]
            )
        except Exception as e:
            print(f"[경고] 라이브러리 자동 설치 실패: {e}")

        for module_name in REQUIRED_PACKAGES:
            try:
                importlib.import_module(module_name)
            except ImportError as e:
                print(f"[경고] {module_name} 임포트 실패: {e}")
    else:
        print("[0/5] 필요한 라이브러리가 모두 설치되어 있습니다.")


ensure_packages_installed()

import feedparser
import pandas as pd
import requests
from bs4 import BeautifulSoup

import config


# ---------------------------------------------------------------------------
# 1(a). 검색 수집 - 구글 / DuckDuckGo 폴백
# ---------------------------------------------------------------------------

def search_google(keyword, max_results):
    """구글 검색으로 site:blog.naver.com 결과 수집. 실패 시 None 반환."""
    query = f'"{keyword}" site:blog.naver.com'
    params = {
        "q": query,
        "tbs": f"qdr:m{config.SEARCH_RECENT_MONTHS}",
        "num": max_results,
    }
    headers = {"User-Agent": config.USER_AGENT}

    try:
        resp = requests.get(
            "https://www.google.com/search",
            params=params,
            headers=headers,
            timeout=10,
        )
        if resp.status_code == 429:
            print(f"  [구글] 429 차단 감지 (키워드: {keyword})")
            return None
        if resp.status_code != 200:
            print(f"  [구글] 응답 코드 {resp.status_code} (키워드: {keyword})")
            return None
        if "captcha" in resp.text.lower() or "unusual traffic" in resp.text.lower():
            print(f"  [구글] CAPTCHA 감지 (키워드: {keyword})")
            return None

        soup = BeautifulSoup(resp.text, "html.parser")
        results = []
        for g in soup.select("div.g"):
            a_tag = g.find("a", href=True)
            h3_tag = g.find("h3")
            if a_tag and h3_tag:
                url = a_tag["href"]
                title = h3_tag.get_text(strip=True)
                if "blog.naver.com" in url and title:
                    results.append({"title": title, "url": url})
            if len(results) >= max_results:
                break

        if not results:
            print(f"  [구글] 결과 파싱 실패 (키워드: {keyword})")
            return None

        return results
    except Exception as e:
        print(f"  [구글] 요청 실패 (키워드: {keyword}): {e}")
        return None


def search_duckduckgo_html(keyword, max_results):
    """DuckDuckGo HTML 버전 검색 1회 시도. 상태코드와 결과를 튜플로 반환."""
    query = f'"{keyword}" site:blog.naver.com'
    headers = {"User-Agent": config.USER_AGENT}

    resp = requests.post(
        "https://html.duckduckgo.com/html/",
        data={"q": query},
        headers=headers,
        timeout=10,
    )
    if resp.status_code != 200:
        return resp.status_code, None

    soup = BeautifulSoup(resp.text, "html.parser")
    results = []
    for result in soup.select("div.result"):
        a_tag = result.select_one("a.result__a")
        if a_tag:
            url = a_tag.get("href", "")
            title = a_tag.get_text(strip=True)
            if "blog.naver.com" in url and title:
                results.append({"title": title, "url": url})
        if len(results) >= max_results:
            break

    return resp.status_code, (results or None)


def search_duckduckgo_lite(keyword, max_results):
    """DuckDuckGo Lite 버전 검색 폴백. 실패 시 None 반환."""
    query = f'"{keyword}" site:blog.naver.com'
    headers = {"User-Agent": config.USER_AGENT}

    resp = requests.get(
        "https://lite.duckduckgo.com/lite/",
        params={"q": query},
        headers=headers,
        timeout=10,
    )
    if resp.status_code != 200:
        return None

    soup = BeautifulSoup(resp.text, "html.parser")
    results = []
    for a_tag in soup.find_all("a", href=True):
        url = a_tag["href"]
        title = a_tag.get_text(strip=True)
        if "blog.naver.com" in url and title:
            results.append({"title": title, "url": url})
        if len(results) >= max_results:
            break

    return results or None


def search_duckduckgo(keyword, max_results):
    """
    DuckDuckGo 검색으로 site:blog.naver.com 결과 수집. 실패 시 None 반환.
    202(봇 차단) 응답 시 잠시 대기 후 재시도하고, 그래도 실패하면 Lite 버전으로 폴백한다.
    """
    try:
        status, results = search_duckduckgo_html(keyword, max_results)

        if status == 202:
            print(f"  [DuckDuckGo] 202 차단 감지, 잠시 후 재시도 (키워드: {keyword})")
            time.sleep(random.uniform(3, 5))
            status, results = search_duckduckgo_html(keyword, max_results)

        if results:
            return results

        if status != 200:
            print(f"  [DuckDuckGo] 응답 코드 {status} (키워드: {keyword})")
        else:
            print(f"  [DuckDuckGo] 결과 파싱 실패 (키워드: {keyword})")

        print(f"  -> DuckDuckGo Lite로 폴백 시도 (키워드: {keyword})")
        lite_results = search_duckduckgo_lite(keyword, max_results)
        if lite_results:
            return lite_results

        print(f"  [DuckDuckGo Lite] 결과 없음 (키워드: {keyword})")
        return None
    except Exception as e:
        print(f"  [DuckDuckGo] 요청 실패 (키워드: {keyword}): {e}")
        return None


def collect_search_data():
    """키워드별 구글->DuckDuckGo 폴백 검색 수집."""
    rows = []
    total = len(config.SEARCH_KEYWORDS)

    for idx, keyword in enumerate(config.SEARCH_KEYWORDS, start=1):
        print(f"[1/5] 구글 검색 수집 중... ({idx}/{total}) (키워드: {keyword})")
        try:
            results = search_google(keyword, config.SEARCH_RESULTS_PER_KEYWORD)

            if results is None:
                print(f"  -> 구글 실패, DuckDuckGo로 폴백 시도 (키워드: {keyword})")
                time.sleep(random.uniform(config.REQUEST_SLEEP_MIN, config.REQUEST_SLEEP_MAX))
                results = search_duckduckgo(keyword, config.SEARCH_RESULTS_PER_KEYWORD)

            if results is None:
                print(f"[경고] '{keyword}' 검색 실패 (구글/DuckDuckGo 모두 실패), 건너뜁니다.")
                continue

            for r in results:
                rows.append({
                    "source": "search",
                    "keyword_or_blog": keyword,
                    "title": r["title"],
                    "url": r["url"],
                    "date": None,
                })

            print(f"  -> {len(results)}건 수집 완료 (키워드: {keyword})")
        except Exception as e:
            print(f"[경고] '{keyword}' 검색 수집 중 오류 발생, 건너뜁니다: {e}")

        time.sleep(random.uniform(config.REQUEST_SLEEP_MIN, config.REQUEST_SLEEP_MAX))

    return rows


# ---------------------------------------------------------------------------
# 1(b). RSS 수집
# ---------------------------------------------------------------------------

def parse_feed_date(entry):
    """feedparser entry에서 날짜(datetime) 추출, 실패 시 None."""
    for key in ("published_parsed", "updated_parsed"):
        t = entry.get(key)
        if t:
            try:
                return datetime(*t[:6])
            except Exception:
                continue
    return None


def collect_feed_sources(sources, step_label="[2/5] RSS 수집"):
    """
    sources: [(label, feed_url), ...] 목록의 각 피드에서 최근 글을 수집한다.
    RSS_BLOG_IDS 기반 수집과 사용자 제공 링크 기반 수집이 이 함수를 공유한다.
    """
    rows = []
    cutoff = datetime.now() - timedelta(days=config.RSS_RECENT_DAYS)
    total = len(sources)

    for idx, (label, feed_url) in enumerate(sources, start=1):
        print(f"{step_label} 중... ({idx}/{total}) (블로그: {label})")
        try:
            feed = feedparser.parse(feed_url)

            if feed.bozo and not feed.entries:
                print(f"[경고] '{label}' RSS 파싱 실패, 건너뜁니다.")
                continue

            count = 0
            for entry in feed.entries:
                title = entry.get("title", "").strip()
                if not title:
                    continue
                pub_date = parse_feed_date(entry)
                if pub_date is not None and pub_date < cutoff:
                    continue

                rows.append({
                    "source": "rss",
                    "keyword_or_blog": label,
                    "title": title,
                    "url": entry.get("link", ""),
                    "date": pub_date.strftime("%Y-%m-%d") if pub_date else None,
                })
                count += 1

            print(f"  -> {count}건 수집 완료 (블로그: {label})")
        except Exception as e:
            print(f"[경고] '{label}' RSS 수집 중 오류 발생, 건너뜁니다: {e}")

    return rows


def collect_rss_data():
    """RSS_BLOG_IDS의 각 블로그 RSS에서 최근 글 수집."""
    sources = [
        (blog_id, f"https://rss.blog.naver.com/{blog_id}.xml")
        for blog_id in config.RSS_BLOG_IDS
    ]
    return collect_feed_sources(sources, step_label="[2/5] RSS 수집")


NAVER_BLOG_ID_PATTERN = re.compile(
    r"(?:m\.)?blog\.naver\.com/(?:PostView\.naver\?blogId=)?([a-zA-Z0-9_-]+)"
)


def extract_naver_blog_id(url):
    """네이버 블로그 URL에서 블로그 ID를 추출. 실패 시 None."""
    match = NAVER_BLOG_ID_PATTERN.search(url)
    if match:
        return match.group(1)
    return None


def discover_feed_link(url):
    """HTML 페이지에서 <link rel="alternate" type="application/rss+xml"> 피드 주소를 탐색."""
    try:
        resp = requests.get(url, headers={"User-Agent": config.USER_AGENT}, timeout=10)
        if resp.status_code != 200:
            return None
        soup = BeautifulSoup(resp.text, "html.parser")
        link_tag = soup.find("link", attrs={"type": "application/rss+xml"})
        if link_tag and link_tag.get("href"):
            href = link_tag["href"]
            if href.startswith("http"):
                return href
        return None
    except Exception:
        return None


def resolve_link_to_feed_source(url):
    """
    사용자가 입력한 링크를 (라벨, 피드URL) 튜플로 변환한다.
    네이버 블로그/RSS 링크, 일반 사이트의 RSS 피드 탐색을 순서대로 시도. 실패 시 None.
    """
    url = url.strip()
    if not url:
        return None

    if url.endswith(".xml") or "rss.blog.naver.com" in url:
        label = extract_naver_blog_id(url) or url
        return label, url

    blog_id = extract_naver_blog_id(url)
    if blog_id:
        return blog_id, f"https://rss.blog.naver.com/{blog_id}.xml"

    feed_url = discover_feed_link(url)
    if feed_url:
        return url, feed_url

    return url, url


def collect_link_data(urls):
    """사용자가 입력한 링크(최대 5개)를 분석용 소스로 변환해 최근 글을 수집."""
    sources = []
    for url in urls[:5]:
        resolved = resolve_link_to_feed_source(url)
        if resolved:
            sources.append(resolved)

    if not sources:
        return []

    return collect_feed_sources(sources, step_label="[링크] 사용자 지정 링크 수집")


# ---------------------------------------------------------------------------
# 1(c). 데이터 통합
# ---------------------------------------------------------------------------

def build_dataframe(search_rows, rss_rows):
    """수집 결과를 pandas DataFrame으로 통합."""
    all_rows = search_rows + rss_rows
    columns = ["source", "keyword_or_blog", "title", "url", "date"]
    if not all_rows:
        return pd.DataFrame(columns=columns)
    df = pd.DataFrame(all_rows, columns=columns)
    df = df.drop_duplicates(subset=["title", "url"]).reset_index(drop=True)
    return df


# ---------------------------------------------------------------------------
# 2(a). 키워드 추출 및 불용어 처리
# ---------------------------------------------------------------------------

STOPWORDS = {
    "하는", "위한", "방법", "정리", "후기", "완벽", "가이드", "총정리",
    "하기", "해보기", "알아보기", "소개", "추천", "이야기", "정보", "리뷰",
    "쉽게", "이렇게", "이것", "저것", "그것", "무엇", "어떻게", "제대로",
    "빠르게", "간단", "기본", "이해", "완전", "필수", "꿀팁", "노하우",
    "오늘", "최근", "요즘", "진짜", "정말", "그냥", "너무", "우리",
    "그리고", "하지만", "그래서", "때문", "관련", "대해", "대한",
    "만들기", "만드는", "대상", "무료", "특강", "강의", "활용", "사용",
    "배우는", "가지", "이제", "이게", "되네", "합니다", "하세요",
    "있는", "없는", "있나요", "여러", "초보", "초보자", "사람", "모든",
    "바로", "함께", "통해", "위해", "순삭", "안내", "모집", "신청",
    "강좌", "수업", "과정", "시간", "하나",
    "with", "for", "the", "and", "how", "to",
}

KOREAN_ENGLISH_WORD_PATTERN = re.compile(r"[가-힣a-zA-Z]{2,}")


def extract_keywords(title):
    """제목에서 한글/영문 단어 추출 후 불용어 제거."""
    words = KOREAN_ENGLISH_WORD_PATTERN.findall(title)
    return [w for w in words if w not in STOPWORDS]


# ---------------------------------------------------------------------------
# 2(b). 주제 분류 사전
# ---------------------------------------------------------------------------

CATEGORY_KEYWORDS = {
    "도구": [
        "챗GPT", "ChatGPT", "클로드", "Claude", "미드저니", "Midjourney",
        "노션", "Notion", "캔바", "Canva", "코파일럿", "Copilot",
        "제미나이", "Gemini", "달리", "DALLE", "퍼플렉시티", "Perplexity",
        "감마", "Gamma", "런웨이", "Runway", "스테이블디퓨전", "StableDiffusion",
        "브루", "Vrew", "뤼튼", "Wrtn",
    ],
    "활용법": [
        "활용", "사용법", "프롬프트", "자동화", "요약", "번역", "작성법",
        "글쓰기", "이미지생성", "영상편집", "코딩", "데이터분석", "업무효율",
        "템플릿", "워크플로우", "연동", "확장프로그램", "플러그인",
    ],
    "수익화": [
        "수익", "부업", "애드센스", "블로그수익", "판매", "마케팅",
        "재테크", "창업", "사이드프로젝트", "전자책", "스마트스토어",
        "제휴마케팅", "브랜딩", "구독료", "유료화", "광고수익",
    ],
    "트렌드": [
        "출시", "업데이트", "뉴스", "비교", "전망", "동향", "최신",
        "신기능", "베타", "발표", "이슈", "순위", "인기", "화제",
        "트렌드", "변화",
    ],
}


def classify_category(keywords):
    """키워드 리스트를 받아 가장 많이 매칭되는 카테고리 반환. 매칭 없으면 '기타'."""
    scores = {cat: 0 for cat in CATEGORY_KEYWORDS}
    joined = " ".join(keywords)
    for cat, cat_keywords in CATEGORY_KEYWORDS.items():
        for ck in cat_keywords:
            if ck in joined:
                scores[cat] += 1
    best_cat = max(scores, key=scores.get)
    if scores[best_cat] == 0:
        return "기타"
    return best_cat


# ---------------------------------------------------------------------------
# 2(c)~2(e). 틈새 필터링 및 TOP 10 선정
# ---------------------------------------------------------------------------

def get_my_topic_keywords():
    """MY_TOPICS 문자열들을 키워드 분해."""
    my_keywords = set()
    for topic in config.MY_TOPICS:
        my_keywords.update(extract_keywords(topic))
    return my_keywords


def build_keyword_stats(df):
    """
    각 키워드에 대해 (빈도, 등장 소스 집합, 카테고리) 통계를 만든다.
    소스는 keyword_or_blog 값 기준 (검색 키워드 또는 RSS 블로그 ID) - 경쟁도(다루는 채널 수) 산출용.
    """
    keyword_freq = {}
    keyword_sources = {}
    keyword_titles = {}

    for _, row in df.iterrows():
        title = row["title"]
        source_id = row["keyword_or_blog"]
        kws = extract_keywords(title)
        for kw in kws:
            keyword_freq[kw] = keyword_freq.get(kw, 0) + 1
            keyword_sources.setdefault(kw, set()).add(source_id)
            keyword_titles.setdefault(kw, []).append(title)

    return keyword_freq, keyword_sources, keyword_titles


def filter_out_my_topics(keyword_freq, my_keywords):
    """MY_TOPICS와 겹치는 키워드 제외 (부분 일치 기준)."""
    my_keywords_lower = [mk.lower() for mk in my_keywords]

    def overlaps_my_topics(kw):
        kw_lower = kw.lower()
        return any(mk in kw_lower or kw_lower in mk for mk in my_keywords_lower)

    return {
        kw: freq for kw, freq in keyword_freq.items()
        if not overlaps_my_topics(kw)
    }


def detect_branding_keywords(df, keyword_sources, keyword_titles):
    """
    단일 소스에서만 등장하고, 그 소스 제목의 30% 이상에서 반복 등장하는
    키워드를 블로거 닉네임 등 브랜딩/시그니처 단어로 간주해 반환한다.
    """
    source_title_counts = df["keyword_or_blog"].value_counts().to_dict()
    branding = set()

    for kw, sources in keyword_sources.items():
        if len(sources) != 1:
            continue
        only_source = next(iter(sources))
        total = source_title_counts.get(only_source, 0)
        if total <= 0:
            continue
        occurrence = len(keyword_titles.get(kw, []))
        if occurrence / total >= 0.3:
            branding.add(kw)

    return branding


def select_top_niche_topics(keyword_freq, keyword_sources, keyword_titles, top_n):
    """
    score = 빈도 / (1 + 언급한 소스 수) 로 틈새 주제 TOP N 선정.
    우연히 1~2회만 등장한 키워드가 상위에 오르지 않도록 최소 빈도(3회) 이상만
    후보로 삼되, 후보가 top_n에 못 미치면 최소 빈도를 2회로 완화한다.
    """
    def build_scored(min_freq):
        scored = []
        for kw, freq in keyword_freq.items():
            if freq < min_freq:
                continue
            source_count = len(keyword_sources.get(kw, set()))
            score = freq / (1 + source_count)
            scored.append({
                "keyword": kw,
                "freq": freq,
                "source_count": source_count,
                "score": score,
                "titles": keyword_titles.get(kw, []),
            })
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored

    scored = build_scored(min_freq=3)
    if len(scored) < top_n:
        scored = build_scored(min_freq=2)

    return scored[:top_n]


def competition_level(source_count):
    """경쟁도 라벨링."""
    if source_count <= 1:
        return "낮음"
    elif source_count <= 3:
        return "중간"
    else:
        return "높음"


def build_related_keywords(main_keyword, titles, exclude=None, limit=5):
    """주제와 관련된 연관 키워드 추출 (같은 제목 그룹에서 등장하는 다른 키워드들)."""
    exclude = exclude or set()
    related_freq = {}
    for title in titles:
        for kw in extract_keywords(title):
            if kw == main_keyword or kw in exclude:
                continue
            related_freq[kw] = related_freq.get(kw, 0) + 1
    related_sorted = sorted(related_freq.items(), key=lambda x: x[1], reverse=True)
    return [kw for kw, _ in related_sorted[:limit]]


def generate_topic_overview(rank, topic_keyword, category, freq, comp_level, related_keywords):
    """템플릿 기반 개요 문장 생성 (LLM 미사용)."""
    comp_text = {
        "낮음": "경쟁 블로그가 적어 선점 기회가 큰 영역입니다.",
        "중간": "일부 경쟁 블로그가 다루고 있으나 아직 포화 상태는 아닙니다.",
        "높음": "다수 블로그가 이미 다루고 있어 차별화 전략이 필요합니다.",
    }.get(comp_level, "")

    overview = (
        f"'{topic_keyword}'은(는) 최근 {freq}회 언급되며 관심도가 높아지는 주제입니다. "
        f"{comp_text} "
        f"'{category}' 관점에서 콘텐츠를 구성하면 차별화된 포스팅이 가능합니다."
    )
    return overview


def build_niche_report_items(top_topics, my_keywords, branding_keywords=None):
    """TOP N 각각에 대해 순위, 카테고리, 개요, 연관 키워드 등을 조립."""
    exclude = set(my_keywords) | set(branding_keywords or [])
    items = []
    for i, topic in enumerate(top_topics, start=1):
        kw = topic["keyword"]
        titles = topic["titles"]
        related = build_related_keywords(kw, titles, exclude=exclude, limit=5)
        related = related if related else ["-"]
        keywords_in_titles = []
        for t in titles:
            keywords_in_titles.extend(extract_keywords(t))
        category = classify_category(keywords_in_titles) if keywords_in_titles else "기타"
        comp_level = competition_level(topic["source_count"])
        overview = generate_topic_overview(
            i, kw, category, topic["freq"], comp_level, related
        )

        items.append({
            "rank": i,
            "topic": kw,
            "category": category,
            "freq": topic["freq"],
            "source_count": topic["source_count"],
            "score": round(topic["score"], 2),
            "competition": comp_level,
            "overview": overview,
            "related_keywords": related,
        })
    return items


# ---------------------------------------------------------------------------
# 3(a). PDF 리포트 생성
# ---------------------------------------------------------------------------

def find_korean_font():
    """한글 폰트 경로 탐색. 없으면 None."""
    for path in config.FONT_CANDIDATES:
        if os.path.exists(path):
            return path
    return None


def generate_pdf_report(niche_items, output_path, font_path):
    """reportlab으로 PDF 리포트 생성. 폰트 없으면 .md로 대체."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    font_name = "MalgunGothic"
    pdfmetrics.registerFont(TTFont(font_name, font_path))

    c = canvas.Canvas(output_path, pagesize=A4)
    width, height = A4

    # 표지
    c.setFont(font_name, 24)
    c.drawCentredString(width / 2, height - 100 * mm, "틈새 주제 추천 리포트")
    c.setFont(font_name, 12)
    today_str = datetime.now().strftime("%Y-%m-%d")
    c.drawCentredString(width / 2, height - 115 * mm, f"생성일: {today_str}")
    c.showPage()

    # 본문
    c.setFont(font_name, 16)
    y = height - 20 * mm
    c.drawString(20 * mm, y, "틈새 주제 TOP 10")
    y -= 12 * mm

    for item in niche_items:
        if y < 40 * mm:
            c.showPage()
            c.setFont(font_name, 12)
            y = height - 20 * mm

        c.setFont(font_name, 13)
        c.drawString(20 * mm, y, f"{item['rank']}위. {item['topic']} ({item['category']})")
        y -= 7 * mm

        c.setFont(font_name, 10)
        c.drawString(22 * mm, y, f"점수: {item['score']}  |  언급 횟수: {item['freq']}  |  경쟁도: {item['competition']}")
        y -= 6 * mm

        overview_lines = wrap_text(item["overview"], 42)
        for line in overview_lines:
            c.drawString(22 * mm, y, line)
            y -= 5.5 * mm

        related_str = ", ".join(item["related_keywords"])
        c.drawString(22 * mm, y, f"예상 연관 키워드: {related_str}")
        y -= 10 * mm

    c.save()


def wrap_text(text, max_chars):
    """간단한 줄바꿈 처리."""
    lines = []
    current = ""
    for ch in text:
        current += ch
        if len(current) >= max_chars:
            lines.append(current)
            current = ""
    if current:
        lines.append(current)
    return lines


def generate_md_report(niche_items, output_path):
    """폰트가 없을 때 PDF 대신 Markdown으로 대체 저장."""
    lines = ["# 틈새 주제 추천 리포트", "", f"생성일: {datetime.now().strftime('%Y-%m-%d')}", ""]
    lines.append("## 틈새 주제 TOP 10")
    lines.append("")
    for item in niche_items:
        lines.append(f"### {item['rank']}위. {item['topic']} ({item['category']})")
        lines.append(f"- 점수: {item['score']}")
        lines.append(f"- 언급 횟수: {item['freq']}")
        lines.append(f"- 경쟁도: {item['competition']}")
        lines.append(f"- 개요: {item['overview']}")
        lines.append(f"- 예상 연관 키워드: {', '.join(item['related_keywords'])}")
        lines.append("")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def create_report(niche_items):
    """PDF 생성 시도, 폰트 없으면 .md로 폴백. 실제로 저장된 파일 경로를 반환한다."""
    font_path = find_korean_font()
    pdf_path = os.path.join(config.OUTPUT_DIR, config.REPORT_PDF_FILENAME)

    if font_path is None:
        print("[경고] 한글 폰트(malgun.ttf / malgunbd.ttf)를 찾을 수 없어 PDF 대신 Markdown으로 저장합니다.")
        md_path = os.path.splitext(pdf_path)[0] + ".md"
        generate_md_report(niche_items, md_path)
        print(f"  -> 저장 완료: {md_path}")
        return md_path

    try:
        generate_pdf_report(niche_items, pdf_path, font_path)
        print(f"  -> 저장 완료: {pdf_path}")
        return pdf_path
    except Exception as e:
        print(f"[경고] PDF 생성 실패, Markdown으로 대체 저장합니다: {e}")
        md_path = os.path.splitext(pdf_path)[0] + ".md"
        generate_md_report(niche_items, md_path)
        print(f"  -> 저장 완료: {md_path}")
        return md_path


# ---------------------------------------------------------------------------
# 3(b). 트렌드 차트 생성
# ---------------------------------------------------------------------------

def create_trend_chart(keyword_freq, niche_items, output_path, font_path):
    """워드클라우드 + 카테고리/키워드 막대그래프 2단 구성."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from wordcloud import WordCloud

    plt.rcParams["font.family"] = "Malgun Gothic"
    plt.rcParams["axes.unicode_minus"] = False

    fig, axes = plt.subplots(2, 1, figsize=(10, 12))

    # 상단: 워드클라우드
    ax_wc = axes[0]
    if keyword_freq:
        wc_font = font_path if font_path else None
        wc = WordCloud(
            font_path=wc_font,
            width=1000,
            height=500,
            background_color="white",
        ).generate_from_frequencies(keyword_freq)
        ax_wc.imshow(wc, interpolation="bilinear")
    ax_wc.axis("off")
    ax_wc.set_title("전체 키워드 워드클라우드", fontsize=16)

    # 하단: 상위 키워드 빈도 막대그래프
    ax_bar = axes[1]
    top_items = sorted(keyword_freq.items(), key=lambda x: x[1], reverse=True)[:15]
    if top_items:
        labels = [k for k, _ in top_items]
        values = [v for _, v in top_items]
        ax_bar.bar(labels, values, color="#4C72B0")
        ax_bar.set_title("상위 키워드 빈도", fontsize=16)
        ax_bar.set_ylabel("언급 횟수")
        ax_bar.tick_params(axis="x", rotation=45)
    else:
        ax_bar.text(0.5, 0.5, "데이터 없음", ha="center", va="center")
        ax_bar.axis("off")

    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close(fig)


# ---------------------------------------------------------------------------
# 3(c). 요약 텍스트 생성
# ---------------------------------------------------------------------------

def create_summary_txt(niche_items, output_path):
    """핵심 인사이트 3줄 요약."""
    if not niche_items:
        lines = ["수집된 데이터가 없어 인사이트를 생성할 수 없습니다."]
    else:
        category_freq = {}
        for item in niche_items:
            category_freq[item["category"]] = category_freq.get(item["category"], 0) + item["freq"]
        hottest_category = max(category_freq, key=category_freq.get) if category_freq else "N/A"

        best_topic = niche_items[0]
        low_competition_topics = [i for i in niche_items if i["competition"] == "낮음"]
        gap_area = low_competition_topics[0]["topic"] if low_competition_topics else best_topic["topic"]

        lines = [
            f"1. 가장 뜨거운 카테고리: {hottest_category}",
            f"2. 최고 틈새 주제: {best_topic['topic']} (점수 {best_topic['score']}, 카테고리: {best_topic['category']})",
            f"3. 경쟁 공백 영역: {gap_area} (경쟁도 낮음, 선점 기회)",
        ]

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


# ---------------------------------------------------------------------------
# 메인 실행 흐름
# ---------------------------------------------------------------------------

def run_pipeline(extra_links=None):
    """
    전체 파이프라인 실행 (검색+RSS+선택적 사용자 링크 수집 -> 분석 -> 결과물 생성).
    CLI(main)와 웹앱(app.py)이 공유한다.

    반환: {
        "has_data": bool,
        "niche_items": [...],
        "output_paths": {"csv": str, "report": str, "chart": str, "summary": str},
    }
    """
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    result = {"has_data": False, "niche_items": [], "output_paths": {}}

    # 1. 데이터 수집
    try:
        search_rows = collect_search_data()
    except Exception as e:
        print(f"[경고] 검색 수집 단계 전체 실패: {e}")
        search_rows = []

    try:
        rss_rows = collect_rss_data()
    except Exception as e:
        print(f"[경고] RSS 수집 단계 전체 실패: {e}")
        rss_rows = []

    link_rows = []
    if extra_links:
        try:
            link_rows = collect_link_data(extra_links)
        except Exception as e:
            print(f"[경고] 링크 수집 단계 전체 실패: {e}")
            link_rows = []

    print("[3/5] 수집 데이터 통합 중...")
    df = build_dataframe(search_rows, rss_rows + link_rows)

    if df.empty:
        print("수집된 데이터가 하나도 없습니다. 프로그램을 종료합니다.")
        return result

    result["has_data"] = True

    csv_path = os.path.join(config.OUTPUT_DIR, config.COLLECTED_DATA_CSV_FILENAME)
    try:
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")
        print(f"  -> 원본 데이터 저장 완료: {csv_path}")
        result["output_paths"]["csv"] = csv_path
    except Exception as e:
        print(f"[경고] 원본 데이터 CSV 저장 실패: {e}")

    # 2. 분석
    print("[4/5] 키워드 분석 및 틈새 주제 선정 중...")
    keyword_freq = {}
    niche_items = []
    try:
        keyword_freq, keyword_sources, keyword_titles = build_keyword_stats(df)
        my_keywords = get_my_topic_keywords()
        filtered_freq = filter_out_my_topics(keyword_freq, my_keywords)

        branding_keywords = detect_branding_keywords(df, keyword_sources, keyword_titles)
        if branding_keywords:
            print(f"[정보] 브랜딩 키워드 제외: {', '.join(sorted(branding_keywords))}")
            filtered_freq = {
                kw: freq for kw, freq in filtered_freq.items()
                if kw not in branding_keywords
            }

        if not filtered_freq:
            print("틈새 주제로 분류될 키워드가 없습니다. (모두 기존 주제와 겹치거나 데이터 부족)")
        else:
            top_topics = select_top_niche_topics(
                filtered_freq, keyword_sources, keyword_titles, config.TOP_N_NICHE_TOPICS
            )
            niche_items = build_niche_report_items(top_topics, my_keywords, branding_keywords)
    except Exception as e:
        print(f"[경고] 분석 단계 실패: {e}")

    result["niche_items"] = niche_items

    # 3. 결과물 생성
    print("[5/5] 결과물 생성 중...")

    try:
        report_path = create_report(niche_items)
        result["output_paths"]["report"] = report_path
    except Exception as e:
        print(f"[경고] PDF/MD 리포트 생성 실패: {e}")

    try:
        font_path = find_korean_font()
        chart_path = os.path.join(config.OUTPUT_DIR, config.TREND_CHART_FILENAME)
        create_trend_chart(keyword_freq, niche_items, chart_path, font_path)
        print(f"  -> 트렌드 차트 저장 완료: {chart_path}")
        result["output_paths"]["chart"] = chart_path
    except Exception as e:
        print(f"[경고] 트렌드 차트 생성 실패: {e}")

    try:
        summary_path = os.path.join(config.OUTPUT_DIR, config.SUMMARY_TXT_FILENAME)
        create_summary_txt(niche_items, summary_path)
        print(f"  -> 요약 저장 완료: {summary_path}")
        result["output_paths"]["summary"] = summary_path
    except Exception as e:
        print(f"[경고] 요약 생성 실패: {e}")

    print("모든 작업이 완료되었습니다.")
    return result


def main():
    run_pipeline()


if __name__ == "__main__":
    main()
