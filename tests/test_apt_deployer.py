import os
from types import SimpleNamespace

import pytest

from apt_landing.config import AptConfig
from apt_landing.deployer import deploy, undeploy
from apt_landing.models import Project


def make_env(tmp_path):
    repo = tmp_path / "apt-pages"
    (repo / ".git").mkdir(parents=True)
    projects = tmp_path / "projects"
    build = projects / "t-apt" / "build"
    build.mkdir(parents=True)
    (build / "index.html").write_text("<html>x</html>", encoding="utf-8")
    cfg = AptConfig(
        projects_dir=str(projects),
        deploy_repo_path=str(repo),
        pages_base_url="https://eunj-it.github.io/apt-pages",
    )
    return cfg


def ok_run(recorder):
    def run(cmd, capture_output=True, text=True):
        recorder.append(cmd)
        return SimpleNamespace(returncode=0, stdout="", stderr="")
    return run


def test_deploy_copies_build_and_pushes(tmp_path):
    cfg = make_env(tmp_path)
    calls = []
    url = deploy(Project(slug="t-apt"), cfg, run=ok_run(calls))
    assert url == "https://eunj-it.github.io/apt-pages/t-apt/"
    assert os.path.isfile(os.path.join(cfg.deploy_repo_path, "t-apt", "index.html"))
    git_subcmds = [c[3] for c in calls]  # ["git", "-C", repo, <subcmd>, ...]
    assert git_subcmds == ["add", "commit", "push"]


def test_deploy_fails_without_repo(tmp_path):
    cfg = make_env(tmp_path)
    cfg.deploy_repo_path = str(tmp_path / "없는리포")
    with pytest.raises(RuntimeError, match="배포 리포"):
        deploy(Project(slug="t-apt"), cfg, run=ok_run([]))


def test_deploy_fails_without_build(tmp_path):
    cfg = make_env(tmp_path)
    with pytest.raises(RuntimeError, match="빌드"):
        deploy(Project(slug="다른매물"), cfg, run=ok_run([]))


def test_deploy_surfaces_git_error(tmp_path):
    cfg = make_env(tmp_path)

    def fail_run(cmd, capture_output=True, text=True):
        return SimpleNamespace(returncode=1, stdout="", stderr="remote: 인증 실패")

    with pytest.raises(RuntimeError, match="인증 실패"):
        deploy(Project(slug="t-apt"), cfg, run=fail_run)


def test_undeploy_removes_folder(tmp_path):
    cfg = make_env(tmp_path)
    calls = []
    deploy(Project(slug="t-apt"), cfg, run=ok_run(calls))
    undeploy("t-apt", cfg, run=ok_run(calls))
    assert not os.path.isdir(os.path.join(cfg.deploy_repo_path, "t-apt"))
