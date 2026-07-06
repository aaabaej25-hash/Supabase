from apt_landing.models import (
    Copy,
    Project,
    StyleGuide,
    UnitType,
    list_projects,
    load_project,
    save_project,
    slugify,
)


def test_slugify_korean_and_symbols():
    assert slugify("래미안 원베일리 2차!") == "래미안-원베일리-2차"
    assert slugify("  Hello World  ") == "hello-world"
    assert slugify("!!!") == "project"


def test_save_load_roundtrip(tmp_path):
    p = Project(
        slug="test-apt",
        name="테스트 아파트",
        address="서울시 서초구",
        move_in="2027년 3월",
        highlights="역세권, 초품아",
        units=[UnitType(name="84A", price="15억")],
        kakao_link="https://open.kakao.com/o/abc",
        reference_url="https://example.com",
        photos=["01-front.jpg"],
        status="draft",
        style=StyleGuide(primary_color="#123456", extracted=True),
        copy=Copy(hero_headline="테스트 헤드라인"),
    )
    save_project(str(tmp_path), p)
    loaded = load_project(str(tmp_path), "test-apt")
    assert loaded == p


def test_list_projects_skips_non_project_dirs(tmp_path):
    save_project(str(tmp_path), Project(slug="a", name="A"))
    save_project(str(tmp_path), Project(slug="b", name="B"))
    (tmp_path / "쓰레기폴더").mkdir()
    slugs = [p.slug for p in list_projects(str(tmp_path))]
    assert slugs == ["a", "b"]


def test_default_style_is_fallback():
    assert StyleGuide().extracted is False
    assert StyleGuide().section_order == ["info", "location", "gallery"]
