from youtube_summarizer.config import load_config, Config


def test_load_config_reads_values(tmp_path):
    cfg_file = tmp_path / "config.toml"
    cfg_file.write_text(
        'output_dir = "D:\\\\out"\n'
        'ollama_model = "mymodel"\n'
        'whisper_model = "small"\n'
        'language = "ko"\n'
        'chunk_size = 1000\n',
        encoding="utf-8",
    )
    cfg = load_config(str(cfg_file))
    assert cfg.output_dir == "D:\\out"
    assert cfg.ollama_model == "mymodel"
    assert cfg.whisper_model == "small"
    assert cfg.chunk_size == 1000


def test_load_config_missing_file_returns_defaults():
    cfg = load_config("nonexistent_____.toml")
    assert isinstance(cfg, Config)
    assert cfg.language == "ko"
    assert cfg.chunk_size == 3000
