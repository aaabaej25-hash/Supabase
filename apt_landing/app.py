import os
import re
from urllib.parse import quote

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from .config import AptConfig, load_config
from .models import (
    Project,
    UnitType,
    list_projects,
    load_project,
    project_dir,
    save_project,
    slugify,
)

_ADMIN_TEMPLATES = os.path.join(os.path.dirname(__file__), "templates", "admin")


def _parse_units(units_text: str) -> list[UnitType]:
    units = []
    for line in units_text.splitlines():
        line = line.strip()
        if not line:
            continue
        name, _, price = line.partition("|")
        units.append(UnitType(name=name.strip(), price=price.strip()))
    return units


def _safe_filename(filename: str) -> str:
    return re.sub(r"[^0-9a-zA-Z가-힣._-]", "-", os.path.basename(filename or "photo"))


def create_app(cfg: AptConfig | None = None) -> FastAPI:
    cfg = cfg or load_config()
    app = FastAPI()
    templates = Jinja2Templates(directory=_ADMIN_TEMPLATES)

    def render(name: str, request: Request, **ctx):
        return templates.TemplateResponse(request, name, ctx)

    @app.exception_handler(FileNotFoundError)
    def not_found(request: Request, exc: FileNotFoundError):
        return RedirectResponse("/?error=" + quote("매물을 찾을 수 없습니다."), status_code=303)

    @app.get("/")
    def index(request: Request, error: str = "", notice: str = ""):
        return render("index.html", request, projects=list_projects(cfg.projects_dir),
                      error=error, notice=notice)

    @app.post("/projects")
    def create_project(request: Request, name: str = Form(...), overwrite: str = Form("")):
        slug = slugify(name)
        exists = os.path.isfile(os.path.join(project_dir(cfg.projects_dir, slug), "project.json"))
        if exists and not overwrite:
            return render("index.html", request, projects=list_projects(cfg.projects_dir),
                          error=f"'{slug}' 매물이 이미 존재합니다. 덮어쓰기를 체크하거나 다른 이름을 쓰세요.",
                          notice="")
        save_project(cfg.projects_dir, Project(slug=slug, name=name.strip()))
        return RedirectResponse(f"/p/{slug}", status_code=303)

    @app.get("/p/{slug}")
    def edit(request: Request, slug: str, error: str = "", notice: str = ""):
        return render("edit.html", request, project=load_project(cfg.projects_dir, slug),
                      error=error, notice=notice)

    @app.post("/p/{slug}")
    def save(request: Request, slug: str, name: str = Form(""), address: str = Form(""),
             move_in: str = Form(""), highlights: str = Form(""), units_text: str = Form(""),
             kakao_link: str = Form(""), reference_url: str = Form("")):
        p = load_project(cfg.projects_dir, slug)
        p.name, p.address, p.move_in = name.strip(), address.strip(), move_in.strip()
        p.highlights, p.kakao_link, p.reference_url = highlights.strip(), kakao_link.strip(), reference_url.strip()
        p.units = _parse_units(units_text)
        save_project(cfg.projects_dir, p)
        return render("edit.html", request, project=p, error="", notice="저장했습니다.")

    def _next_photo_seq(p: Project) -> int:
        max_seq = 0
        for photo in p.photos:
            prefix = photo.split("-", 1)[0]
            if prefix.isdigit():
                max_seq = max(max_seq, int(prefix))
        return max_seq + 1

    @app.post("/p/{slug}/photos")
    def upload_photos(request: Request, slug: str, files: list[UploadFile] = File(...)):
        p = load_project(cfg.projects_dir, slug)
        photo_dir = os.path.join(project_dir(cfg.projects_dir, slug), "photos")
        os.makedirs(photo_dir, exist_ok=True)
        seq = _next_photo_seq(p)
        for f in files:
            name = f"{seq:02d}-{_safe_filename(f.filename)}"
            seq += 1
            with open(os.path.join(photo_dir, name), "wb") as out:
                out.write(f.file.read())
            p.photos.append(name)
        save_project(cfg.projects_dir, p)
        return render("edit.html", request, project=p, error="",
                      notice=f"{len(files)}장 업로드했습니다.")

    @app.get("/p/{slug}/photo-file/{name}")
    def photo_file(slug: str, name: str):
        if slug != slugify(slug):
            raise HTTPException(404, "사진을 찾을 수 없습니다")
        path = os.path.join(project_dir(cfg.projects_dir, slug), "photos", os.path.basename(name))
        if not os.path.isfile(path):
            raise HTTPException(404, "사진을 찾을 수 없습니다")
        return FileResponse(path)

    @app.post("/p/{slug}/photos/{name}/delete")
    def delete_photo(request: Request, slug: str, name: str):
        p = load_project(cfg.projects_dir, slug)
        if name in p.photos:
            p.photos.remove(name)
            path = os.path.join(project_dir(cfg.projects_dir, slug), "photos", os.path.basename(name))
            if os.path.isfile(path):
                os.remove(path)
            save_project(cfg.projects_dir, p)
        return render("edit.html", request, project=p, error="", notice="삭제했습니다.")

    @app.post("/p/{slug}/photos/{name}/up")
    def photo_up(request: Request, slug: str, name: str):
        p = load_project(cfg.projects_dir, slug)
        if name in p.photos:
            i = p.photos.index(name)
            if i > 0:
                p.photos[i - 1], p.photos[i] = p.photos[i], p.photos[i - 1]
                save_project(cfg.projects_dir, p)
        return render("edit.html", request, project=p, error="", notice="")

    return app
