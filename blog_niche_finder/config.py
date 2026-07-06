# -*- coding: utf-8 -*-
"""
blog_niche_finder 설정 파일
사용자가 쉽게 수정할 수 있는 값들을 모아둔다.
"""

import os

# 검색 키워드 (각각 site:blog.naver.com 붙여서 검색, 키워드당 상위 15개, 최근 3개월)
SEARCH_KEYWORDS = [
    "AI 자동화",
    "ChatGPT 활용",
    "AI 수익화",
    "클로드 AI",
]

# 검색당 수집할 최대 결과 수
SEARCH_RESULTS_PER_KEYWORD = 15

# 최근 몇 개월 이내 결과만 수집할지 (구글 tbs=qdr:m3 기준)
SEARCH_RECENT_MONTHS = 3

# RSS로 모니터링할 네이버 블로그 ID 목록
# 실제 RSS URL: https://rss.blog.naver.com/{blog_id}.xml
RSS_BLOG_IDS = [
    "michaelchae",
    "hun1188",
    "sunny-canva",
]

# RSS에서 최근 며칠 이내 글만 수집할지
RSS_RECENT_DAYS = 90

# 내 블로그가 이미 다룬 주제 (틈새 필터링 시 제외 기준)
MY_TOPICS = [
    "교육 AI 책",
]

# 출력 디렉토리 및 파일명
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

REPORT_PDF_FILENAME = "niche_topics_report.pdf"
TREND_CHART_FILENAME = "trend_chart.png"
SUMMARY_TXT_FILENAME = "summary.txt"
COLLECTED_DATA_CSV_FILENAME = "collected_data.csv"

# 틈새 주제 TOP N
TOP_N_NICHE_TOPICS = 10

# 요청 사이 sleep 범위 (초)
REQUEST_SLEEP_MIN = 1.0
REQUEST_SLEEP_MAX = 2.0

# 한글 폰트 후보 경로 (reportlab / matplotlib / wordcloud 공용)
FONT_CANDIDATES = [
    r"C:\Windows\Fonts\malgun.ttf",
    r"C:\Windows\Fonts\malgunbd.ttf",
]

# User-Agent (검색 스크래핑용)
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
