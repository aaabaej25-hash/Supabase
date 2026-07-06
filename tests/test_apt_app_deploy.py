from fastapi.testclient import TestClient

import apt_landing.app as app_module
from apt_landing.app import create_app
from apt_landing.config import AptConfig
from apt_landing.models import load_project


def make_client(tmp_path):
    cfg = AptConfig(projects_dir=str(tmp_path / "projects"),
                    pages_base_url="https://eunj-it.github.io/apt-pages")
    client = TestClient(create_app(cfg))
    client.post("/projects", data={"name": "테스트"})
    return client, cfg


def test_deploy_success_saves_url_and_status(tmp_path, monkeypatch):
    client, cfg = make_client(tmp_path)
    monkeypatch.setattr(app_module, "deploy",
                        lambda p, c: f"{c.pages_base_url}/{p.slug}/")
    r = client.post("/p/테스트/deploy")
    assert r.status_code == 200
    p = load_project(cfg.projects_dir, "테스트")
    assert p.status == "deployed"
    assert p.deployed_url == "https://eunj-it.github.io/apt-pages/테스트/"


def test_deploy_failure_shows_error(tmp_path, monkeypatch):
    client, cfg = make_client(tmp_path)

    def boom(p, c):
        raise RuntimeError("git push 실패:\nremote 인증 오류")

    monkeypatch.setattr(app_module, "deploy", boom)
    r = client.post("/p/테스트/deploy")
    assert "인증 오류" in r.text
    p = load_project(cfg.projects_dir, "테스트")
    assert p.status != "deployed"


def test_undeploy_clears_url(tmp_path, monkeypatch):
    client, cfg = make_client(tmp_path)
    monkeypatch.setattr(app_module, "deploy", lambda p, c: "https://x/테스트/")
    monkeypatch.setattr(app_module, "undeploy", lambda slug, c: None)
    client.post("/p/테스트/deploy")
    client.post("/p/테스트/undeploy")
    p = load_project(cfg.projects_dir, "테스트")
    assert p.deployed_url == ""
    assert p.status == "copy_done"
