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
