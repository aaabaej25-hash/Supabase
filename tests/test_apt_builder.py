import os

from PIL import Image

from apt_landing.builder import build
from apt_landing.models import Copy, Project, StyleGuide, UnitType, save_project


def make_project(tmp_path, photos=True) -> Project:
    p = Project(
        slug="t-apt",
        name="테스트 아파트",
        address="서울시 서초구 123",
        move_in="2027년 3월",
        units=[UnitType(name="84A", price="15억")],
        kakao_link="https://open.kakao.com/o/abc",
        style=StyleGuide(primary_color="#112244", section_order=["gallery", "info", "location"]),
        copy=Copy(hero_headline="빛나는 시작", cta_text="카톡 문의"),
    )
    save_project(str(tmp_path), p)
    if photos:
        photo_dir = tmp_path / "t-apt" / "photos"
        Image.new("RGB", (2400, 1200), "red").save(photo_dir / "01-front.jpg")
        p.photos = ["01-front.jpg"]
    return p


def test_build_renders_landing(tmp_path):
    p = make_project(tmp_path)
    build_dir, failed = build(p, str(tmp_path))
    assert failed == []
    html = open(os.path.join(build_dir, "index.html"), encoding="utf-8").read()
    assert "테스트 아파트" in html
    assert "빛나는 시작" in html
    assert "https://open.kakao.com/o/abc" in html
    assert "--primary: #112244" in html
    # 섹션 순서 반영: 갤러리가 핵심정보보다 앞
    assert html.index('id="gallery"') < html.index('id="info"')


def test_build_converts_photos_to_webp_max_1600(tmp_path):
    p = make_project(tmp_path)
    build_dir, _ = build(p, str(tmp_path))
    out = os.path.join(build_dir, "photos", "01-front.webp")
    assert os.path.isfile(out)
    assert Image.open(out).width <= 1600
    # 원본 보존
    assert os.path.isfile(os.path.join(str(tmp_path), "t-apt", "photos", "01-front.jpg"))


def test_build_skips_broken_photo(tmp_path):
    p = make_project(tmp_path)
    broken = tmp_path / "t-apt" / "photos" / "02-broken.jpg"
    broken.write_bytes(b"not an image")
    p.photos.append("02-broken.jpg")
    build_dir, failed = build(p, str(tmp_path))
    assert failed == ["02-broken.jpg"]
    assert os.path.isfile(os.path.join(build_dir, "index.html"))


def test_build_without_photos(tmp_path):
    p = make_project(tmp_path, photos=False)
    build_dir, failed = build(p, str(tmp_path))
    assert failed == []
    assert os.path.isfile(os.path.join(build_dir, "index.html"))
