import io
from urllib.parse import unquote

from fastapi.testclient import TestClient
from PIL import Image

from apt_landing.app import create_app
from apt_landing.config import AptConfig
from apt_landing.models import load_project


def make_client(tmp_path):
    cfg = AptConfig(projects_dir=str(tmp_path / "projects"))
    return TestClient(create_app(cfg)), cfg


def png_bytes():
    buf = io.BytesIO()
    Image.new("RGB", (100, 80), "blue").save(buf, "PNG")
    return buf.getvalue()


def test_create_and_list_project(tmp_path):
    client, cfg = make_client(tmp_path)
    r = client.post("/projects", data={"name": "테스트 아파트"}, follow_redirects=False)
    assert r.status_code == 303
    # 한글 슬러그는 location 헤더에서 퍼센트 인코딩됨
    assert unquote(r.headers["location"]) == "/p/테스트-아파트"
    r = client.get("/")
    assert "테스트 아파트" in r.text


def test_create_duplicate_requires_overwrite(tmp_path):
    client, cfg = make_client(tmp_path)
    client.post("/projects", data={"name": "중복"})
    r = client.post("/projects", data={"name": "중복"})
    assert "이미 존재" in r.text
    r = client.post("/projects", data={"name": "중복", "overwrite": "on"}, follow_redirects=False)
    assert r.status_code == 303


def test_save_project_info(tmp_path):
    client, cfg = make_client(tmp_path)
    client.post("/projects", data={"name": "테스트"})
    r = client.post(
        "/p/테스트",
        data={
            "name": "테스트",
            "address": "서울시 서초구",
            "move_in": "2027년 3월",
            "highlights": "역세권",
            "units_text": "84A|15억\n59B|11억",
            "kakao_link": "https://open.kakao.com/o/abc",
            "reference_url": "",
        },
    )
    assert r.status_code == 200
    p = load_project(cfg.projects_dir, "테스트")
    assert p.address == "서울시 서초구"
    assert [u.name for u in p.units] == ["84A", "59B"]
    assert p.units[1].price == "11억"


def test_photo_upload_delete_and_reorder(tmp_path):
    client, cfg = make_client(tmp_path)
    client.post("/projects", data={"name": "테스트"})
    files = [
        ("files", ("a.png", png_bytes(), "image/png")),
        ("files", ("b.png", png_bytes(), "image/png")),
    ]
    r = client.post("/p/테스트/photos", files=files)
    assert r.status_code == 200
    p = load_project(cfg.projects_dir, "테스트")
    assert len(p.photos) == 2
    second = p.photos[1]
    client.post(f"/p/테스트/photos/{second}/up")
    p = load_project(cfg.projects_dir, "테스트")
    assert p.photos[0] == second
    client.post(f"/p/테스트/photos/{second}/delete")
    p = load_project(cfg.projects_dir, "테스트")
    assert len(p.photos) == 1
