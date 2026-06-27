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
