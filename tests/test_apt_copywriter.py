import json

import pytest

from apt_landing.copywriter import CopyParseError, generate_copy, regenerate_section
from apt_landing.models import Project, UnitType

SAMPLE = Project(
    slug="t",
    name="테스트 아파트",
    address="서울시 서초구",
    move_in="2027년 3월",
    highlights="역세권",
    units=[UnitType(name="84A", price="15억")],
)

GOOD_JSON = json.dumps(
    {
        "hero_headline": "H",
        "hero_sub": "S",
        "info_summary": "I",
        "location_paragraph": "L",
        "gallery_caption": "G",
        "cta_text": "C",
    },
    ensure_ascii=False,
)


def test_generate_copy_parses_json():
    copy = generate_copy(SAMPLE, "m", chat=lambda model, prompt: GOOD_JSON)
    assert copy.hero_headline == "H"
    assert copy.cta_text == "C"


def test_generate_copy_strips_surrounding_text():
    copy = generate_copy(SAMPLE, "m", chat=lambda model, prompt: f"물론입니다!\n{GOOD_JSON}\n끝.")
    assert copy.hero_sub == "S"


def test_generate_copy_retries_once_then_raises():
    calls = []

    def bad_chat(model, prompt):
        calls.append(prompt)
        return "JSON 아님"

    with pytest.raises(CopyParseError) as exc:
        generate_copy(SAMPLE, "m", chat=bad_chat)
    assert len(calls) == 2
    assert exc.value.raw == "JSON 아님"


def test_regenerate_section_returns_plain_text():
    text = regenerate_section(SAMPLE, "hero_headline", "m", chat=lambda model, prompt: "새 헤드라인\n")
    assert text == "새 헤드라인"


def test_regenerate_section_rejects_unknown_section():
    with pytest.raises(ValueError):
        regenerate_section(SAMPLE, "없는섹션", "m", chat=lambda model, prompt: "x")
