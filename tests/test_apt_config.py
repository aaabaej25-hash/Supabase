import os

from apt_landing.config import AptConfig, load_config


def test_load_config_missing_file_returns_defaults(tmp_path):
    cfg = load_config(os.path.join(str(tmp_path), "없는파일.toml"))
    assert cfg == AptConfig()


def test_load_config_reads_apt_landing_section(tmp_path):
    p = tmp_path / "config.toml"
    p.write_text(
        'ollama_model = "llama3.1"\n'  # youtube_summarizer용 최상위 키는 무시되어야 함
        "[apt_landing]\n"
        'ollama_model = "qwen2"\n'
        'projects_dir = "D:\\\\data\\\\projects"\n'
        'deploy_repo_path = "C:\\\\youtube\\\\apt-pages"\n'
        'pages_base_url = "https://eunj-it.github.io/apt-pages"\n',
        encoding="utf-8",
    )
    cfg = load_config(str(p))
    assert cfg.ollama_model == "qwen2"
    assert cfg.projects_dir == "D:\\data\\projects"
    assert cfg.deploy_repo_path == "C:\\youtube\\apt-pages"
    assert cfg.pages_base_url == "https://eunj-it.github.io/apt-pages"


def test_load_config_section_missing_returns_defaults(tmp_path):
    p = tmp_path / "config.toml"
    p.write_text('ollama_model = "llama3.1"\n', encoding="utf-8")
    assert load_config(str(p)) == AptConfig()
