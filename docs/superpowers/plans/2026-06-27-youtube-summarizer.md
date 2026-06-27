# 유튜브 스크립트 요약 도구 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 유튜브 URL을 받아 스크립트를 추출하고 로컬 LLM으로 한국어 요약 마크다운을 `C:\youtube\summaries`에 저장하는 CLI 도구를 만든다.

**Architecture:** 6단계 파이프라인(파싱 → 스크립트 확보 → 메타데이터 → 요약 → 렌더 → 저장)을 단일 책임 모듈로 분리한다. 각 모듈은 순수 함수에 가깝게 설계해 독립 테스트가 가능하다. 외부 의존성(yt-dlp, 자막 API, whisper, ollama)은 모킹으로 격리한다.

**Tech Stack:** Python 3.10+, yt-dlp, youtube-transcript-api, faster-whisper, ollama, pytest

## Global Constraints

- Python 3.10+ (dataclass, `X | None` 타입 힌트 사용)
- 출력 언어는 항상 한국어 (요약 프롬프트에 강제)
- 기본 저장 폴더: `C:\youtube\summaries` (없으면 자동 생성)
- 외부 네트워크/프로세스 호출(yt-dlp, 자막 API, whisper, ollama)은 테스트에서 모킹 — 실제 호출 금지
- 패키지 루트: `youtube_summarizer/`, 테스트 루트: `tests/`
- 설정 파일: `config.toml` (Python 3.11+ `tomllib`, 3.10은 `tomli` 폴백)
- 모든 사용자 대면 메시지는 한국어

---

### Task 1: 프로젝트 스캐폴딩 & 설정 로더

**Files:**
- Create: `youtube_summarizer/__init__.py`
- Create: `youtube_summarizer/config.py`
- Create: `config.toml`
- Create: `requirements.txt`
- Create: `tests/__init__.py`
- Test: `tests/test_config.py`

**Interfaces:**
- Produces:
  - `Config` dataclass: `output_dir: str`, `ollama_model: str`, `whisper_model: str`, `language: str`, `chunk_size: int`
  - `load_config(path: str = "config.toml") -> Config` — 파일이 없으면 기본값 Config 반환

- [ ] **Step 1: requirements.txt 작성**

```
yt-dlp
youtube-transcript-api
faster-whisper
ollama
tomli; python_version < "3.11"
pytest
```

- [ ] **Step 2: config.toml 작성**

```toml
output_dir    = "C:\\youtube\\summaries"
ollama_model  = "llama3.1"
whisper_model = "base"
language      = "ko"
chunk_size    = 3000
```

- [ ] **Step 3: 빈 패키지 파일 생성**

`youtube_summarizer/__init__.py` 와 `tests/__init__.py` 를 빈 파일로 생성.

- [ ] **Step 4: 실패하는 테스트 작성**

`tests/test_config.py`:

```python
from youtube_summarizer.config import load_config, Config


def test_load_config_reads_values(tmp_path):
    cfg_file = tmp_path / "config.toml"
    cfg_file.write_text(
        'output_dir = "D:\\\\out"\n'
        'ollama_model = "mymodel"\n'
        'whisper_model = "small"\n'
        'language = "ko"\n'
        'chunk_size = 1000\n',
        encoding="utf-8",
    )
    cfg = load_config(str(cfg_file))
    assert cfg.output_dir == "D:\\out"
    assert cfg.ollama_model == "mymodel"
    assert cfg.whisper_model == "small"
    assert cfg.chunk_size == 1000


def test_load_config_missing_file_returns_defaults():
    cfg = load_config("nonexistent_____.toml")
    assert isinstance(cfg, Config)
    assert cfg.language == "ko"
    assert cfg.chunk_size == 3000
```

- [ ] **Step 5: 테스트 실패 확인**

Run: `python -m pytest tests/test_config.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'youtube_summarizer.config'`

- [ ] **Step 6: config.py 구현**

