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
