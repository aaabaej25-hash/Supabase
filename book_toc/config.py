from dataclasses import dataclass
import os

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib


@dataclass
class BookTocConfig:
    ollama_model: str = "llama3.1"
    output_dir: str = "book_tocs"
    book_count: int = 5


def load_config(path: str = "config.toml") -> BookTocConfig:
    if not os.path.exists(path):
        return BookTocConfig()
    with open(path, "rb") as f:
        data = tomllib.load(f).get("book_toc", {})
    return BookTocConfig(
        ollama_model=data.get("ollama_model", BookTocConfig.ollama_model),
        output_dir=data.get("output_dir", BookTocConfig.output_dir),
        book_count=data.get("book_count", BookTocConfig.book_count),
    )
