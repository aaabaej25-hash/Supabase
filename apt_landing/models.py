import json
import os
import re
import unicodedata
from dataclasses import asdict, dataclass, field

DEFAULT_SECTION_ORDER = ["info", "location", "gallery"]

COPY_SECTIONS = [
    "hero_headline",
    "hero_sub",
    "info_summary",
    "location_paragraph",
    "gallery_caption",
    "cta_text",
]


@dataclass
class StyleGuide:
    primary_color: str = "#1a3c5e"
    accent_color: str = "#c8a45e"
    background_color: str = "#ffffff"
    section_order: list[str] = field(default_factory=lambda: list(DEFAULT_SECTION_ORDER))
    tone: str = "신뢰감 있고 정중한 분양 안내 톤"
    extracted: bool = False


@dataclass
class Copy:
    hero_headline: str = ""
    hero_sub: str = ""
    info_summary: str = ""
    location_paragraph: str = ""
    gallery_caption: str = ""
    cta_text: str = ""


@dataclass
class UnitType:
    name: str = ""
    price: str = ""


@dataclass
class Project:
    slug: str
    name: str = ""
    address: str = ""
    move_in: str = ""
    highlights: str = ""
    units: list[UnitType] = field(default_factory=list)
    kakao_link: str = ""
    reference_url: str = ""
    photos: list[str] = field(default_factory=list)
    status: str = "draft"
    deployed_url: str = ""
    style: StyleGuide = field(default_factory=StyleGuide)
    copy: Copy = field(default_factory=Copy)
    google_form_action: str = ""
    google_form_entry_name: str = ""
    google_form_entry_email: str = ""
    google_form_entry_phone: str = ""


def slugify(name: str) -> str:
    s = unicodedata.normalize("NFC", name.strip().lower())
    s = re.sub(r"[^0-9a-z가-힣]+", "-", s)
    return s.strip("-") or "project"


def project_dir(base_dir: str, slug: str) -> str:
    return os.path.join(base_dir, slug)


def save_project(base_dir: str, p: Project) -> None:
    d = project_dir(base_dir, p.slug)
    os.makedirs(os.path.join(d, "photos"), exist_ok=True)
    with open(os.path.join(d, "project.json"), "w", encoding="utf-8") as f:
        json.dump(asdict(p), f, ensure_ascii=False, indent=2)


def _project_from_dict(data: dict) -> Project:
    return Project(
        slug=data["slug"],
        name=data.get("name", ""),
        address=data.get("address", ""),
        move_in=data.get("move_in", ""),
        highlights=data.get("highlights", ""),
        units=[UnitType(**u) for u in data.get("units", [])],
        kakao_link=data.get("kakao_link", ""),
        reference_url=data.get("reference_url", ""),
        photos=data.get("photos", []),
        status=data.get("status", "draft"),
        deployed_url=data.get("deployed_url", ""),
        style=StyleGuide(**data.get("style", {})),
        copy=Copy(**data.get("copy", {})),
        google_form_action=data.get("google_form_action", ""),
        google_form_entry_name=data.get("google_form_entry_name", ""),
        google_form_entry_email=data.get("google_form_entry_email", ""),
        google_form_entry_phone=data.get("google_form_entry_phone", ""),
    )


def load_project(base_dir: str, slug: str) -> Project:
    path = os.path.join(project_dir(base_dir, slug), "project.json")
    with open(path, encoding="utf-8") as f:
        return _project_from_dict(json.load(f))


def list_projects(base_dir: str) -> list[Project]:
    if not os.path.isdir(base_dir):
        return []
    result = []
    for name in sorted(os.listdir(base_dir)):
        if os.path.isfile(os.path.join(base_dir, name, "project.json")):
            result.append(load_project(base_dir, name))
    return result
