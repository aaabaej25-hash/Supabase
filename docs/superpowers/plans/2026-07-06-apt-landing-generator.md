# 아파트 랜딩페이지 자동 생성기 (apt_landing) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 아파트 정보·사진·참고 URL을 입력하면 Ollama로 카피를 생성하고, 정적 랜딩페이지를 빌드해 GitHub Pages에 배포하는 로컬 FastAPI 웹앱.

**Architecture:** `apt_landing/` 패키지(youtube_summarizer와 형제). 파일 기반 저장(`projects/<슬러그>/project.json` + `photos/` + `build/`). 관리 UI는 서버 렌더링 HTML, 랜딩페이지는 Jinja2로 빌드한 순수 정적 사이트, 배포는 로컬에 클론된 `apt-pages` 리포에 git push.

**Tech Stack:** Python 3.10+, FastAPI + uvicorn, Jinja2, httpx, BeautifulSoup4, Pillow, ollama, pytest.

**Spec:** `docs/superpowers/specs/2026-07-06-apt-landing-generator-design.md`

## Global Constraints

- 기존 코드 스타일을 따른다: dataclass 모델, 모듈 수준 함수, 한국어 에러 메시지 (youtube_summarizer 참조)
- 에러 원칙: 죽지 않고, 무엇이 잘못됐는지 화면에 보여주고, 재시도 가능하게
- 스타일 추출 실패 시 기본 스타일로 폴백하되 UI에 폴백 사실 명시 (조용한 폴백 금지)
- 카피 JSON 파싱 실패 시 1회 자동 재시도, 재실패 시 원문을 보여주고 수동 편집 유도
- 랜딩페이지 섹션: 히어로(항상 처음) → [핵심정보·입지·갤러리 = 순서 가변] → 문의 CTA(항상 마지막)
- 문의는 카카오톡 링크 버튼만 — 랜딩페이지에 서버 통신 코드 금지
- 매물 데이터(`projects/`)는 git에 커밋하지 않는다
- 경로는 항상 `os.path.join` 사용 (Windows 환경)
- 모든 명령은 리포 루트 `C:\youtube`에서 실행

---

### Task 1: 의존성 및 설정 (`apt_landing.config`)

**Files:**
- Create: `apt_landing/__init__.py` (빈 파일)
- Create: `apt_landing/config.py`
- Modify: `requirements.txt` (의존성 추가)
- Modify: `config.toml` (`[apt_landing]` 섹션 추가)
- Modify: `.gitignore` (`projects/` 추가, 파일 없으면 생성)
- Test: `tests/test_apt_config.py`

**Interfaces:**
- Consumes: 없음 (첫 태스크)
- Produces: `AptConfig` dataclass — 필드 `ollama_model: str`, `projects_dir: str`, `deploy_repo_path: str`, `pages_base_url: str`. `load_config(path: str = "config.toml") -> AptConfig`

- [ ] **Step 1: 의존성 추가 및 설치**

`requirements.txt` 끝에 추가:

```
fastapi
uvicorn
jinja2
httpx
beautifulsoup4
pillow
python-multipart
```

Run: `pip install -r requirements.txt`
Expected: 에러 없이 설치 완료

- [ ] **Step 2: 실패하는 테스트 작성**

`tests/test_apt_config.py`:

```python
import os

from apt_landing.config import AptConfig, load_config


def test_load_config_missing_file_returns_defaults(tmp_path):
    cfg = load_config(os.path.join(str(tmp_path), "없는파일.toml"))
    assert cfg == AptConfig()


def test_load_config_reads_apt_landing_section(tmp_path):
    p = tmp_path / "config.toml"
    p.write_text(
        'ollama_model = "llama3.1"\n'  # youtube_summarizer용 최상위 키는 무시되어야 함
        "[apt_landing]\n"
        'ollama_model = "qwen2"\n'
        'projects_dir = "D:\\\\data\\\\projects"\n'
        'deploy_repo_path = "C:\\\\youtube\\\\apt-pages"\n'
        'pages_base_url = "https://eunj-it.github.io/apt-pages"\n',
        encoding="utf-8",
    )
    cfg = load_config(str(p))
    assert cfg.ollama_model == "qwen2"
    assert cfg.projects_dir == "D:\\data\\projects"
    assert cfg.deploy_repo_path == "C:\\youtube\\apt-pages"
    assert cfg.pages_base_url == "https://eunj-it.github.io/apt-pages"


def test_load_config_section_missing_returns_defaults(tmp_path):
    p = tmp_path / "config.toml"
    p.write_text('ollama_model = "llama3.1"\n', encoding="utf-8")
    assert load_config(str(p)) == AptConfig()
```

- [ ] **Step 3: 테스트 실패 확인**

Run: `pytest tests/test_apt_config.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'apt_landing'`

- [ ] **Step 4: 구현**

`apt_landing/__init__.py`: 빈 파일 생성.

`apt_landing/config.py`:

```python
from dataclasses import dataclass
import os

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib


@dataclass
class AptConfig:
    ollama_model: str = "llama3.1"
    projects_dir: str = "projects"
    deploy_repo_path: str = "C:\\youtube\\apt-pages"
    pages_base_url: str = "https://eunj-it.github.io/apt-pages"


def load_config(path: str = "config.toml") -> AptConfig:
    if not os.path.exists(path):
        return AptConfig()
    with open(path, "rb") as f:
        data = tomllib.load(f).get("apt_landing", {})
    return AptConfig(
        ollama_model=data.get("ollama_model", AptConfig.ollama_model),
        projects_dir=data.get("projects_dir", AptConfig.projects_dir),
        deploy_repo_path=data.get("deploy_repo_path", AptConfig.deploy_repo_path),
        pages_base_url=data.get("pages_base_url", AptConfig.pages_base_url),
    )
```

- [ ] **Step 5: 테스트 통과 확인**

Run: `pytest tests/test_apt_config.py -v`
Expected: PASS (3 passed)

- [ ] **Step 6: 설정 파일·gitignore 수정**

`config.toml` 끝에 추가 (기존 최상위 키들 아래):

```toml
[apt_landing]
ollama_model = "llama3.1"
projects_dir = "projects"
deploy_repo_path = "C:\\youtube\\apt-pages"
pages_base_url = "https://eunj-it.github.io/apt-pages"
```

`.gitignore`에 아래 줄 추가 (파일 없으면 생성):

```
projects/
```

Run: `pytest tests/ -v` (기존 youtube_summarizer 테스트가 config.toml 변경에 깨지지 않는지 확인)
Expected: 전부 PASS

- [ ] **Step 7: Commit**

```bash
git add apt_landing/ tests/test_apt_config.py requirements.txt config.toml .gitignore
git commit -m "feat(apt_landing): 패키지 스캐폴드 및 설정 로더"
```

---

### Task 2: 데이터 모델 (`apt_landing.models`)

**Files:**
- Create: `apt_landing/models.py`
- Test: `tests/test_apt_models.py`

**Interfaces:**
- Consumes: 없음
- Produces:
  - `StyleGuide(primary_color: str, accent_color: str, background_color: str, section_order: list[str], tone: str, extracted: bool)` — 기본값 내장, `extracted=False`면 폴백 상태
  - `Copy(hero_headline, hero_sub, info_summary, location_paragraph, gallery_caption, cta_text)` — 전부 `str`, 기본 `""`
  - `UnitType(name: str, price: str)`
  - `Project(slug, name, address, move_in, highlights, units: list[UnitType], kakao_link, reference_url, photos: list[str], status: str, deployed_url: str, style: StyleGuide, copy: Copy)` — `status`는 `"draft" | "copy_done" | "deployed"`
  - `COPY_SECTIONS: list[str]` — Copy 필드명 6개
  - `slugify(name: str) -> str`
  - `project_dir(base_dir: str, slug: str) -> str`
  - `save_project(base_dir: str, p: Project) -> None` / `load_project(base_dir: str, slug: str) -> Project` / `list_projects(base_dir: str) -> list[Project]`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_apt_models.py`:

```python
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
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `pytest tests/test_apt_models.py -v`
Expected: FAIL — `ImportError` (models 모듈 없음)

