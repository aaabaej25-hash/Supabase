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
