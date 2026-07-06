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
