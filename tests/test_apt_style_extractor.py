from apt_landing.style_extractor import extract_style

SAMPLE_HTML = """
<html><head><style>
.hero { background-color: #112244; color: #ffffff; }
.btn { background: #cc9933; } .btn2 { background: #cc9933; }
h1 { color: #112244; } p { color: #333333; }
</style></head>
<body>
<h2>사진 갤러리</h2><p>단지 전경을 만나보세요</p>
<h2>프리미엄 입지</h2><p>도심 한가운데</p>
<h2>세대 안내 및 가격</h2><p>84타입</p>
<p>지금 만나보세요. 프리미엄의 기준.</p>
</body></html>
"""


def fake_fetch(url):
    return SAMPLE_HTML


def fake_chat(model, prompt):
    return "고급스럽고 절제된 프리미엄 톤"


def test_extract_style_colors_and_tone():
    sg = extract_style("https://example.com", "m", chat=fake_chat, fetch=fake_fetch)
    assert sg.extracted is True
    assert sg.primary_color == "#112244"  # 최다 빈도
    assert sg.accent_color == "#cc9933"   # 2위 빈도
    assert sg.tone == "고급스럽고 절제된 프리미엄 톤"


def test_extract_style_section_order_from_headings():
    sg = extract_style("https://example.com", "m", chat=fake_chat, fetch=fake_fetch)
    # 문서 순서: 갤러리 → 입지 → 세대(핵심정보)
    assert sg.section_order == ["gallery", "location", "info"]


def test_extract_style_fetch_failure_falls_back():
    def boom(url):
        raise RuntimeError("연결 실패")

    sg = extract_style("https://example.com", "m", chat=fake_chat, fetch=boom)
    assert sg.extracted is False
    assert sg.section_order == ["info", "location", "gallery"]


def test_extract_style_no_colors_falls_back():
    sg = extract_style("https://example.com", "m", chat=fake_chat, fetch=lambda u: "<html><body>텍스트만</body></html>")
    assert sg.extracted is False
