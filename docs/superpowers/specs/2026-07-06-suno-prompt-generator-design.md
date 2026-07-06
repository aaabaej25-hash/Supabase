# 유튜브 채널 → Suno 프롬프트 10곡 생성기 — 디자인 스펙

- 날짜: 2026-07-06
- 상태: 사용자 디자인 승인 완료, 구현 계획 대기
- 위치: 기존 `youtube_summarizer` 패키지에 모듈 추가 (새 저장소 없음)

## 배경과 목표

유튜브 채널 URL을 입력하면 채널의 주제·톤·시청자를 분석해, Suno(AI 음악 생성)에
바로 붙여넣을 수 있는 곡 프롬프트 10개를 생성하는 로컬 웹 도구를 만든다.

전체 자동화는 2단계로 나뉜다.

1. **이번 스펙 범위**: 채널 분석 → `songs.json` + `songs.md` 생성 (로컬 웹 UI)
2. **이후 확장(범위 외)**: `songs.json`을 입력으로 Suno에서 실제 음원을 생성하는
   Playwright 브라우저 자동화. 공식 Suno API가 공개되면 API 호출로 교체한다.
   1단계 출력 스키마는 처음부터 2단계 입력 형식으로 맞춘다.

## 확정된 결정 사항

| 항목 | 결정 | 근거 |
|------|------|------|
| 플랫폼 | 로컬 웹 (FastAPI + 단일 HTML) | 혼자, 이 PC에서만 사용. 파이프라인이 전부 Python이라 같은 프로세스에서 호출. 데스크톱 앱은 복잡도 대비 실익 없음 |
| LLM | 로컬 Ollama (기존 llama3.1) | 무료·로컬 유지. 기존 `summarizer.py` 호출 패턴 재사용 |
| 곡 수 | 기본 10곡, `config.toml`로 조절 | 사용자가 Suno 유료 구독 중이라 상한 여유 있음 |
| 비용 | 전 구간 무료 (FastAPI/Ollama/yt-dlp) | 사용자 요청 |

## 아키텍처

```
youtube_summarizer/
  extractor.py        (기존) video_id 파싱, 단일 영상 메타데이터
  transcript.py       (기존) 자막 확보 → whisper 폴백
  summarizer.py       (기존) Ollama 호출, 청크 요약
  channel.py          (신규) 채널 URL 파싱 + yt-dlp flat 목록 수집
  song_prompts.py     (신규) 채널 프로필 분석 + 곡 프롬프트 생성
  web/
    app.py            (신규) FastAPI 서버, 잡 실행, SSE 진행 스트리밍
    static/index.html (신규) 단일 페이지 UI
```

- `channel.py`: `@핸들`, `/channel/UC…`, `/c/…`, `/user/…` URL을 정규화하고
  yt-dlp `extract_flat`으로 최근 30개 영상의 제목·조회수·길이·설명을 한 번에 수집.
- `song_prompts.py`: `summarizer.py`의 `_ollama_chat` / `_extract_json` 패턴을
  재사용(공용 함수로 승격)해 2회 LLM 호출 — ① 채널 프로필, ② 곡 프롬프트 목록.
- `web/app.py`: 잡은 동시에 1개만 실행(개인 도구, 단순 유지).
- 설정 추가(`config.toml`): `videos_to_sample = 4`, `songs_count = 10`.

## 데이터 흐름

```
POST /api/analyze {channel_url}   → {job_id} 반환, 백그라운드 실행
GET  /api/events/{job_id}  (SSE)  → 진행 이벤트 스트림 + 최종 결과
```

파이프라인:

1. 채널 목록 수집 (flat, 최근 30개) — 다운로드 없음, 빠름
2. 대표 영상 4개 선정 — 조회수 상위 2 + 최신 2 (중복 시 다음 후보로 대체)
3. 대표 영상 자막 확보 — 기존 `transcript.py` (자막 → whisper 폴백)
4. 채널 프로필 분석 (Ollama) — 주제, 톤/분위기, 타깃 시청자, 반복 키워드
5. 곡 프롬프트 생성 (Ollama) — 역할 분배로 다양성 강제:
   인트로 1, 아웃트로 1, 무드별 BGM 4(잔잔/업템포/긴장/따뜻), 주제곡 2, 자유 2
6. 저장: `output/<채널명>/songs.json` + `songs.md`

### 곡 프롬프트 생성 규칙 (LLM 프롬프트에 하드코딩)

- 스타일은 영어 쉼표 태그: `lo-fi hip hop, warm piano, 80bpm, mellow female vocals`
- 실제 아티스트/곡명 언급 금지 (Suno가 차단함)
- 가사는 한국어 허용, `instrumental` 플래그 명시
- 곡당 필드: `title`, `style`, `lyrics`, `instrumental`, `role`, `why`

### 출력 스키마 (`songs.json`)

```json
[
  {
    "title": "새벽 코딩 세션",
    "style": "lo-fi hip hop, mellow rhodes, vinyl crackle, 75bpm, instrumental",
    "lyrics": "",
    "instrumental": true,
    "role": "잔잔한 BGM",
    "why": "채널의 심야 개발 브이로그 톤과 매칭"
  }
]
```

## 화면 구성 (단일 페이지)

- **입력부**: 채널 URL 입력창 + "분석 시작" 버튼
- **진행부**: 단계별 진행 표시. whisper 폴백 시 수 분 걸릴 수 있으므로
  현재 처리 중인 영상 제목을 텍스트로 표시 (예: "자막 확보 중 (2/4): …")
- **결과부**: 곡 카드 10개 — 제목, 스타일 태그, 역할, 가사 유무, 선정 이유.
  카드마다 "스타일 복사" / "가사 복사" 버튼 (Suno Custom 모드 붙여넣기용)
- 하단: `songs.json` / `songs.md` 다운로드 링크

## 에러 처리

- 채널 URL 파싱 실패, 비공개/존재하지 않는 채널 → 한국어 에러 메시지를
  SSE 에러 이벤트로 전달해 화면에 표시 (기존 코드의 한국어 에러 스타일 유지)
- 대표 영상의 자막·whisper 실패 → 해당 영상만 건너뛰고 다음 후보로 대체.
  전체 실패로 번지지 않게 함
- Ollama JSON 파싱 실패 → 1회 재요청, 재실패 시 원문 일부 포함 에러 표시
- 곡 수 부족/필드 누락 응답 → 스키마 검증 후 부족분만 재생성 요청 1회

## 테스트

기존 pytest 스타일 유지. yt-dlp·Ollama 호출은 mock.

- 채널 URL 파싱 단위 테스트 (핸들/channel/c/user 형식, 실패 케이스)
- 대표 영상 선정 로직 테스트 (조회수 상위 + 최신, 중복 제거)
- 곡 프롬프트 JSON 스키마 검증 테스트 (곡 수, 필수 필드, instrumental 일관성)
- 웹 UI는 수동 확인 (개인 도구라 E2E 자동화는 범위 외)

## 범위 외 (명시)

- Suno 실제 생성 자동화 (Playwright / 공식 API) — 별도 스펙으로 진행
- 다중 사용자, 인증, 배포 — 로컬 개인 도구
- 동시 분석 잡 — 1개씩만 실행