- [ ] **Step 3: 구현**

`apt_landing/models.py`:

```python
import json
import os
import re
import unicodedata
from dataclasses import asdict, dataclass, field

DEFAULT_SECTION_ORDER = ["info", "location", "gallery"]

COPY_SECTIONS = [
    "hero_headline",
    "hero_sub",
    "info_summary",
    "location_paragraph",
    "gallery_caption",
    "cta_text",
]


@dataclass
class StyleGuide:
    primary_color: str = "#1a3c5e"
    accent_color: str = "#c8a45e"
    background_color: str = "#ffffff"
    section_order: list[str] = field(default_factory=lambda: list(DEFAULT_SECTION_ORDER))
    tone: str = "신뢰감 있고 정중한 분양 안내 톤"
    extracted: bool = False


@dataclass
class Copy:
    hero_headline: str = ""
    hero_sub: str = ""
    info_summary: str = ""
    location_paragraph: str = ""
    gallery_caption: str = ""
    cta_text: str = ""


@dataclass
class UnitType:
    name: str = ""
    price: str = ""


@dataclass
class Project:
    slug: str
    name: str = ""
    address: str = ""
    move_in: str = ""
    highlights: str = ""
    units: list[UnitType] = field(default_factory=list)
    kakao_link: str = ""
    reference_url: str = ""
    photos: list[str] = field(default_factory=list)
    status: str = "draft"
    deployed_url: str = ""
    style: StyleGuide = field(default_factory=StyleGuide)
    copy: Copy = field(default_factory=Copy)


def slugify(name: str) -> str:
    s = unicodedata.normalize("NFC", name.strip().lower())
    s = re.sub(r"[^0-9a-z가-힣]+", "-", s)
    return s.strip("-") or "project"


def project_dir(base_dir: str, slug: str) -> str:
    return os.path.join(base_dir, slug)


def save_project(base_dir: str, p: Project) -> None:
    d = project_dir(base_dir, p.slug)
    os.makedirs(os.path.join(d, "photos"), exist_ok=True)
    with open(os.path.join(d, "project.json"), "w", encoding="utf-8") as f:
        json.dump(asdict(p), f, ensure_ascii=False, indent=2)


def _project_from_dict(data: dict) -> Project:
    return Project(
        slug=data["slug"],
        name=data.get("name", ""),
        address=data.get("address", ""),
        move_in=data.get("move_in", ""),
        highlights=data.get("highlights", ""),
        units=[UnitType(**u) for u in data.get("units", [])],
        kakao_link=data.get("kakao_link", ""),
        reference_url=data.get("reference_url", ""),
        photos=data.get("photos", []),
        status=data.get("status", "draft"),
        deployed_url=data.get("deployed_url", ""),
        style=StyleGuide(**data.get("style", {})),
        copy=Copy(**data.get("copy", {})),
    )


def load_project(base_dir: str, slug: str) -> Project:
    path = os.path.join(project_dir(base_dir, slug), "project.json")
    with open(path, encoding="utf-8") as f:
        return _project_from_dict(json.load(f))


def list_projects(base_dir: str) -> list[Project]:
    if not os.path.isdir(base_dir):
        return []
    result = []
    for name in sorted(os.listdir(base_dir)):
        if os.path.isfile(os.path.join(base_dir, name, "project.json")):
            result.append(load_project(base_dir, name))
    return result
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `pytest tests/test_apt_models.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add apt_landing/models.py tests/test_apt_models.py
git commit -m "feat(apt_landing): Project/StyleGuide/Copy 모델 및 파일 저장소"
```

---

### Task 3: Ollama 클라이언트 + 카피 생성 (`apt_landing.copywriter`)

**Files:**
- Create: `apt_landing/ollama_client.py`
- Create: `apt_landing/copywriter.py`
- Test: `tests/test_apt_copywriter.py`

**Interfaces:**
- Consumes: `models.Project`, `models.Copy`, `models.COPY_SECTIONS`
- Produces:
  - `ollama_client.ollama_chat(model: str, prompt: str) -> str` — 실패 시 `RuntimeError`(한국어 안내)
  - `copywriter.CopyParseError(RuntimeError)` — 속성 `raw: str` (LLM 원문)
  - `copywriter.generate_copy(project: Project, model: str, chat=ollama_chat) -> Copy` — 파싱 실패 시 1회 재시도 후 `CopyParseError`
  - `copywriter.regenerate_section(project: Project, section: str, model: str, chat=ollama_chat) -> str` — 한 섹션 텍스트만 반환

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_apt_copywriter.py`:

```python
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
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `pytest tests/test_apt_copywriter.py -v`
Expected: FAIL — `ImportError`

- [ ] **Step 3: 구현**

`apt_landing/ollama_client.py` (youtube_summarizer의 `_ollama_chat` 패턴 재사용):

```python
def ollama_chat(model: str, prompt: str) -> str:
    try:
        import ollama
        resp = ollama.chat(model=model, messages=[{"role": "user", "content": prompt}])
        return resp["message"]["content"]
    except Exception as e:
        raise RuntimeError(
            f"Ollama 호출 실패. 'ollama serve' 실행 및 'ollama pull {model}' 확인: {e}"
        )
```

`apt_landing/copywriter.py`:

```python
import json

from .models import COPY_SECTIONS, Copy, Project
from .ollama_client import ollama_chat


class CopyParseError(RuntimeError):
    def __init__(self, raw: str):
        super().__init__(f"카피 JSON 파싱 실패: {raw[:200]}")
        self.raw = raw


_SECTION_LABELS = {
    "hero_headline": "히어로 헤드라인 (한 줄, 15자 내외)",
    "hero_sub": "히어로 서브 문구 (한 줄)",
    "info_summary": "핵심 정보 요약 (2~3문장)",
    "location_paragraph": "입지 설명 문단 (3~4문장)",
    "gallery_caption": "사진 갤러리 캡션 (한 줄)",
    "cta_text": "카카오톡 문의 버튼 문구 (한 줄, 10자 내외)",
}


def _project_brief(p: Project) -> str:
    units = ", ".join(f"{u.name}: {u.price}" for u in p.units) or "미정"
    return (
        f"- 단지명: {p.name}\n"
        f"- 위치: {p.address}\n"
        f"- 입주시기: {p.move_in}\n"
        f"- 평형/가격: {units}\n"
        f"- 특장점: {p.highlights}"
    )


_COPY_PROMPT = (
    "당신은 부동산 분양 카피라이터입니다. 아래 아파트 정보로 랜딩페이지 카피를 한국어로 작성하세요.\n"
    "톤: {tone}\n\n"
    "아파트 정보:\n{brief}\n\n"
    "반드시 아래 JSON 형식만 출력하세요(설명·코드블록 금지):\n"
    '{{"hero_headline": "...", "hero_sub": "...", "info_summary": "...", '
    '"location_paragraph": "...", "gallery_caption": "...", "cta_text": "..."}}'
)

_SECTION_PROMPT = (
    "당신은 부동산 분양 카피라이터입니다. 아래 아파트 정보로 랜딩페이지의 "
    "'{label}' 문구 하나만 한국어로 작성하세요. 문구 텍스트만 출력하고 설명·따옴표는 금지합니다.\n"
    "톤: {tone}\n\n아파트 정보:\n{brief}"
)


