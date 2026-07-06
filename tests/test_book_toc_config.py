import os

from book_toc.config import BookTocConfig, load_config


def test_load_config_missing_file_returns_defaults(tmp_path):
    cfg = load_config(os.path.join(str(tmp_path), "없는파일.toml"))
    assert cfg == BookTocConfig()


def test_load_config_reads_book_toc_section(tmp_path):
    p = tmp_path / "config.toml"
    p.write_text(
        'ollama_model = "llama3.1"\n'  # 최상위 키(youtube_summarizer용)는 무시
        "[book_toc]\n"
        'ollama_model = "qwen2"\n'
        'output_dir = "D:\\\\tocs"\n'
        "book_count = 7\n",
        encoding="utf-8",
    )
    cfg = load_config(str(p))
    assert cfg.ollama_model == "qwen2"
    assert cfg.output_dir == "D:\\tocs"
    assert cfg.book_count == 7


def test_load_config_section_missing_returns_defaults(tmp_path):
    p = tmp_path / "config.toml"
    p.write_text('ollama_model = "llama3.1"\n', encoding="utf-8")
    assert load_config(str(p)) == BookTocConfig()
