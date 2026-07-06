import os
import shutil

from jinja2 import Environment, FileSystemLoader
from PIL import Image

from .models import Project, project_dir

_TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")
_MAX_WIDTH = 1600


def _process_photo(src: str, dst: str) -> None:
    img = Image.open(src).convert("RGB")
    if img.width > _MAX_WIDTH:
        img = img.resize((_MAX_WIDTH, int(img.height * _MAX_WIDTH / img.width)))
    img.save(dst, "WEBP", quality=85)


def build(project: Project, base_dir: str) -> tuple[str, list[str]]:
    pdir = project_dir(base_dir, project.slug)
    build_dir = os.path.join(pdir, "build")
    shutil.rmtree(build_dir, ignore_errors=True)
    os.makedirs(os.path.join(build_dir, "photos"), exist_ok=True)

    processed, failed = [], []
    for name in project.photos:
        out_name = os.path.splitext(name)[0] + ".webp"
        try:
            _process_photo(
                os.path.join(pdir, "photos", name),
                os.path.join(build_dir, "photos", out_name),
            )
            processed.append(out_name)
        except Exception:
            failed.append(name)

    # 주의: select_autoescape는 .j2 확장자를 autoescape 대상으로 보지 않으므로 True 고정
    env = Environment(loader=FileSystemLoader(_TEMPLATE_DIR), autoescape=True)
    html = env.get_template("landing.html.j2").render(
        project=project, style=project.style, copy=project.copy, photos=processed
    )
    with open(os.path.join(build_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)
    return build_dir, failed
