import io
import json

from fastapi.testclient import TestClient
from PIL import Image

import apt_landing.app as app_module
from apt_landing.app import create_app
from apt_landing.config import AptConfig
from apt_landing.copywriter import CopyParseError
from apt_landing.models import load_project

GOOD_JSON = json.dumps(
    {"hero_headline": "H", "hero_sub": "S", "info_summary": "I",
     "location_paragraph": "L", "gallery_caption": "G", "cta_text": "C"},
    ensure_ascii=False,
)


def make_client(tmp_path):
    cfg = AptConfig(projects_dir=str(tmp_path / "projects"))
    client = TestClient(create_app(cfg))
    client.post("/projects", data={"name": "테스트"})
    return client, cfg


def test_generate_copy_route(tmp_path, monkeypatch):
    client, cfg = make_client(tmp_path)
    monkeypatch.setattr(app_module, "ollama_chat", lambda model, prompt: GOOD_JSON)
    r = client.post("/p/테스트/copy/generate")
    assert r.status_code == 200
    p = load_project(cfg.projects_dir, "테스트")
    assert p.copy.hero_headline == "H"


def test_generate_copy_parse_error_shows_raw(tmp_path, monkeypatch):
    client, cfg = make_client(tmp_path)
    monkeypatch.setattr(app_module, "ollama_chat", lambda model, prompt: "JSON 아님")
    r = client.post("/p/테스트/copy/generate")
    assert "JSON 아님" in r.text  # 원문 표시 → 수동 편집 유도


def test_regenerate_single_section(tmp_path, monkeypatch):
    client, cfg = make_client(tmp_path)
    monkeypatch.setattr(app_module, "ollama_chat", lambda model, prompt: "새 문구")
    client.post("/p/테스트/copy/generate/hero_headline")
    p = load_project(cfg.projects_dir, "테스트")
    assert p.copy.hero_headline == "새 문구"


def test_save_copy_marks_copy_done(tmp_path):
    client, cfg = make_client(tmp_path)
    data = {k: f"수정된 {k}" for k in
            ["hero_headline", "hero_sub", "info_summary", "location_paragraph", "gallery_caption", "cta_text"]}
    client.post("/p/테스트/copy", data=data)
    p = load_project(cfg.projects_dir, "테스트")
    assert p.copy.info_summary == "수정된 info_summary"
    assert p.status == "copy_done"


def test_style_route_fallback_notice(tmp_path, monkeypatch):
    client, cfg = make_client(tmp_path)
    client.post("/p/테스트", data={"name": "테스트", "reference_url": "https://예시.com",
                                   "address": "", "move_in": "", "highlights": "",
                                   "units_text": "", "kakao_link": ""})
    monkeypatch.setattr(app_module, "extract_style",
                        lambda url, model, **kw: app_module.StyleGuide())
    r = client.post("/p/테스트/style")
    assert "기본 스타일" in r.text


def test_preview_builds_and_serves(tmp_path):
    client, cfg = make_client(tmp_path)
    buf = io.BytesIO()
    Image.new("RGB", (100, 80), "green").save(buf, "PNG")
    client.post("/p/테스트/photos", files=[("files", ("a.png", buf.getvalue(), "image/png"))])
    r = client.get("/preview/테스트/")
    assert r.status_code == 200
    assert "테스트" in r.text
    p = load_project(cfg.projects_dir, "테스트")
    photo_name = "01-a.webp"
    r = client.get(f"/preview/테스트/photos/{photo_name}")
    assert r.status_code == 200