```python
from dataclasses import dataclass
import os

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib


@dataclass
class Config:
    output_dir: str = "C:\\youtube\\summaries"
    ollama_model: str = "llama3.1"
    whisper_model: str = "base"
    language: str = "ko"
    chunk_size: int = 3000


def load_config(path: str = "config.toml") -> Config:
    if not os.path.exists(path):
        return Config()
    with open(path, "rb") as f:
        data = tomllib.load(f)
    return Config(
        output_dir=data.get("output_dir", Config.output_dir),
        ollama_model=data.get("ollama_model", Config.ollama_model),
        whisper_model=data.get("whisper_model", Config.whisper_model),
        language=data.get("language", Config.language),
        chunk_size=data.get("chunk_size", Config.chunk_size),
    )
```

- [ ] **Step 7: 테스트 통과 확인**

Run: `python -m pytest tests/test_config.py -v`
Expected: PASS (2 passed)

- [ ] **Step 8: Commit**

```bash
git add requirements.txt config.toml youtube_summarizer/ tests/
git commit -m "feat: 프로젝트 스캐폴딩 및 설정 로더"
```

---

### Task 2: URL 파싱 (video_id 추출)

**Files:**
- Create: `youtube_summarizer/extractor.py`
- Test: `tests/test_extractor_parse.py`

**Interfaces:**
- Produces:
  - `parse_video_id(url: str) -> str` — 다양한 유튜브 URL 형식에서 11자리 video_id 추출. 실패 시 `ValueError` 발생.

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_extractor_parse.py`:

```python
import pytest
from youtube_summarizer.extractor import parse_video_id


