"""입력 → 카피 생성 → 빌드 → 배포(dry-run) 전체 파이프라인 검증."""
import json
import os
from types import SimpleNamespace

from PIL import Image

from apt_landing.builder import build
from apt_landing.config import AptConfig
from apt_landing.copywriter import generate_copy
from apt_landing.deployer import deploy
from apt_landing.models import Project, UnitType, load_project, save_project


def test_full_pipeline(tmp_path):
    projects = tmp_path / "projects"

    # 1) 매물 입력
    p = Project(
        slug="래미안-테스트",
        name="래미안 테스트",
        address="서울시 서초구 테스트로 1",
        move_in="2027년 3월",
        highlights="역세권, 초품아, 커뮤니티 시설",
        units=[UnitType(name="84A", price="15억"), UnitType(name="59B", price="11억")],
        kakao_link="https://open.kakao.com/o/test",
    )
    save_project(str(projects), p)
    photo_dir = projects / "래미안-테스트" / "photos"
    Image.new("RGB", (2000, 1000), "navy").save(photo_dir / "01-view.jpg")
    p.photos = ["01-view.jpg"]

    # 2) 카피 생성 (Ollama mock)
    fake_json = json.dumps(
        {"hero_headline": "도심 속 프리미엄", "hero_sub": "역세권 초품아",
         "info_summary": "84·59 두 타입", "location_paragraph": "서초 중심 입지",
         "gallery_caption": "단지 전경", "cta_text": "카톡 상담"},
        ensure_ascii=False,
    )
    p.copy = generate_copy(p, "m", chat=lambda model, prompt: fake_json)
    save_project(str(projects), p)

    # 3) 빌드 → 완전한 정적 사이트인지
    build_dir, failed = build(p, str(projects))
    assert failed == []
    html = open(os.path.join(build_dir, "index.html"), encoding="utf-8").read()
    for text in ["도심 속 프리미엄", "래미안 테스트", "15억",
                 "https://open.kakao.com/o/test", "photos/01-view.webp"]:
        assert text in html
    assert os.path.isfile(os.path.join(build_dir, "photos", "01-view.webp"))

    # 4) 배포 dry-run → git 명령 순서 검증
    repo = tmp_path / "apt-pages"
    (repo / ".git").mkdir(parents=True)
    cfg = AptConfig(projects_dir=str(projects), deploy_repo_path=str(repo),
                    pages_base_url="https://eunj-it.github.io/apt-pages")
    calls = []

    def dry_run(cmd, capture_output=True, text=True):
        calls.append(cmd)
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    url = deploy(p, cfg, run=dry_run)
    assert url == "https://eunj-it.github.io/apt-pages/래미안-테스트/"
    assert [c[3] for c in calls] == ["add", "commit", "push"]
    assert os.path.isfile(os.path.join(str(repo), "래미안-테스트", "index.html"))

    # 5) 저장된 project.json 왕복 확인
    assert load_project(str(projects), "래미안-테스트").copy.hero_headline == "도심 속 프리미엄"
