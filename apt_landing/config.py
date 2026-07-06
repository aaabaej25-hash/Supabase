from dataclasses import dataclass
import os

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib


@dataclass
class AptConfig:
    ollama_model: str = "llama3.1"
    projects_dir: str = "projects"
    deploy_repo_path: str = "C:\\youtube\\apt-pages"
    pages_base_url: str = "https://eunj-it.github.io/apt-pages"


def load_config(path: str = "config.toml") -> AptConfig:
    if not os.path.exists(path):
        return AptConfig()
    with open(path, "rb") as f:
        data = tomllib.load(f).get("apt_landing", {})
    return AptConfig(
        ollama_model=data.get("ollama_model", AptConfig.ollama_model),
        projects_dir=data.get("projects_dir", AptConfig.projects_dir),
        deploy_repo_path=data.get("deploy_repo_path", AptConfig.deploy_repo_path),
        pages_base_url=data.get("pages_base_url", AptConfig.pages_base_url),
    )