@pytest.mark.parametrize("url,expected", [
    ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
    ("https://youtu.be/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
    ("https://www.youtube.com/shorts/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
    ("https://youtube.com/watch?v=dQw4w9WgXcQ&t=10s", "dQw4w9WgXcQ"),
])
def test_parse_valid_urls(url, expected):
    assert parse_video_id(url) == expected


def test_parse_invalid_url_raises():
    with pytest.raises(ValueError):
        parse_video_id("https://example.com/notyoutube")
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python -m pytest tests/test_extractor_parse.py -v`
Expected: FAIL — `ModuleNotFoundError` 또는 `ImportError`

- [ ] **Step 3: parse_video_id 구현**

`youtube_summarizer/extractor.py`:

```python
import re

_ID = r"(?P<id>[0-9A-Za-z_-]{11})"
_PATTERNS = [
    re.compile(r"youtu\.be/" + _ID),
    re.compile(r"youtube\.com/watch\?(?:[^&]*&)*v=" + _ID),
    re.compile(r"youtube\.com/shorts/" + _ID),
    re.compile(r"youtube\.com/embed/" + _ID),
]


def parse_video_id(url: str) -> str:
    for pat in _PATTERNS:
        m = pat.search(url)
        if m:
            return m.group("id")
    raise ValueError(f"유튜브 video_id를 추출할 수 없습니다: {url}")
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/test_extractor_parse.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add youtube_summarizer/extractor.py tests/test_extractor_parse.py
git commit -m "feat: 유튜브 URL에서 video_id 추출"
```

---

### Task 3: 메타데이터 수집 (yt-dlp)

**Files:**
- Modify: `youtube_summarizer/extractor.py`
- Test: `tests/test_extractor_metadata.py`

**Interfaces:**
- Consumes: `parse_video_id` (동일 모듈)
- Produces:
  - `Metadata` dataclass: `title: str`, `channel: str`, `duration: str`, `url: str`
  - `fetch_metadata(video_id: str) -> Metadata` — yt-dlp로 정보 조회. 영상 접근 실패 시 `RuntimeError` 발생.
  - `_format_duration(seconds: int) -> str` — 초를 `MM:SS` / `H:MM:SS` 문자열로 변환.

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_extractor_metadata.py`:

```python
from unittest.mock import patch
import pytest
from youtube_summarizer.extractor import fetch_metadata, Metadata, _format_duration


def test_format_duration():
    assert _format_duration(75) == "01:15"
    assert _format_duration(3725) == "1:02:05"


def test_fetch_metadata_success():
    fake_info = {"title": "테스트 영상", "uploader": "채널A", "duration": 754}
    with patch("youtube_summarizer.extractor._extract_info", return_value=fake_info):
        md = fetch_metadata("dQw4w9WgXcQ")
    assert isinstance(md, Metadata)
    assert md.title == "테스트 영상"
    assert md.channel == "채널A"
    assert md.duration == "12:34"
    assert md.url == "https://youtu.be/dQw4w9WgXcQ"


def test_fetch_metadata_failure_raises():
    with patch("youtube_summarizer.extractor._extract_info", side_effect=Exception("private")):
        with pytest.raises(RuntimeError):
            fetch_metadata("dQw4w9WgXcQ")
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python -m pytest tests/test_extractor_metadata.py -v`
Expected: FAIL — `ImportError: cannot import name 'fetch_metadata'`

- [ ] **Step 3: extractor.py에 추가 구현**

`youtube_summarizer/extractor.py` 상단에 추가:

```python
from dataclasses import dataclass


@dataclass
class Metadata:
    title: str
    channel: str
    duration: str
    url: str


def _format_duration(seconds: int) -> str:
    h, rem = divmod(int(seconds), 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def _extract_info(video_id: str) -> dict:
    import yt_dlp
    url = f"https://youtu.be/{video_id}"
    with yt_dlp.YoutubeDL({"quiet": True, "skip_download": True}) as ydl:
        return ydl.extract_info(url, download=False)


def fetch_metadata(video_id: str) -> Metadata:
    try:
        info = _extract_info(video_id)
    except Exception as e:
        raise RuntimeError(f"영상 정보를 가져올 수 없습니다 (비공개/삭제/지역제한?): {e}")
    return Metadata(
        title=info.get("title", "제목 없음"),
        channel=info.get("uploader", "채널 미상"),
        duration=_format_duration(info.get("duration", 0)),
        url=f"https://youtu.be/{video_id}",
    )
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/test_extractor_metadata.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add youtube_summarizer/extractor.py tests/test_extractor_metadata.py
git commit -m "feat: yt-dlp로 영상 메타데이터 수집"
```

---

### Task 4: 스크립트 확보 (자막 → whisper 폴백)

**Files:**
- Create: `youtube_summarizer/transcript.py`
- Test: `tests/test_transcript.py`

**Interfaces:**
- Consumes: 없음
- Produces:
  - `TranscriptResult` dataclass: `text: str`, `source: str` (`"자막"` 또는 `"음성인식(whisper)"`)
  - `fetch_transcript(video_id: str, whisper_model: str) -> TranscriptResult` — 자막 API 시도 후 실패하면 whisper 폴백.
  - `_fetch_captions(video_id: str) -> str` — youtube-transcript-api 호출. 자막 없으면 예외.
  - `_whisper_transcribe(video_id: str, whisper_model: str) -> str` — yt-dlp 오디오 다운로드 + faster-whisper 전사. ffmpeg/whisper 미설치 시 안내 메시지 포함 `RuntimeError`.

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_transcript.py`:

```python
from unittest.mock import patch
import pytest
from youtube_summarizer.transcript import fetch_transcript, TranscriptResult


def test_uses_captions_when_available():
    with patch("youtube_summarizer.transcript._fetch_captions", return_value="자막 텍스트"):
        result = fetch_transcript("vid", "base")
    assert result == TranscriptResult(text="자막 텍스트", source="자막")


def test_falls_back_to_whisper():
    with patch("youtube_summarizer.transcript._fetch_captions", side_effect=Exception("no captions")), \
         patch("youtube_summarizer.transcript._whisper_transcribe", return_value="전사 텍스트") as w:
        result = fetch_transcript("vid", "base")
    w.assert_called_once_with("vid", "base")
    assert result.source == "음성인식(whisper)"
    assert result.text == "전사 텍스트"


def test_whisper_failure_propagates():
    with patch("youtube_summarizer.transcript._fetch_captions", side_effect=Exception("no captions")), \
         patch("youtube_summarizer.transcript._whisper_transcribe", side_effect=RuntimeError("ffmpeg 없음")):
        with pytest.raises(RuntimeError):
            fetch_transcript("vid", "base")
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python -m pytest tests/test_transcript.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'youtube_summarizer.transcript'`

- [ ] **Step 3: transcript.py 구현**

```python
from dataclasses import dataclass


@dataclass
class TranscriptResult:
    text: str
    source: str


def _fetch_captions(video_id: str) -> str:
    from youtube_transcript_api import YouTubeTranscriptApi
    entries = YouTubeTranscriptApi.get_transcript(video_id, languages=["ko", "en"])
    return " ".join(e["text"] for e in entries).strip()


def _whisper_transcribe(video_id: str, whisper_model: str) -> str:
    import os
    import tempfile
    try:
        import yt_dlp
        from faster_whisper import WhisperModel
    except ImportError as e:
        raise RuntimeError(
            "음성인식에 필요한 패키지가 없습니다. faster-whisper와 ffmpeg를 설치하세요: " + str(e)
        )
    tmpdir = tempfile.mkdtemp()
    out_tmpl = os.path.join(tmpdir, "%(id)s.%(ext)s")
    opts = {
        "quiet": True,
        "format": "bestaudio/best",
        "outtmpl": out_tmpl,
        "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3"}],
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([f"https://youtu.be/{video_id}"])
    except Exception as e:
        raise RuntimeError(f"오디오 다운로드 실패 (ffmpeg 설치 확인): {e}")
    audio_path = os.path.join(tmpdir, f"{video_id}.mp3")
    model = WhisperModel(whisper_model)
    segments, _ = model.transcribe(audio_path)
    return " ".join(seg.text for seg in segments).strip()


def fetch_transcript(video_id: str, whisper_model: str) -> TranscriptResult:
    try:
        text = _fetch_captions(video_id)
        return TranscriptResult(text=text, source="자막")
    except Exception:
        text = _whisper_transcribe(video_id, whisper_model)
        return TranscriptResult(text=text, source="음성인식(whisper)")
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/test_transcript.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add youtube_summarizer/transcript.py tests/test_transcript.py
git commit -m "feat: 자막 확보 및 whisper 폴백"
```

---

### Task 5: 청크 분할 & 요약 (Ollama)

**Files:**
- Create: `youtube_summarizer/summarizer.py`
- Test: `tests/test_summarizer.py`

**Interfaces:**
- Consumes: 없음
- Produces:
  - `Section` dataclass: `heading: str`, `bullets: list[str]`
  - `Summary` dataclass: `overview: list[str]`, `sections: list[Section]`
  - `chunk_text(text: str, chunk_size: int) -> list[str]` — 단어 경계 기준 분할.
  - `summarize(text: str, model: str, chunk_size: int) -> Summary` — 청크별 요약(map) 후 통합(reduce). Ollama 호출은 `_ollama_chat`로 격리.
  - `_ollama_chat(model: str, prompt: str) -> str` — ollama.chat 래퍼. 연결 실패 시 안내 메시지 포함 `RuntimeError`.

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_summarizer.py`:

```python
from unittest.mock import patch
from youtube_summarizer.summarizer import chunk_text, summarize, Summary, Section


def test_chunk_text_splits_by_size():
    text = "word " * 1000  # 5000자
    chunks = chunk_text(text, 1000)
    assert len(chunks) > 1
    assert all(len(c) <= 1100 for c in chunks)  # 단어 경계 여유


def test_chunk_text_short_returns_single():
    chunks = chunk_text("짧은 텍스트", 1000)
    assert chunks == ["짧은 텍스트"]


def test_summarize_builds_summary():
    fake_json = (
        '{"overview": ["핵심1", "핵심2"], '
        '"sections": [{"heading": "도입", "bullets": ["a", "b"]}]}'
    )
    with patch("youtube_summarizer.summarizer._ollama_chat", return_value=fake_json):
        result = summarize("어떤 긴 텍스트", "llama3.1", 1000)
    assert isinstance(result, Summary)
    assert result.overview == ["핵심1", "핵심2"]
    assert result.sections[0] == Section(heading="도입", bullets=["a", "b"])
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python -m pytest tests/test_summarizer.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'youtube_summarizer.summarizer'`

- [ ] **Step 3: summarizer.py 구현**

```python
import json
from dataclasses import dataclass


@dataclass
class Section:
    heading: str
    bullets: list[str]


@dataclass
class Summary:
    overview: list[str]
    sections: list[Section]


def chunk_text(text: str, chunk_size: int) -> list[str]:
    words = text.split(" ")
    chunks, current = [], ""
    for w in words:
        if len(current) + len(w) + 1 > chunk_size and current:
            chunks.append(current.strip())
            current = ""
        current += w + " "
    if current.strip():
        chunks.append(current.strip())
    return chunks or [text]


def _ollama_chat(model: str, prompt: str) -> str:
    try:
        import ollama
        resp = ollama.chat(model=model, messages=[{"role": "user", "content": prompt}])
        return resp["message"]["content"]
    except Exception as e:
        raise RuntimeError(
            f"Ollama 호출 실패. 'ollama serve' 실행 및 'ollama pull {model}' 확인: {e}"
        )


_PARTIAL_PROMPT = (
    "다음은 유튜브 스크립트의 일부입니다. 한국어로 핵심 내용을 간결한 불릿으로 정리하세요.\n\n{chunk}"
)

_FINAL_PROMPT = (
    "다음은 한 영상의 부분 요약들입니다. 이를 종합하여 반드시 한국어로, "
    "아래 JSON 형식만 출력하세요(설명·코드블록 금지):\n"
    '{{"overview": ["핵심 불릿 3~5개"], '
    '"sections": [{{"heading": "주제 제목", "bullets": ["내용"]}}]}}\n\n'
    "부분 요약:\n{partials}"
)


def _extract_json(raw: str) -> dict:
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1:
        raise RuntimeError(f"요약 JSON 파싱 실패: {raw[:200]}")
    return json.loads(raw[start : end + 1])


def summarize(text: str, model: str, chunk_size: int) -> Summary:
    chunks = chunk_text(text, chunk_size)
    partials = [_ollama_chat(model, _PARTIAL_PROMPT.format(chunk=c)) for c in chunks]
    final_raw = _ollama_chat(model, _FINAL_PROMPT.format(partials="\n\n".join(partials)))
    data = _extract_json(final_raw)
    sections = [Section(heading=s["heading"], bullets=s["bullets"]) for s in data.get("sections", [])]
    return Summary(overview=data.get("overview", []), sections=sections)
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/test_summarizer.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add youtube_summarizer/summarizer.py tests/test_summarizer.py
git commit -m "feat: 청크 분할 및 Ollama 섹션별 요약"
```

---

### Task 6: 마크다운 렌더링

**Files:**
- Create: `youtube_summarizer/renderer.py`
- Test: `tests/test_renderer.py`

**Interfaces:**
- Consumes: `Metadata` (extractor), `Summary`/`Section` (summarizer), `TranscriptResult.source`
- Produces:
  - `render(metadata: Metadata, summary: Summary, source: str, date: str) -> str` — frontmatter + 핵심 요약 + 섹션별 요약 마크다운 문자열.

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_renderer.py`:

```python
from youtube_summarizer.renderer import render
from youtube_summarizer.extractor import Metadata
from youtube_summarizer.summarizer import Summary, Section


def test_render_contains_all_parts():
    md = Metadata(title="제목", channel="채널", duration="12:34", url="https://youtu.be/x")
    summary = Summary(
        overview=["핵심1", "핵심2"],
        sections=[Section(heading="도입", bullets=["a", "b"])],
    )
    out = render(md, summary, source="자막", date="2026-06-27")
    assert "title: \"제목\"" in out
    assert "source: \"자막\"" in out
    assert "## 핵심 요약" in out
    assert "- 핵심1" in out
    assert "### 도입" in out
    assert "- a" in out
    assert "date: 2026-06-27" in out
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python -m pytest tests/test_renderer.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'youtube_summarizer.renderer'`

- [ ] **Step 3: renderer.py 구현**

```python
from youtube_summarizer.extractor import Metadata
from youtube_summarizer.summarizer import Summary


def render(metadata: Metadata, summary: Summary, source: str, date: str) -> str:
    lines = []
    lines.append("---")
    lines.append(f'title: "{metadata.title}"')
    lines.append(f'channel: "{metadata.channel}"')
    lines.append(f"url: {metadata.url}")
    lines.append(f'duration: "{metadata.duration}"')
    lines.append(f'source: "{source}"')
    lines.append(f"date: {date}")
    lines.append("---")
    lines.append("")
    lines.append(f"# {metadata.title}")
    lines.append("")
    lines.append("## 핵심 요약")
    for b in summary.overview:
        lines.append(f"- {b}")
    lines.append("")
    lines.append("## 섹션별 요약")
    lines.append("")
    for sec in summary.sections:
        lines.append(f"### {sec.heading}")
        for b in sec.bullets:
            lines.append(f"- {b}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/test_renderer.py -v`
Expected: PASS (1 passed)

- [ ] **Step 5: Commit**

```bash
git add youtube_summarizer/renderer.py tests/test_renderer.py
git commit -m "feat: 요약 데이터를 마크다운으로 렌더링"
```

---

### Task 7: 파일 저장 (슬러그 & 중복 방지)

**Files:**
- Create: `youtube_summarizer/writer.py`
- Test: `tests/test_writer.py`

**Interfaces:**
- Consumes: 없음
- Produces:
  - `slugify(title: str) -> str` — 공백→`-`, 특수문자 제거, 한글 유지, 길이 제한(80자).
  - `save(md: str, title: str, output_dir: str, date: str) -> str` — `<output_dir>/<date>-<slug>.md` 저장, 폴더 자동 생성, 중복 시 `-2`,`-3` 접미사. 저장 경로 반환.

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_writer.py`:

```python
import os
from youtube_summarizer.writer import slugify, save


def test_slugify_basic():
    assert slugify("Hello World!") == "Hello-World"


def test_slugify_keeps_korean():
    assert slugify("파이썬 강좌 #1") == "파이썬-강좌-1"


def test_save_creates_file(tmp_path):
    out = str(tmp_path / "summaries")
    path = save("내용", "제목", out, "2026-06-27")
    assert os.path.exists(path)
    assert path.endswith("2026-06-27-제목.md")
    assert open(path, encoding="utf-8").read() == "내용"


def test_save_avoids_overwrite(tmp_path):
    out = str(tmp_path / "summaries")
    p1 = save("a", "제목", out, "2026-06-27")
    p2 = save("b", "제목", out, "2026-06-27")
    assert p1 != p2
    assert p2.endswith("2026-06-27-제목-2.md")
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python -m pytest tests/test_writer.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'youtube_summarizer.writer'`

- [ ] **Step 3: writer.py 구현**

```python
import os
import re


def slugify(title: str) -> str:
    # 한글, 영숫자, 공백, 하이픈만 남김
    cleaned = re.sub(r"[^\w\s가-힣-]", "", title, flags=re.UNICODE)
    cleaned = re.sub(r"[\s_]+", "-", cleaned).strip("-")
    return cleaned[:80] or "untitled"


def save(md: str, title: str, output_dir: str, date: str) -> str:
    os.makedirs(output_dir, exist_ok=True)
    base = f"{date}-{slugify(title)}"
    path = os.path.join(output_dir, base + ".md")
    n = 2
    while os.path.exists(path):
        path = os.path.join(output_dir, f"{base}-{n}.md")
        n += 1
    with open(path, "w", encoding="utf-8") as f:
        f.write(md)
    return path
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/test_writer.py -v`
Expected: PASS (4 passed)

주의: `\w`는 유니코드 모드에서 한글을 포함하므로 `test_slugify_keeps_korean`이 통과해야 한다. 실패 시 정규식의 `가-힣` 중복은 무해하니 그대로 둔다.

- [ ] **Step 5: Commit**

```bash
git add youtube_summarizer/writer.py tests/test_writer.py
git commit -m "feat: 슬러그 생성 및 중복 방지 파일 저장"
```

---

### Task 8: CLI 진입점 (파이프라인 통합)

**Files:**
- Create: `youtube_summarizer/cli.py`
- Create: `youtube_summarizer/__main__.py`
- Test: `tests/test_cli.py`

**Interfaces:**
- Consumes: `load_config`, `parse_video_id`, `fetch_metadata`, `fetch_transcript`, `summarize`, `render`, `save`
- Produces:
  - `run(url: str, out: str | None, config_path: str, today: str) -> str` — 전체 파이프라인 실행, 저장 경로 반환. `out`이 주어지면 config의 output_dir을 오버라이드.
  - `main(argv: list[str] | None = None) -> int` — argparse로 인자 파싱(`url` 위치인자, `--out`, `--config`), 진행 메시지 출력, 에러를 잡아 한국어 메시지 출력 후 종료코드 반환.

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_cli.py`:

```python
from unittest.mock import patch
from youtube_summarizer.cli import run, main
from youtube_summarizer.extractor import Metadata
from youtube_summarizer.summarizer import Summary, Section
from youtube_summarizer.transcript import TranscriptResult


def test_run_pipeline(tmp_path):
    md = Metadata(title="제목", channel="채널", duration="01:00", url="https://youtu.be/x")
    summ = Summary(overview=["핵심"], sections=[Section(heading="h", bullets=["b"])])
    tr = TranscriptResult(text="스크립트", source="자막")
    with patch("youtube_summarizer.cli.parse_video_id", return_value="vid"), \
         patch("youtube_summarizer.cli.fetch_metadata", return_value=md), \
         patch("youtube_summarizer.cli.fetch_transcript", return_value=tr), \
         patch("youtube_summarizer.cli.summarize", return_value=summ):
        path = run("https://youtu.be/x", out=str(tmp_path), config_path="nonexistent.toml", today="2026-06-27")
    assert path.endswith("2026-06-27-제목.md")
    assert "## 핵심 요약" in open(path, encoding="utf-8").read()


def test_main_invalid_url_returns_error_code():
    with patch("youtube_summarizer.cli.parse_video_id", side_effect=ValueError("bad")):
        code = main(["not-a-url"])
    assert code == 1
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python -m pytest tests/test_cli.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'youtube_summarizer.cli'`

- [ ] **Step 3: cli.py 구현**

```python
import argparse
import sys
from datetime import date

from youtube_summarizer.config import load_config
from youtube_summarizer.extractor import parse_video_id, fetch_metadata
from youtube_summarizer.transcript import fetch_transcript
from youtube_summarizer.summarizer import summarize
from youtube_summarizer.renderer import render
from youtube_summarizer.writer import save


def run(url: str, out: str | None, config_path: str, today: str) -> str:
    cfg = load_config(config_path)
    output_dir = out or cfg.output_dir

    print("[1/5] URL 분석 중...")
    video_id = parse_video_id(url)

    print("[2/5] 영상 정보 수집 중...")
    metadata = fetch_metadata(video_id)

    print("[3/5] 스크립트 확보 중 (자막 또는 음성인식)...")
    transcript = fetch_transcript(video_id, cfg.whisper_model)
    print(f"      → 출처: {transcript.source}")

    print("[4/5] 한국어 요약 생성 중...")
    summary = summarize(transcript.text, cfg.ollama_model, cfg.chunk_size)

    print("[5/5] 마크다운 저장 중...")
    md = render(metadata, summary, transcript.source, today)
    path = save(md, metadata.title, output_dir, today)
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="유튜브 영상을 한국어로 요약해 마크다운으로 저장")
    parser.add_argument("url", help="유튜브 영상 URL")
    parser.add_argument("--out", default=None, help="저장 폴더 (config 오버라이드)")
    parser.add_argument("--config", default="config.toml", help="설정 파일 경로")
    args = parser.parse_args(argv)

    try:
        path = run(args.url, args.out, args.config, date.today().isoformat())
    except Exception as e:
        print(f"오류: {e}", file=sys.stderr)
        return 1
    print(f"완료: {path}")
    return 0
```

`youtube_summarizer/__main__.py`:

```python
import sys
from youtube_summarizer.cli import main

if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/test_cli.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: 전체 테스트 실행**

Run: `python -m pytest -v`
Expected: 모든 테스트 PASS

- [ ] **Step 6: Commit**

```bash
git add youtube_summarizer/cli.py youtube_summarizer/__main__.py tests/test_cli.py
git commit -m "feat: CLI 진입점 및 파이프라인 통합"
```

---

### Task 9: README & 수동 검증

**Files:**
- Create: `README.md`

**Interfaces:** 없음 (문서 및 수동 통합 테스트)

- [ ] **Step 1: README.md 작성**

````markdown
# 유튜브 스크립트 요약 도구

유튜브 링크를 넣으면 스크립트를 추출해 로컬 LLM으로 한국어 요약 마크다운을 생성합니다.

## 설치

```bash
pip install -r requirements.txt
```

추가 요구사항:
- `ffmpeg` (자막 없는 영상의 음성인식용)
- Ollama 설치 후 모델 받기: `ollama pull llama3.1`

## 사용

```bash
python -m youtube_summarizer "https://youtu.be/VIDEO_ID"
python -m youtube_summarizer "https://youtu.be/VIDEO_ID" --out "D:\\my-notes"
```

## 설정 (config.toml)

| 키 | 설명 |
|----|------|
| output_dir | 기본 저장 폴더 |
| ollama_model | 사용할 Ollama 모델명 |
| whisper_model | whisper 모델 크기 (tiny/base/small/medium) |
| chunk_size | 요약 청크 크기 (글자 수) |
````

- [ ] **Step 2: 의존성 설치**

Run: `pip install -r requirements.txt`
Expected: 설치 성공

- [ ] **Step 3: 실제 영상으로 수동 검증 (자막 있는 영상)**

사전: `ollama serve` 실행 중, 모델 pull 완료.
Run: `python -m youtube_summarizer "<자막 있는 짧은 유튜브 URL>"`
Expected: `[1/5]`~`[5/5]` 진행 메시지 출력 후 `완료: C:\youtube\summaries\<날짜>-<제목>.md`. 파일 열어 frontmatter·핵심 요약·섹션별 요약이 한국어로 들어있는지 확인.

- [ ] **Step 4: 에러 경로 수동 검증**

Run: `python -m youtube_summarizer "https://example.com/bad"`
Expected: `오류: 유튜브 video_id를 추출할 수 없습니다...` 출력, 종료코드 1.

- [ ] **Step 5: Commit**

```bash
git add README.md
git commit -m "docs: README 추가 및 수동 검증 완료"
```

---

## Self-Review

**1. Spec coverage:**
- 파이프라인 6단계 → Task 2~8 ✓
- 자막→whisper 폴백 → Task 4 ✓
- 메타데이터 수집 → Task 3 ✓
- 청크 분할 map-reduce 요약(한국어) → Task 5 ✓
- frontmatter+핵심요약+섹션별 요약 마크다운 → Task 6 ✓
- 슬러그·중복 방지·폴더 자동 생성 → Task 7 ✓
- 설정(config.toml, output_dir 등) → Task 1 ✓
- 에러 처리(잘못된 URL/접근 실패/Ollama/whisper) → Task 2,3,4,5,8 ✓
- CLI `--out` 오버라이드 → Task 8 ✓
- 테스트 전략(extractor/transcript/summarizer/writer) → 각 Task ✓

**2. Placeholder scan:** 모든 코드/테스트/명령 블록에 실제 내용 포함. 플레이스홀더 없음.

**3. Type consistency:** `Metadata`, `TranscriptResult`, `Summary`, `Section` 데이터 구조와 `parse_video_id`/`fetch_metadata`/`fetch_transcript`/`summarize`/`render`/`save` 시그니처가 Task 간 일관됨. `render`/`save`는 Task 8에서 정의된 인자 순서대로 호출됨.

> 참고: 현재 `C:\youtube`는 git 저장소가 아니다. 실행 전 `git init`이 필요하며(커밋 스텝 사용), 원치 않으면 각 Task의 commit 스텝을 생략해도 된다.
