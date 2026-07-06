import os
import shutil
import subprocess

from .config import AptConfig
from .models import Project


def _git(repo: str, args: list[str], run) -> None:
    r = run(["git", "-C", repo] + args, capture_output=True, text=True)
    output = (r.stdout or "") + (r.stderr or "")
    if r.returncode != 0 and "nothing to commit" not in output:
        raise RuntimeError(f"git {args[0]} 실패:\n{output.strip()}")


def deploy(project: Project, cfg: AptConfig, run=subprocess.run) -> str:
    repo = cfg.deploy_repo_path
    if not os.path.isdir(os.path.join(repo, ".git")):
        raise RuntimeError(
            f"배포 리포가 없습니다: {repo}\n먼저 GitHub에 apt-pages 리포를 만들고 이 경로에 clone 하세요."
        )
    build_dir = os.path.join(cfg.projects_dir, project.slug, "build")
    if not os.path.isfile(os.path.join(build_dir, "index.html")):
        raise RuntimeError("빌드 결과가 없습니다. 먼저 미리보기를 실행해 빌드하세요.")

    target = os.path.join(repo, project.slug)
    shutil.rmtree(target, ignore_errors=True)
    shutil.copytree(build_dir, target)

    _git(repo, ["add", "-A"], run)
    _git(repo, ["commit", "-m", f"deploy: {project.slug}"], run)
    _git(repo, ["push"], run)
    return f"{cfg.pages_base_url.rstrip('/')}/{project.slug}/"


def undeploy(slug: str, cfg: AptConfig, run=subprocess.run) -> None:
    repo = cfg.deploy_repo_path
    shutil.rmtree(os.path.join(repo, slug), ignore_errors=True)
    _git(repo, ["add", "-A"], run)
    _git(repo, ["commit", "-m", f"undeploy: {slug}"], run)
    _git(repo, ["push"], run)
