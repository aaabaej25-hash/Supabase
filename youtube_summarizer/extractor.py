import re
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