def _extract_json(raw: str) -> dict:
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1:
        raise CopyParseError(raw)
    try:
        return json.loads(raw[start : end + 1])
    except json.JSONDecodeError:
        raise CopyParseError(raw)


def generate_copy(project: Project, model: str, chat=ollama_chat) -> Copy:
    prompt = _COPY_PROMPT.format(tone=project.style.tone, brief=_project_brief(project))
    raw = chat(model, prompt)
    try:
        data = _extract_json(raw)
    except CopyParseError:
        raw = chat(model, prompt)  # 1회 자동 재시도
        data = _extract_json(raw)
    return Copy(**{k: str(data.get(k, "")) for k in COPY_SECTIONS})


def regenerate_section(project: Project, section: str, model: str, chat=ollama_chat) -> str:
    if section not in COPY_SECTIONS:
        raise ValueError(f"알 수 없는 섹션: {section}")
    prompt = _SECTION_PROMPT.format(
        label=_SECTION_LABELS[section], tone=project.style.tone, brief=_project_brief(project)
    )
    return chat(model, prompt).strip()
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `pytest tests/test_apt_copywriter.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add apt_landing/ollama_client.py apt_landing/copywriter.py tests/test_apt_copywriter.py
git commit -m "feat(apt_landing): Ollama 카피 생성 (전체 + 섹션별 재생성)"
```

---

### Task 4: 참고 URL 스타일 추출 (`apt_landing.style_extractor`)

**Files:**
- Create: `apt_landing/style_extractor.py`
- Test: `tests/test_apt_style_extractor.py`

**Interfaces:**
- Consumes: `models.StyleGuide`, `models.DEFAULT_SECTION_ORDER`, `ollama_client.ollama_chat`
- Produces: `extract_style(url: str, model: str, chat=ollama_chat, fetch=None) -> StyleGuide` — 성공 시 `extracted=True`, 어떤 실패든 기본 `StyleGuide()`(`extracted=False`) 반환. **예외를 밖으로 던지지 않는다** (앱은 `extracted` 플래그로 폴백 여부를 UI에 표시)

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_apt_style_extractor.py`:

```python
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
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `pytest tests/test_apt_style_extractor.py -v`
Expected: FAIL — `ImportError`

- [ ] **Step 3: 구현**

`apt_landing/style_extractor.py`:

