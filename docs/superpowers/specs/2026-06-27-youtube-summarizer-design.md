# 유튜브 스크립트 요약 도구 — 설계 문서

작성일: 2026-06-27

## 1. 목적

유튜브 링크를 입력하면 스크립트(자막)를 추출하고, 로컬 LLM으로 한국어 요약 문서를
생성하여 지정 폴더(`C:\youtube`)에 마크다운으로 저장하는 CLI 도구.

## 2. 확정된 요구사항

| 항목 | 결정 |
|------|------|
| 실행 형태 | CLI 명령어 |
| 요약 엔진 | 로컬 LLM (Ollama) |
| 자막 처리 | 자막 있으면 자막 사용, 없으면 Whisper 음성인식 폴백 |
| 출력 언어 | 항상 한국어 |
| 문서 구성 | 섹션별 요약 중심 (+ 메타데이터 frontmatter, 핵심 요약) |
| 저장 위치 | `C:\youtube\summaries` |
| 기술 스택 | Python (yt-dlp + youtube-transcript-api + faster-whisper + ollama) |

## 3. 전체 구조 (파이프라인)

```
유튜브 URL
   │
   ▼
[1] 입력 파싱 ──► video_id 추출, URL 검증
   │
   ▼
[2] 스크립트 확보
     ├─ 자막 있음 → youtube-transcript-api (빠름)
     └─ 자막 없음 → yt-dlp로 오디오 다운로드 → faster-whisper 전사
   │
   ▼
[3] 메타데이터 수집 ──► yt-dlp로 제목/채널/길이
   │
   ▼
[4] 요약 (Ollama) ──► 긴 스크립트는 청크 분할 → 섹션별 요약 → 한국어
   │
   ▼
[5] 마크다운 렌더 ──► frontmatter + 핵심 요약 + 섹션별 요약
   │
   ▼
[6] 저장 ──► C:\youtube\summaries\<날짜>-<제목slug>.md
```

## 4. 모듈 구성 (단일 책임)

```
youtube_summarizer/
├── cli.py            # 진입점: 인자 파싱, 파이프라인 호출, 진행상황 출력
├── config.py         # 설정 로드 (출력폴더, ollama 모델명, whisper 모델크기)
├── extractor.py      # video_id 파싱 + 메타데이터 수집 (yt-dlp)
├── transcript.py     # 자막 확보: 자막 API → 실패 시 whisper 폴백
├── summarizer.py     # 청크 분할 + Ollama 호출 + 섹션별 한국어 요약
├── renderer.py       # 요약 데이터 → 마크다운 문자열
└── writer.py         # 파일명 생성 + 저장
```

각 모듈은 순수 함수에 가깝게 설계해 입출력이 명확하고 독립 테스트가 가능하다.

## 5. 데이터 흐름

```
url:str
  → extractor.parse(url) -> video_id:str
  → extractor.metadata(video_id) -> {title, channel, duration, url}
  → transcript.fetch(video_id) -> raw_text:str   (자막 or whisper)
  → summarizer.summarize(raw_text) -> Summary{ sections: [{heading, bullets}] }
  → renderer.render(metadata, summary) -> md:str
  → writer.save(md, title) -> path
```

`Summary`는 섹션 리스트를 담는 단순 dataclass. 렌더러는 LLM을 모르고, 요약기는
마크다운을 모른다 — 경계가 명확하다.

## 6. 요약 전략

- 스크립트가 길면 토큰 한계를 넘으므로 **청크 분할**(기본 ~3000자) 후 각 청크를 요약하고,
  부분 요약들을 다시 합쳐 **섹션별 최종 요약**을 생성한다 (map-reduce 방식).
- Ollama 프롬프트는 "한국어로, 주제별 섹션과 불릿으로 정리"를 강제한다.
- 자막에 타임스탬프가 있을 경우(자막 출처일 때만) 섹션 헤딩 옆에 대략적 시점을 표기한다.

## 7. 에러 처리

| 상황 | 처리 |
|------|------|
| 잘못된 URL / video_id 추출 실패 | 즉시 명확한 메시지 출력 후 종료 |
| 비공개·삭제·지역제한 영상 | yt-dlp 에러를 잡아 사유 안내 |
| 자막 없음 | whisper 폴백으로 자동 전환 (안내 메시지 출력) |
| whisper/ffmpeg 미설치 | 설치 안내 후 종료 (자막 폴백 불가 명시) |
| Ollama 미실행 / 모델 없음 | 연결 실패 감지, `ollama serve` 및 `ollama pull` 안내 |
| 저장 폴더 없음 | 자동 생성 |
| 동일 파일명 존재 | 뒤에 `-2`, `-3` 붙여 덮어쓰기 방지 |

긴 작업(다운로드/전사/요약)에는 단계별 진행 메시지를 출력한다.

## 8. 파일명 & 출력 위치

- 위치: `C:\youtube\summaries\` (없으면 자동 생성)
- 파일명: `2026-06-27-영상제목-슬러그.md`
  - 처리일(날짜) + 제목을 안전한 슬러그로 변환 (공백→`-`, 특수문자 제거, 한글 유지, 길이 제한).

## 9. 설정 (`config.toml`)

```toml
output_dir    = "C:\\youtube\\summaries"
ollama_model  = "llama3.1"     # 보유 모델로 교체
whisper_model = "base"         # tiny/base/small/medium
language      = "ko"
chunk_size    = 3000
```

CLI 사용: `python -m youtube_summarizer <유튜브URL>`

## 10. 출력 마크다운 예시

```markdown
---
title: "영상 제목"
channel: "채널명"
url: https://youtu.be/XXXX
duration: "12:34"
source: "자막"        # 또는 "음성인식(whisper)"
date: 2026-06-27
---

# 영상 제목

## 핵심 요약
- (전체를 3~5줄 불릿으로)

## 섹션별 요약

### 1. 도입 (00:00~)
- ...

### 2. 주요 내용 (03:20~)
- ...
```

## 11. 테스트 전략

- `extractor.parse` — 다양한 URL 형식(youtu.be, watch?v=, 쇼츠) 단위 테스트
- `transcript.fetch` — 자막 API/whisper를 모킹해 분기 검증
- `summarizer` — 청크 분할 로직 단위 테스트 (LLM 호출은 모킹)
- `writer` — 슬러그·중복 파일명 규칙 테스트

## 12. 사전 요구 사항 (설치)

- Python 3.10+
- 파이썬 패키지: `yt-dlp`, `youtube-transcript-api`, `faster-whisper`, `ollama`
- `ffmpeg` (whisper 폴백용 오디오 처리)
- Ollama 설치 및 모델 pull (예: `ollama pull llama3.1`)
