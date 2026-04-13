"""Project management — CRUD, file operations, template support."""
import json
import os
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from .users import get_current_user

router = APIRouter()

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
PROJECTS_ROOT = Path(os.getenv("GODOTFORGE_PROJECTS_ROOT", "/tmp/godotforge/projects"))
TEMPLATES_ROOT = Path(os.getenv(
    "GODOTFORGE_TEMPLATES_ROOT",
    str(Path(__file__).resolve().parents[4] / "templates"),
))

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    description: str = ""
    template: str = ""  # e.g. "2d-platformer"
    godot_version: str = "4.4"


class ProjectResponse(BaseModel):
    id: str
    name: str
    description: str
    owner_id: str
    template: str
    godot_version: str
    created_at: str
    updated_at: str
    path: str


class ProjectList(BaseModel):
    projects: list[ProjectResponse]
    total: int


class FileRequest(BaseModel):
    action: str = Field(..., pattern=r"^(read|write|delete|list)$")
    path: str = Field(default="", description="Relative path inside the project")
    content: str = Field(default="", description="File content for write action")


class FileResponse(BaseModel):
    path: str
    content: str = ""
    is_dir: bool = False
    children: list[str] = []
    size: int = 0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _projects_meta_file(owner_id: str) -> Path:
    p = PROJECTS_ROOT / owner_id / "projects.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    if not p.exists():
        p.write_text("[]")
    return p


def _load_projects(owner_id: str) -> list[dict]:
    try:
        data = json.loads(_projects_meta_file(owner_id).read_text())
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def _save_projects(owner_id: str, projects: list[dict]) -> None:
    _projects_meta_file(owner_id).write_text(json.dumps(projects, indent=2, ensure_ascii=False))


def _find_project(owner_id: str, project_id: str) -> dict | None:
    for p in _load_projects(owner_id):
        if p["id"] == project_id:
            return p
    return None


def _project_dir(owner_id: str, project_id: str) -> Path:
    return PROJECTS_ROOT / owner_id / project_id


def _default_project_godot(name: str, godot_version: str) -> str:
    """Generate a minimal but valid Godot 4.x project.godot file."""
    return f"""; Engine configuration file.
; It's best edited using the editor UI and not directly,
; unless you know what you are doing.

[application]

config/name="{name}"
config/features=PackedStringArray("4.4", "GL Compatibility")
run/main_scene=""
config/icon="res://icon.svg"

[display]

window/size/viewport_width=1152
window/size/viewport_height=648

[rendering]

renderer/rendering_method="gl_compatibility"
renderer/rendering_method.mobile="gl_compatibility"
"""


def _build_file_tree(root: Path, prefix: str = "") -> list[str]:
    """Return a flat list of relative paths under *root*."""
    entries: list[str] = []
    if not root.is_dir():
        return entries
    for child in sorted(root.iterdir()):
        rel = f"{prefix}/{child.name}" if prefix else child.name
        if child.name.startswith(".") or child.name == "__pycache__":
            continue
        if child.is_dir():
            entries.append(rel + "/")
            entries.extend(_build_file_tree(child, rel))
        else:
            entries.append(rel)
    return entries


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(body: ProjectCreate, user: Annotated[dict, Depends(get_current_user)]):
    """Create a new Godot project, optionally from a template."""
    owner_id = user["id"]
    project_id = uuid.uuid4().hex[:12]
    proj_dir = _project_dir(owner_id, project_id)
    proj_dir.mkdir(parents=True, exist_ok=True)

    # Copy template if specified
    if body.template:
        template_dir = TEMPLATES_ROOT / body.template
        if template_dir.is_dir():
            shutil.copytree(template_dir, proj_dir, dirs_exist_ok=True)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Template '{body.template}' not found",
            )

    # Ensure project.godot exists
    godot_file = proj_dir / "project.godot"
    if not godot_file.exists():
        godot_file.write_text(_default_project_godot(body.name, body.godot_version))

    # Ensure scripts/ dir
    (proj_dir / "scripts").mkdir(exist_ok=True)

    now = datetime.now(timezone.utc).isoformat()
    meta = {
        "id": project_id,
        "name": body.name,
        "description": body.description,
        "owner_id": owner_id,
        "template": body.template,
        "godot_version": body.godot_version,
        "created_at": now,
        "updated_at": now,
        "path": str(proj_dir),
    }

    projects = _load_projects(owner_id)
    projects.append(meta)
    _save_projects(owner_id, projects)

    return ProjectResponse(**meta)


@router.get("", response_model=ProjectList)
async def list_projects(user: Annotated[dict, Depends(get_current_user)]):
    """List all projects owned by the authenticated user."""
    projects = _load_projects(user["id"])
    return ProjectList(
        projects=[ProjectResponse(**p) for p in projects],
        total=len(projects),
    )


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str, user: Annotated[dict, Depends(get_current_user)]):
    """Get a single project's metadata (includes file tree in description)."""
    proj = _find_project(user["id"], project_id)
    if proj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    # Enrich description with file tree
    proj_dir = _project_dir(user["id"], project_id)
    tree = _build_file_tree(proj_dir)
    enriched = dict(proj)
    enriched["description"] = proj["description"] + "\n\n--- File Tree ---\n" + "\n".join(tree) if tree else proj["description"]
    return ProjectResponse(**enriched)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(project_id: str, user: Annotated[dict, Depends(get_current_user)]):
    """Delete a project and all its files."""
    proj = _find_project(user["id"], project_id)
    if proj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    # Remove directory
    proj_dir = _project_dir(user["id"], project_id)
    if proj_dir.exists():
        shutil.rmtree(proj_dir)

    # Remove from metadata
    projects = [p for p in _load_projects(user["id"]) if p["id"] != project_id]
    _save_projects(user["id"], projects)


@router.post("/{project_id}/files", response_model=FileResponse)
async def manage_files(
    project_id: str,
    body: FileRequest,
    user: Annotated[dict, Depends(get_current_user)],
):
    """Read, write, delete, or list files inside a project."""
    proj = _find_project(user["id"], project_id)
    if proj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    proj_dir = _project_dir(user["id"], project_id)
    target = (proj_dir / body.path).resolve()

    # Prevent path traversal
    if not str(target).startswith(str(proj_dir)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Path traversal not allowed")

    if body.action == "list":
        if target.is_dir():
            children = [
                c.name + ("/" if c.is_dir() else "")
                for c in sorted(target.iterdir())
                if not c.name.startswith(".")
            ]
            return FileResponse(path=body.path, is_dir=True, children=children)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Not a directory")

    if body.action == "read":
        if not target.exists():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
        if target.is_dir():
            children = [c.name + ("/" if c.is_dir() else "") for c in sorted(target.iterdir())]
            return FileResponse(path=body.path, is_dir=True, children=children)
        content = target.read_text(errors="replace")
        return FileResponse(path=body.path, content=content, size=target.stat().st_size)

    if body.action == "write":
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body.content)
        # Touch updated_at
        _touch_updated(user["id"], project_id)
        return FileResponse(path=body.path, content=body.content, size=len(body.content.encode()))

    if body.action == "delete":
        if not target.exists():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
        if target.is_dir():
            shutil.rmtree(target)
        else:
            target.unlink()
        _touch_updated(user["id"], project_id)
        return FileResponse(path=body.path)

    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unknown action: {body.action}")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _touch_updated(owner_id: str, project_id: str) -> None:
    projects = _load_projects(owner_id)
    for p in projects:
        if p["id"] == project_id:
            p["updated_at"] = datetime.now(timezone.utc).isoformat()
            break
    _save_projects(owner_id, projects)