```python
import re
from collections import Counter

import httpx
from bs4 import BeautifulSoup

from .models import DEFAULT_SECTION_ORDER, StyleGuide
from .ollama_client import ollama_chat

_HEX_RE = re.compile(r"#[0-9a-fA-F]{6}\b")

# 회색조(채도 낮음)·순백/순흑 계열은 브랜드 색이 아니므로 제외
def _is_chromatic(hex_color: str) -> bool:
    r, g, b = (int(hex_color[i : i + 2], 16) for i in (1, 3, 5))
    return (max(r, g, b) - min(r, g, b)) >= 24


_SECTION_KEYWORDS = {
    "info": ["세대", "평형", "가격", "타입", "분양가", "공급"],
    "location": ["입지", "위치", "교통", "학군", "인프라"],
    "gallery": ["갤러리", "사진", "전경", "조감도", "투시도"],
}

_TONE_PROMPT = (
    "다음은 부동산 랜딩페이지의 텍스트입니다. 이 카피의 톤(분위기)을 "
    "한국어 한 문장으로 요약하세요. 문장만 출력하세요.\n\n{text}"
)


def _fetch(url: str) -> str:
    resp = httpx.get(url, timeout=15, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()
    return resp.text


def _extract_colors(html: str) -> list[str]:
    counts = Counter(c.lower() for c in _HEX_RE.findall(html) if _is_chromatic(c.lower()))
    return [c for c, _ in counts.most_common(2)]


def _guess_section_order(soup: BeautifulSoup) -> list[str]:
    order = []
    for h in soup.find_all(["h1", "h2", "h3"]):
        text = h.get_text()
        for section, keywords in _SECTION_KEYWORDS.items():
            if section not in order and any(k in text for k in keywords):
                order.append(section)
    order += [s for s in DEFAULT_SECTION_ORDER if s not in order]
    return order


def extract_style(url: str, model: str, chat=ollama_chat, fetch=None) -> StyleGuide:
    try:
        html = (fetch or _fetch)(url)
        colors = _extract_colors(html)
        if not colors:
            return StyleGuide()  # 추출 빈약 → 폴백
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(" ", strip=True)[:2000]
        tone = chat(model, _TONE_PROMPT.format(text=text)).strip() or StyleGuide().tone
        return StyleGuide(
            primary_color=colors[0],
            accent_color=colors[1] if len(colors) > 1 else StyleGuide().accent_color,
            section_order=_guess_section_order(soup),
            tone=tone,
            extracted=True,
        )
    except Exception:
        return StyleGuide()  # 어떤 실패든 기본 스타일 폴백 (UI가 extracted로 표시)
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `pytest tests/test_apt_style_extractor.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add apt_landing/style_extractor.py tests/test_apt_style_extractor.py
git commit -m "feat(apt_landing): 참고 URL 스타일 추출 (색상·섹션 순서·톤, 실패 시 폴백)"
```

---

### Task 5: 정적 사이트 빌더 (`apt_landing.builder` + 랜딩 템플릿)

**Files:**
- Create: `apt_landing/templates/landing.html.j2`
- Create: `apt_landing/builder.py`
- Test: `tests/test_apt_builder.py`

**Interfaces:**
- Consumes: `models.Project`, `models.project_dir`
- Produces: `build(project: Project, base_dir: str) -> tuple[str, list[str]]` — `(build_dir 절대/상대 경로, 실패한 사진 파일명 목록)`. `build_dir/index.html` + `build_dir/photos/*.webp` 생성. 사진 처리 실패는 해당 파일만 건너뛰고 실패 목록으로 반환

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_apt_builder.py`:

```python
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
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `pytest tests/test_apt_builder.py -v`
Expected: FAIL — `ImportError`

- [ ] **Step 3: 랜딩 템플릿 작성**

`apt_landing/templates/landing.html.j2`:

```html
<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{ project.name }}</title>
<style>
:root { --primary: {{ style.primary_color }}; --accent: {{ style.accent_color }}; --bg: {{ style.background_color }}; }
* { margin: 0; box-sizing: border-box; }
body { font-family: 'Pretendard', 'Malgun Gothic', sans-serif; background: var(--bg); color: #222; line-height: 1.6; }
.hero { min-height: 70vh; display: flex; flex-direction: column; justify-content: center; align-items: center;
  text-align: center; color: #fff; background: var(--primary); background-size: cover; background-position: center;
  padding: 4rem 1.5rem; text-shadow: 0 1px 8px rgba(0,0,0,.5); }
.hero h1 { font-size: clamp(1.8rem, 5vw, 3rem); margin-bottom: 1rem; }
.hero p { font-size: clamp(1rem, 2.5vw, 1.3rem); }
section { max-width: 860px; margin: 0 auto; padding: 3.5rem 1.5rem; }
section h2 { color: var(--primary); font-size: 1.6rem; margin-bottom: 1.2rem;
  border-left: 5px solid var(--accent); padding-left: .8rem; }
table { width: 100%; border-collapse: collapse; margin-top: 1rem; }
th, td { border: 1px solid #ddd; padding: .7rem 1rem; text-align: left; }
th { background: var(--primary); color: #fff; }
.gallery { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: .8rem; margin-top: 1rem; }
.gallery img { width: 100%; height: 200px; object-fit: cover; border-radius: 8px; }
.cta { text-align: center; background: var(--primary); color: #fff; max-width: none; }
.cta a { display: inline-block; margin-top: 1.2rem; padding: 1rem 2.5rem; border-radius: 999px;
  background: #FEE500; color: #191919; font-weight: bold; font-size: 1.15rem; text-decoration: none; }
footer { text-align: center; padding: 1.5rem; color: #999; font-size: .85rem; }
</style>
</head>
<body>
<header class="hero"{% if photos %} style="background-image: linear-gradient(rgba(0,0,0,.45), rgba(0,0,0,.45)), url('photos/{{ photos[0] }}')"{% endif %}>
  <h1>{{ copy.hero_headline or project.name }}</h1>
  <p>{{ copy.hero_sub }}</p>
</header>

{% for section in style.section_order %}
{% if section == "info" %}
<section id="info">
  <h2>단지 안내</h2>
  <p>{{ copy.info_summary }}</p>
  <table>
    <tr><th>항목</th><th>내용</th></tr>
    <tr><td>단지명</td><td>{{ project.name }}</td></tr>
    <tr><td>위치</td><td>{{ project.address }}</td></tr>
    <tr><td>입주시기</td><td>{{ project.move_in }}</td></tr>
    {% for u in project.units %}
    <tr><td>{{ u.name }}</td><td>{{ u.price }}</td></tr>
    {% endfor %}
  </table>
</section>
{% elif section == "location" %}
<section id="location">
  <h2>입지 환경</h2>
  <p>{{ copy.location_paragraph }}</p>
</section>
{% elif section == "gallery" %}
{% if photos %}
<section id="gallery">
  <h2>단지 둘러보기</h2>
  <p>{{ copy.gallery_caption }}</p>
  <div class="gallery">
    {% for photo in photos %}<img src="photos/{{ photo }}" alt="{{ project.name }} 사진 {{ loop.index }}">{% endfor %}
  </div>
</section>
{% endif %}
{% endif %}
{% endfor %}

<section class="cta">
  <h2 style="color:#fff;border-color:var(--accent)">문의하기</h2>
  <p>{{ project.highlights }}</p>
  <a href="{{ project.kakao_link }}">{{ copy.cta_text or "카카오톡으로 문의하기" }}</a>
</section>
<footer>{{ project.name }}</footer>
</body>
</html>
```

- [ ] **Step 4: 빌더 구현**

`apt_landing/builder.py`:

```python
import os
import shutil

from jinja2 import Environment, FileSystemLoader
from PIL import Image

from .models import Project, project_dir

_TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")
_MAX_WIDTH = 1600


def _process_photo(src: str, dst: str) -> None:
    img = Image.open(src).convert("RGB")
    if img.width > _MAX_WIDTH:
        img = img.resize((_MAX_WIDTH, int(img.height * _MAX_WIDTH / img.width)))
    img.save(dst, "WEBP", quality=85)


def build(project: Project, base_dir: str) -> tuple[str, list[str]]:
    pdir = project_dir(base_dir, project.slug)
    build_dir = os.path.join(pdir, "build")
    shutil.rmtree(build_dir, ignore_errors=True)
    os.makedirs(os.path.join(build_dir, "photos"), exist_ok=True)

    processed, failed = [], []
    for name in project.photos:
        out_name = os.path.splitext(name)[0] + ".webp"
        try:
            _process_photo(
                os.path.join(pdir, "photos", name),
                os.path.join(build_dir, "photos", out_name),
            )
            processed.append(out_name)
        except Exception:
            failed.append(name)

    # 주의: select_autoescape는 .j2 확장자를 autoescape 대상으로 보지 않으므로 True 고정
    env = Environment(loader=FileSystemLoader(_TEMPLATE_DIR), autoescape=True)
    html = env.get_template("landing.html.j2").render(
        project=project, style=project.style, copy=project.copy, photos=processed
    )
    with open(os.path.join(build_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)
    return build_dir, failed
```

- [ ] **Step 5: 테스트 통과 확인**

Run: `pytest tests/test_apt_builder.py -v`
Expected: PASS (4 passed)

- [ ] **Step 6: Commit**

```bash
git add apt_landing/templates/landing.html.j2 apt_landing/builder.py tests/test_apt_builder.py
git commit -m "feat(apt_landing): 랜딩 템플릿 및 정적 사이트 빌더 (WebP 변환 포함)"
```

---

### Task 6: GitHub Pages 배포 (`apt_landing.deployer`)

**Files:**
- Create: `apt_landing/deployer.py`
- Test: `tests/test_apt_deployer.py`

**Interfaces:**
- Consumes: `models.Project`, `config.AptConfig`
- Produces:
  - `deploy(project: Project, cfg: AptConfig, run=subprocess.run) -> str` — 배포 URL 반환. `cfg.deploy_repo_path`가 git 리포가 아니면 `RuntimeError`(클론 안내). `build/`가 없으면 `RuntimeError`. git 실패 시 stderr 포함 `RuntimeError`. "nothing to commit"은 성공 취급
  - `undeploy(slug: str, cfg: AptConfig, run=subprocess.run) -> None` — 리포에서 매물 폴더 삭제 후 commit/push

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_apt_deployer.py`:

```python
import os
from types import SimpleNamespace

import pytest

from apt_landing.config import AptConfig
from apt_landing.deployer import deploy, undeploy
from apt_landing.models import Project


def make_env(tmp_path):
    repo = tmp_path / "apt-pages"
    (repo / ".git").mkdir(parents=True)
    projects = tmp_path / "projects"
    build = projects / "t-apt" / "build"
    build.mkdir(parents=True)
    (build / "index.html").write_text("<html>x</html>", encoding="utf-8")
    cfg = AptConfig(
        projects_dir=str(projects),
        deploy_repo_path=str(repo),
        pages_base_url="https://eunj-it.github.io/apt-pages",
    )
    return cfg


def ok_run(recorder):
    def run(cmd, capture_output=True, text=True):
        recorder.append(cmd)
        return SimpleNamespace(returncode=0, stdout="", stderr="")
    return run


def test_deploy_copies_build_and_pushes(tmp_path):
    cfg = make_env(tmp_path)
    calls = []
    url = deploy(Project(slug="t-apt"), cfg, run=ok_run(calls))
    assert url == "https://eunj-it.github.io/apt-pages/t-apt/"
    assert os.path.isfile(os.path.join(cfg.deploy_repo_path, "t-apt", "index.html"))
    git_subcmds = [c[3] for c in calls]  # ["git", "-C", repo, <subcmd>, ...]
    assert git_subcmds == ["add", "commit", "push"]


def test_deploy_fails_without_repo(tmp_path):
    cfg = make_env(tmp_path)
    cfg.deploy_repo_path = str(tmp_path / "없는리포")
    with pytest.raises(RuntimeError, match="배포 리포"):
        deploy(Project(slug="t-apt"), cfg, run=ok_run([]))


def test_deploy_fails_without_build(tmp_path):
    cfg = make_env(tmp_path)
    with pytest.raises(RuntimeError, match="빌드"):
        deploy(Project(slug="다른매물"), cfg, run=ok_run([]))


def test_deploy_surfaces_git_error(tmp_path):
    cfg = make_env(tmp_path)

    def fail_run(cmd, capture_output=True, text=True):
        return SimpleNamespace(returncode=1, stdout="", stderr="remote: 인증 실패")

    with pytest.raises(RuntimeError, match="인증 실패"):
        deploy(Project(slug="t-apt"), cfg, run=fail_run)


def test_undeploy_removes_folder(tmp_path):
    cfg = make_env(tmp_path)
    calls = []
    deploy(Project(slug="t-apt"), cfg, run=ok_run(calls))
    undeploy("t-apt", cfg, run=ok_run(calls))
    assert not os.path.isdir(os.path.join(cfg.deploy_repo_path, "t-apt"))
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `pytest tests/test_apt_deployer.py -v`
Expected: FAIL — `ImportError`

- [ ] **Step 3: 구현**

`apt_landing/deployer.py`:

```python
import os
import shutil
import subprocess

from .config import AptConfig
from .models import Project


def _git(repo: str, args: list[str], run) -> None:
    r = run(["git", "-C", repo] + args, capture_output=True, text=True)
    output = (r.stdout or "") + (r.stderr or "")
    if r.returncode != 0 and "nothing to commit" not in output:
        raise RuntimeError(f"git {args[0]} 실패:\n{output.strip()}")


def deploy(project: Project, cfg: AptConfig, run=subprocess.run) -> str:
    repo = cfg.deploy_repo_path
    if not os.path.isdir(os.path.join(repo, ".git")):
        raise RuntimeError(
            f"배포 리포가 없습니다: {repo}\n먼저 GitHub에 apt-pages 리포를 만들고 이 경로에 clone 하세요."
        )
    build_dir = os.path.join(cfg.projects_dir, project.slug, "build")
    if not os.path.isfile(os.path.join(build_dir, "index.html")):
        raise RuntimeError("빌드 결과가 없습니다. 먼저 미리보기를 실행해 빌드하세요.")

    target = os.path.join(repo, project.slug)
    shutil.rmtree(target, ignore_errors=True)
    shutil.copytree(build_dir, target)

    _git(repo, ["add", "-A"], run)
    _git(repo, ["commit", "-m", f"deploy: {project.slug}"], run)
    _git(repo, ["push"], run)
    return f"{cfg.pages_base_url.rstrip('/')}/{project.slug}/"


def undeploy(slug: str, cfg: AptConfig, run=subprocess.run) -> None:
    repo = cfg.deploy_repo_path
    shutil.rmtree(os.path.join(repo, slug), ignore_errors=True)
    _git(repo, ["add", "-A"], run)
    _git(repo, ["commit", "-m", f"undeploy: {slug}"], run)
    _git(repo, ["push"], run)
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `pytest tests/test_apt_deployer.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add apt_landing/deployer.py tests/test_apt_deployer.py
git commit -m "feat(apt_landing): GitHub Pages 배포/게시중단 (git push 기반)"
```

---

### Task 7: 관리 UI ① — 앱 골격, 매물 목록/생성/편집, 사진 업로드 (`apt_landing.app`)

**Files:**
- Create: `apt_landing/app.py`
- Create: `apt_landing/templates/admin/base.html`
- Create: `apt_landing/templates/admin/index.html`
- Create: `apt_landing/templates/admin/edit.html`
- Test: `tests/test_apt_app.py`

**Interfaces:**
- Consumes: `config.AptConfig`, `models.*`
- Produces: `create_app(cfg: AptConfig | None = None) -> FastAPI`. 라우트:
  - `GET /` 매물 목록, `POST /projects` 생성(form: `name`, checkbox `overwrite`) — 슬러그 충돌 시 덮어쓰기 미체크면 에러 표시
  - `GET /p/{slug}` 편집 화면, `POST /p/{slug}` 정보 저장 (form: `name, address, move_in, highlights, units_text, kakao_link, reference_url` — `units_text`는 줄마다 `평형|가격`)
  - `POST /p/{slug}/photos` 다중 업로드, `POST /p/{slug}/photos/{name}/delete`, `POST /p/{slug}/photos/{name}/up` (순서 위로)
  - Task 8이 이 앱에 라우트를 추가하므로 `create_app` 내부에서 `cfg`를 클로저로 쓰는 구조 유지

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_apt_app.py`:

```python
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
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `pytest tests/test_apt_app.py -v`
Expected: FAIL — `ImportError`

- [ ] **Step 3: 관리 템플릿 작성**

`apt_landing/templates/admin/base.html`:

```html
<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<title>APT 랜딩 생성기</title>
<style>
body { font-family: 'Malgun Gothic', sans-serif; max-width: 960px; margin: 2rem auto; padding: 0 1rem; }
label { display: block; margin-top: .8rem; font-weight: bold; }
input[type=text], textarea { width: 100%; padding: .45rem; margin-top: .2rem; box-sizing: border-box; }
button { margin-top: .6rem; padding: .45rem 1.1rem; cursor: pointer; }
.error { background: #fdecea; color: #b3261e; padding: .7rem; border-radius: 6px; margin: .8rem 0; white-space: pre-wrap; }
.notice { background: #e6f4ea; color: #1e7e34; padding: .7rem; border-radius: 6px; margin: .8rem 0; }
nav { margin-bottom: 1.5rem; } nav a { margin-right: 1rem; }
table { border-collapse: collapse; width: 100%; } td, th { border: 1px solid #ccc; padding: .5rem .8rem; text-align: left; }
iframe { width: 100%; height: 620px; border: 1px solid #ccc; margin-top: 1rem; }
.photo-row { display: flex; align-items: center; gap: .6rem; margin: .3rem 0; }
.photo-row img { height: 60px; border-radius: 4px; }
.inline { display: inline; }
</style>
</head>
<body>
<nav><a href="/">📋 매물 목록</a>{% if project %} | <a href="/p/{{ project.slug }}">✏️ 정보·사진</a> | <a href="/p/{{ project.slug }}/copy">📝 카피·미리보기</a> | <a href="/p/{{ project.slug }}/deploy">🚀 배포</a>{% endif %}</nav>
{% if error %}<div class="error">{{ error }}</div>{% endif %}
{% if notice %}<div class="notice">{{ notice }}</div>{% endif %}
{% block content %}{% endblock %}
</body>
</html>
```

`apt_landing/templates/admin/index.html`:

```html
{% extends "base.html" %}
{% block content %}
<h1>매물 목록</h1>
<form method="post" action="/projects">
  <label>새 매물 이름 <input type="text" name="name" required></label>
  <label><input type="checkbox" name="overwrite"> 같은 이름이 있으면 덮어쓰기</label>
  <button type="submit">만들기</button>
</form>
<table style="margin-top:1.5rem">
  <tr><th>매물</th><th>상태</th><th>배포 URL</th></tr>
  {% for p in projects %}
  <tr>
    <td><a href="/p/{{ p.slug }}">{{ p.name }}</a></td>
    <td>{{ {"draft": "초안", "copy_done": "카피 확정", "deployed": "배포됨"}[p.status] }}</td>
    <td>{% if p.deployed_url %}<a href="{{ p.deployed_url }}" target="_blank">{{ p.deployed_url }}</a>{% endif %}</td>
  </tr>
  {% endfor %}
</table>
{% endblock %}
```

`apt_landing/templates/admin/edit.html`:

```html
{% extends "base.html" %}
{% block content %}
<h1>{{ project.name }} — 정보·사진</h1>
<form method="post" action="/p/{{ project.slug }}">
  <label>단지명 <input type="text" name="name" value="{{ project.name }}"></label>
  <label>위치(주소) <input type="text" name="address" value="{{ project.address }}"></label>
  <label>입주시기 <input type="text" name="move_in" value="{{ project.move_in }}"></label>
  <label>평형/가격 (한 줄에 하나, "84A|15억" 형식)
    <textarea name="units_text" rows="4">{% for u in project.units %}{{ u.name }}|{{ u.price }}
{% endfor %}</textarea></label>
  <label>특장점 메모 <textarea name="highlights" rows="3">{{ project.highlights }}</textarea></label>
  <label>카카오톡 문의 링크 (채널 또는 오픈채팅) <input type="text" name="kakao_link" value="{{ project.kakao_link }}"></label>
  <label>참고 랜딩페이지 URL (선택) <input type="text" name="reference_url" value="{{ project.reference_url }}"></label>
  <button type="submit">저장</button>
</form>

<h2 style="margin-top:2rem">사진 ({{ project.photos|length }}장 — 첫 사진이 히어로 배경)</h2>
<form method="post" action="/p/{{ project.slug }}/photos" enctype="multipart/form-data">
  <input type="file" name="files" multiple accept="image/*">
  <button type="submit">업로드</button>
</form>
{% for photo in project.photos %}
<div class="photo-row">
  <img src="/p/{{ project.slug }}/photo-file/{{ photo }}" alt="{{ photo }}">
  <span>{{ photo }}</span>
  <form class="inline" method="post" action="/p/{{ project.slug }}/photos/{{ photo }}/up"><button>▲ 위로</button></form>
  <form class="inline" method="post" action="/p/{{ project.slug }}/photos/{{ photo }}/delete"><button>삭제</button></form>
</div>
{% endfor %}

<h2 style="margin-top:2rem">스타일</h2>
<p>
  {% if project.style.extracted %}✅ 참고 URL에서 추출된 스타일 사용 중 — 주조색 <code>{{ project.style.primary_color }}</code>, 톤: {{ project.style.tone }}
  {% else %}ℹ️ 기본 스타일 사용 중 (추출 실패 또는 미실행){% endif %}
</p>
<form method="post" action="/p/{{ project.slug }}/style">
  <button type="submit" {% if not project.reference_url %}disabled{% endif %}>참고 URL에서 스타일 추출</button>
  {% if not project.reference_url %}<span>← 참고 URL을 먼저 저장하세요</span>{% endif %}
</form>
{% endblock %}
```

- [ ] **Step 4: 앱 구현**

`apt_landing/app.py` (Task 8·9 라우트가 추가될 골격 — 이 태스크에서는 목록/생성/편집/사진까지):

```python
import os
import re

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from .config import AptConfig, load_config
from .models import (
    Project,
    UnitType,
    list_projects,
    load_project,
    project_dir,
    save_project,
    slugify,
)

_ADMIN_TEMPLATES = os.path.join(os.path.dirname(__file__), "templates", "admin")


def _parse_units(units_text: str) -> list[UnitType]:
    units = []
    for line in units_text.splitlines():
        line = line.strip()
        if not line:
            continue
        name, _, price = line.partition("|")
        units.append(UnitType(name=name.strip(), price=price.strip()))
    return units


def _safe_filename(filename: str) -> str:
    return re.sub(r"[^0-9a-zA-Z가-힣._-]", "-", os.path.basename(filename or "photo"))


def create_app(cfg: AptConfig | None = None) -> FastAPI:
    cfg = cfg or load_config()
    app = FastAPI()
    templates = Jinja2Templates(directory=_ADMIN_TEMPLATES)

    def render(name: str, request: Request, **ctx):
        return templates.TemplateResponse(request, name, ctx)

    @app.get("/")
    def index(request: Request, error: str = "", notice: str = ""):
        return render("index.html", request, projects=list_projects(cfg.projects_dir),
                      error=error, notice=notice)

    @app.post("/projects")
    def create_project(request: Request, name: str = Form(...), overwrite: str = Form("")):
        slug = slugify(name)
        exists = os.path.isfile(os.path.join(project_dir(cfg.projects_dir, slug), "project.json"))
        if exists and not overwrite:
            return render("index.html", request, projects=list_projects(cfg.projects_dir),
                          error=f"'{slug}' 매물이 이미 존재합니다. 덮어쓰기를 체크하거나 다른 이름을 쓰세요.",
                          notice="")
        save_project(cfg.projects_dir, Project(slug=slug, name=name.strip()))
        return RedirectResponse(f"/p/{slug}", status_code=303)

    @app.get("/p/{slug}")
    def edit(request: Request, slug: str, error: str = "", notice: str = ""):
        return render("edit.html", request, project=load_project(cfg.projects_dir, slug),
                      error=error, notice=notice)

    @app.post("/p/{slug}")
    def save(request: Request, slug: str, name: str = Form(""), address: str = Form(""),
             move_in: str = Form(""), highlights: str = Form(""), units_text: str = Form(""),
             kakao_link: str = Form(""), reference_url: str = Form("")):
        p = load_project(cfg.projects_dir, slug)
        p.name, p.address, p.move_in = name.strip(), address.strip(), move_in.strip()
        p.highlights, p.kakao_link, p.reference_url = highlights.strip(), kakao_link.strip(), reference_url.strip()
        p.units = _parse_units(units_text)
        save_project(cfg.projects_dir, p)
        return render("edit.html", request, project=p, error="", notice="저장했습니다.")

    @app.post("/p/{slug}/photos")
    def upload_photos(request: Request, slug: str, files: list[UploadFile] = File(...)):
        p = load_project(cfg.projects_dir, slug)
        photo_dir = os.path.join(project_dir(cfg.projects_dir, slug), "photos")
        os.makedirs(photo_dir, exist_ok=True)
        for f in files:
            name = f"{len(p.photos) + 1:02d}-{_safe_filename(f.filename)}"
            with open(os.path.join(photo_dir, name), "wb") as out:
                out.write(f.file.read())
            p.photos.append(name)
        save_project(cfg.projects_dir, p)
        return render("edit.html", request, project=p, error="",
                      notice=f"{len(files)}장 업로드했습니다.")

    @app.get("/p/{slug}/photo-file/{name}")
    def photo_file(slug: str, name: str):
        return FileResponse(os.path.join(project_dir(cfg.projects_dir, slug), "photos",
                                         os.path.basename(name)))

    @app.post("/p/{slug}/photos/{name}/delete")
    def delete_photo(request: Request, slug: str, name: str):
        p = load_project(cfg.projects_dir, slug)
        if name in p.photos:
            p.photos.remove(name)
            path = os.path.join(project_dir(cfg.projects_dir, slug), "photos", os.path.basename(name))
            if os.path.isfile(path):
                os.remove(path)
            save_project(cfg.projects_dir, p)
        return render("edit.html", request, project=p, error="", notice="삭제했습니다.")

    @app.post("/p/{slug}/photos/{name}/up")
    def photo_up(request: Request, slug: str, name: str):
        p = load_project(cfg.projects_dir, slug)
        if name in p.photos:
            i = p.photos.index(name)
            if i > 0:
                p.photos[i - 1], p.photos[i] = p.photos[i], p.photos[i - 1]
                save_project(cfg.projects_dir, p)
        return render("edit.html", request, project=p, error="", notice="")

    return app
```

- [ ] **Step 5: 테스트 통과 확인**

Run: `pytest tests/test_apt_app.py -v`
Expected: PASS (4 passed)

- [ ] **Step 6: Commit**

```bash
git add apt_landing/app.py apt_landing/templates/admin/ tests/test_apt_app.py
git commit -m "feat(apt_landing): 관리 UI - 매물 목록/생성/편집, 사진 업로드·순서·삭제"
```

---

### Task 8: 관리 UI ② — 스타일 추출, 카피 생성/편집, 미리보기

**Files:**
- Modify: `apt_landing/app.py` (`create_app` 내부에 라우트 추가 — Task 7의 라우트들 아래, `return app` 위)
- Create: `apt_landing/templates/admin/copy.html`
- Test: `tests/test_apt_app_copy.py`

**Interfaces:**
- Consumes: `style_extractor.extract_style`, `copywriter.generate_copy / regenerate_section / CopyParseError`, `builder.build`, `models.COPY_SECTIONS`
- Produces: 라우트 —
  - `POST /p/{slug}/style` 스타일 추출 실행 → edit 화면에 결과 표시 (`extracted=False`면 폴백 안내)
  - `GET /p/{slug}/copy` 카피 편집+미리보기 화면
  - `POST /p/{slug}/copy/generate` 전체 생성 (CopyParseError 시 원문을 error로 표시)
  - `POST /p/{slug}/copy/generate/{section}` 섹션 하나 재생성
  - `POST /p/{slug}/copy` 편집 내용 저장 (status가 draft면 copy_done으로)
  - `GET /preview/{slug}/` 빌드 후 index.html 반환, `GET /preview/{slug}/photos/{name}` 빌드된 사진 반환

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_apt_app_copy.py`:

```python
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
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `pytest tests/test_apt_app_copy.py -v`
Expected: FAIL — 404 또는 AttributeError (라우트·임포트 없음)

- [ ] **Step 3: copy.html 템플릿 작성**

`apt_landing/templates/admin/copy.html`:

```html
{% extends "base.html" %}
{% block content %}
<h1>{{ project.name }} — 카피·미리보기</h1>

<form method="post" action="/p/{{ project.slug }}/copy/generate">
  <button type="submit">🤖 전체 카피 생성 (Ollama)</button>
  <span>톤: {{ project.style.tone }}</span>
</form>

<form method="post" action="/p/{{ project.slug }}/copy">
  {% for section, label in sections %}
  <label>{{ label }}
    <textarea name="{{ section }}" rows="{{ 3 if section in ['info_summary', 'location_paragraph'] else 1 }}">{{ project.copy[section] }}</textarea>
  </label>
  <button type="submit" form="regen-{{ section }}">이 섹션만 재생성</button>
  {% endfor %}
  <hr>
  <button type="submit">카피 저장 (미리보기 갱신)</button>
</form>
{% for section, label in sections %}
<form id="regen-{{ section }}" method="post" action="/p/{{ project.slug }}/copy/generate/{{ section }}"></form>
{% endfor %}

<h2 style="margin-top:2rem">미리보기 (배포 결과와 동일)</h2>
{% if failed_photos %}<div class="error">사진 처리 실패(건너뜀): {{ failed_photos|join(", ") }}</div>{% endif %}
<iframe src="/preview/{{ project.slug }}/"></iframe>
{% endblock %}
```

참고: `project.copy[section]`이 동작하도록 라우트에서 `copy`를 dict로 넘긴다 (Step 4의 `_copy_ctx` 참조 — dataclass는 subscript 불가하므로 `asdict` 사용).

- [ ] **Step 4: 라우트 구현**

`apt_landing/app.py` 임포트 추가 (파일 상단):

```python
from dataclasses import asdict

from .builder import build
from .copywriter import CopyParseError, generate_copy, regenerate_section
from .models import COPY_SECTIONS, StyleGuide
from .ollama_client import ollama_chat
from .style_extractor import extract_style
```

주의: 테스트가 `monkeypatch.setattr(app_module, "ollama_chat", ...)` 하므로, 라우트에서 **모듈 전역을 통해** 호출한다 (아래 코드처럼 `chat=ollama_chat`를 기본 인자로 바인딩하지 말고 호출 시점에 참조).

`create_app` 내부, `return app` 앞에 추가:

```python
    _SECTION_LABELS_UI = [
        ("hero_headline", "히어로 헤드라인"),
        ("hero_sub", "히어로 서브 문구"),
        ("info_summary", "핵심 정보 요약"),
        ("location_paragraph", "입지 설명"),
        ("gallery_caption", "갤러리 캡션"),
        ("cta_text", "문의 버튼 문구"),
    ]

    def _copy_page(request: Request, p, error="", notice="", failed_photos=None):
        ctx_project = {**asdict(p), "slug": p.slug, "copy": asdict(p.copy)}
        return render("copy.html", request, project=ctx_project,
                      sections=_SECTION_LABELS_UI, error=error, notice=notice,
                      failed_photos=failed_photos or [])

    @app.get("/p/{slug}/copy")
    def copy_page(request: Request, slug: str):
        p = load_project(cfg.projects_dir, slug)
        # 미리보기 iframe이 어차피 빌드하지만, 사진 처리 실패 목록을 화면에 표시하기 위해
        # 여기서도 빌드해 failed를 수집한다 (스펙 5절: 실패한 사진은 목록에 표시)
        _build_dir, failed = build(p, cfg.projects_dir)
        return _copy_page(request, p, failed_photos=failed)

    @app.post("/p/{slug}/style")
    def run_style(request: Request, slug: str):
        p = load_project(cfg.projects_dir, slug)
        p.style = extract_style(p.reference_url, cfg.ollama_model, chat=ollama_chat)
        save_project(cfg.projects_dir, p)
        if p.style.extracted:
            notice, error = f"스타일 추출 완료 — 주조색 {p.style.primary_color}", ""
        else:
            notice, error = "", "스타일 추출에 실패해 기본 스타일을 사용합니다. (JS 렌더링 페이지는 지원 안 됨)"
        return render("edit.html", request, project=p, error=error, notice=notice)

    @app.post("/p/{slug}/copy/generate")
    def gen_copy(request: Request, slug: str):
        p = load_project(cfg.projects_dir, slug)
        try:
            p.copy = generate_copy(p, cfg.ollama_model, chat=ollama_chat)
            save_project(cfg.projects_dir, p)
            return _copy_page(request, p, notice="카피를 생성했습니다. 검토 후 수정하세요.")
        except CopyParseError as e:
            return _copy_page(request, p, error=f"카피 형식 오류 — 아래 원문을 참고해 직접 입력하세요:\n{e.raw}")
        except RuntimeError as e:
            return _copy_page(request, p, error=str(e))

    @app.post("/p/{slug}/copy/generate/{section}")
    def gen_section(request: Request, slug: str, section: str):
        p = load_project(cfg.projects_dir, slug)
        try:
            setattr(p.copy, section, regenerate_section(p, section, cfg.ollama_model, chat=ollama_chat))
            save_project(cfg.projects_dir, p)
            return _copy_page(request, p, notice="섹션을 재생성했습니다.")
        except (RuntimeError, ValueError) as e:
            return _copy_page(request, p, error=str(e))

    @app.post("/p/{slug}/copy")
    async def save_copy(request: Request, slug: str):
        form = await request.form()
        p = load_project(cfg.projects_dir, slug)
        for section in COPY_SECTIONS:
            setattr(p.copy, section, str(form.get(section, "")).strip())
        if p.status == "draft":
            p.status = "copy_done"
        save_project(cfg.projects_dir, p)
        return _copy_page(request, p, notice="카피를 저장했습니다.")

    @app.get("/preview/{slug}/")
    def preview(slug: str):
        p = load_project(cfg.projects_dir, slug)
        build_dir, _failed = build(p, cfg.projects_dir)
        return FileResponse(os.path.join(build_dir, "index.html"))

    @app.get("/preview/{slug}/photos/{name}")
    def preview_photo(slug: str, name: str):
        return FileResponse(os.path.join(project_dir(cfg.projects_dir, slug), "build",
                                         "photos", os.path.basename(name)))
```

`copywriter.generate_copy` / `regenerate_section` / `extract_style`의 `chat` 파라미터에 모듈 전역 `ollama_chat`을 명시적으로 넘기고 있으므로, 테스트의 `monkeypatch.setattr(app_module, "ollama_chat", ...)`이 적용된다.

- [ ] **Step 5: 테스트 통과 확인**

Run: `pytest tests/test_apt_app_copy.py -v`
Expected: PASS (6 passed)

Run: `pytest tests/test_apt_app.py -v` (Task 7 라우트 회귀 확인)
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add apt_landing/app.py apt_landing/templates/admin/copy.html tests/test_apt_app_copy.py
git commit -m "feat(apt_landing): 관리 UI - 스타일 추출, 카피 생성/편집, 실시간 미리보기"
```

---

### Task 9: 관리 UI ③ — 배포 화면 + 앱 엔트리포인트

**Files:**
- Modify: `apt_landing/app.py` (배포 라우트 추가)
- Create: `apt_landing/templates/admin/deploy.html`
- Create: `apt_landing/__main__.py`
- Test: `tests/test_apt_app_deploy.py`

**Interfaces:**
- Consumes: `deployer.deploy / undeploy`, `builder.build`
- Produces:
  - `GET /p/{slug}/deploy` 배포 화면, `POST /p/{slug}/deploy` 빌드+배포 실행(성공 시 `status="deployed"`, `deployed_url` 저장), `POST /p/{slug}/undeploy` 게시 중단(성공 시 `status="copy_done"`, URL 제거)
  - `python -m apt_landing` → `uvicorn` 으로 `127.0.0.1:8000` 서빙

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_apt_app_deploy.py`:

```python
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
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `pytest tests/test_apt_app_deploy.py -v`
Expected: FAIL — 404 (라우트 없음)

- [ ] **Step 3: deploy.html 템플릿 작성**

`apt_landing/templates/admin/deploy.html`:

```html
{% extends "base.html" %}
{% block content %}
<h1>{{ project.name }} — 배포</h1>

{% if project.deployed_url %}
<p>✅ 배포됨: <a href="{{ project.deployed_url }}" target="_blank">{{ project.deployed_url }}</a></p>
<p><input type="text" value="{{ project.deployed_url }}" readonly onclick="this.select()" style="width:100%"> ← 클릭해서 복사</p>
{% else %}
<p>아직 배포되지 않았습니다.</p>
{% endif %}

<form method="post" action="/p/{{ project.slug }}/deploy">
  <button type="submit">🚀 빌드하고 배포하기</button>
</form>
{% if project.deployed_url %}
<form method="post" action="/p/{{ project.slug }}/undeploy">
  <button type="submit">게시 중단 (페이지 내리기)</button>
</form>
{% endif %}
<p style="margin-top:1rem;color:#777">배포 후 GitHub Pages 반영까지 1~2분 걸릴 수 있습니다.</p>
{% endblock %}
```

- [ ] **Step 4: 라우트·엔트리포인트 구현**

`apt_landing/app.py` 임포트 추가:

```python
from .deployer import deploy, undeploy
```

`create_app` 내부, `return app` 앞에 추가 (deploy/undeploy는 monkeypatch가 적용되도록 모듈 전역으로 호출):

```python
    @app.get("/p/{slug}/deploy")
    def deploy_page(request: Request, slug: str, error: str = "", notice: str = ""):
        return render("deploy.html", request, project=load_project(cfg.projects_dir, slug),
                      error=error, notice=notice)

    @app.post("/p/{slug}/deploy")
    def run_deploy(request: Request, slug: str):
        p = load_project(cfg.projects_dir, slug)
        try:
            _build_dir, failed = build(p, cfg.projects_dir)
            p.deployed_url = deploy(p, cfg)
            p.status = "deployed"
            save_project(cfg.projects_dir, p)
            notice = "배포 완료!" + (f" (사진 {len(failed)}장 처리 실패로 제외됨)" if failed else "")
            return render("deploy.html", request, project=p, error="", notice=notice)
        except RuntimeError as e:
            return render("deploy.html", request, project=p, error=str(e), notice="")

    @app.post("/p/{slug}/undeploy")
    def run_undeploy(request: Request, slug: str):
        p = load_project(cfg.projects_dir, slug)
        try:
            undeploy(slug, cfg)
            p.deployed_url = ""
            p.status = "copy_done"
            save_project(cfg.projects_dir, p)
            return render("deploy.html", request, project=p, error="", notice="게시를 중단했습니다.")
        except RuntimeError as e:
            return render("deploy.html", request, project=p, error=str(e), notice="")
```

주의: Task 9 테스트가 `app_module.deploy`를 monkeypatch 하므로 라우트 본문에서 `deploy(p, cfg)`처럼 모듈 전역 이름으로 호출해야 한다. 단, 위 코드처럼 `from .deployer import deploy`로 임포트하면 `app_module.deploy`가 모듈 전역에 바인딩되어 monkeypatch가 적용된다. `run_deploy`에서 monkeypatch된 `deploy`가 빌드 산출물을 요구하지 않도록 라우트에서 `build()`를 먼저 호출하는 순서를 유지한다.

`apt_landing/__main__.py`:

```python
import uvicorn

from .app import create_app

if __name__ == "__main__":
    uvicorn.run(create_app(), host="127.0.0.1", port=8000)
```

- [ ] **Step 5: 테스트 통과 확인**

Run: `pytest tests/test_apt_app_deploy.py -v`
Expected: PASS (3 passed)

- [ ] **Step 6: 서버 기동 스모크 테스트**

Run: `python -c "from apt_landing.app import create_app; app = create_app(); print('routes:', len(app.routes))"`
Expected: `routes:` 뒤에 15 이상의 숫자, 에러 없음

- [ ] **Step 7: Commit**

```bash
git add apt_landing/app.py apt_landing/templates/admin/deploy.html apt_landing/__main__.py tests/test_apt_app_deploy.py
git commit -m "feat(apt_landing): 배포 화면 및 python -m apt_landing 엔트리포인트"
```

---

### Task 10: 통합 테스트 + 전체 검증

**Files:**
- Test: `tests/test_apt_integration.py`

**Interfaces:**
- Consumes: 전체 파이프라인 (`models` → `copywriter` → `builder` → `deployer` dry-run)
- Produces: 없음 (검증 태스크)

- [ ] **Step 1: 통합 테스트 작성**

`tests/test_apt_integration.py`:

```python
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
```

- [ ] **Step 2: 통합 테스트 실행**

Run: `pytest tests/test_apt_integration.py -v`
Expected: PASS (1 passed)

- [ ] **Step 3: 전체 테스트 스위트 실행**

Run: `pytest tests/ -v`
Expected: 전부 PASS (apt_landing 신규 테스트 + 기존 youtube_summarizer 테스트 모두)

- [ ] **Step 4: Commit**

```bash
git add tests/test_apt_integration.py
git commit -m "test(apt_landing): 전체 파이프라인 통합 테스트"
```

---

## 수동 E2E 체크리스트 (구현 완료 후, 사용자와 함께)

자동화 밖의 실제 연동 확인 — 스펙 6절 "수동 E2E":

1. GitHub에 `apt-pages` 공개 리포 생성 → Settings > Pages > main 브랜치 활성화 → `C:\youtube\apt-pages`에 clone → `config.toml`의 `deploy_repo_path`·`pages_base_url` 실제 값으로 수정
2. `ollama serve` 실행 상태에서 `python -m apt_landing` → `http://127.0.0.1:8000` 접속
3. 매물 1건 생성 → 정보·사진·카톡 오픈채팅 링크 입력 → (선택) 참고 URL 스타일 추출 → 카피 생성·수정 → 미리보기 확인 → 배포
4. 발급된 URL을 휴대폰에서 열어 카톡 버튼이 오픈채팅으로 연결되는지 확인
