"""Project management — CRUD, file operations, template support."""
import asyncio
import json
import logging
import mimetypes
import os
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse as FastAPIFileResponse
from pydantic import BaseModel, Field

from .users import get_current_user
from ..config import settings
from ..services.llm_service import generate_gdscript

logger = logging.getLogger(__name__)

router = APIRouter()
templates_router = APIRouter()

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
run/main_scene="res://main.tscn"
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


# ---------------------------------------------------------------------------
# New models
# ---------------------------------------------------------------------------

class FileTreeNode(BaseModel):
    name: str
    type: str = Field(..., pattern=r"^(file|directory)$")
    path: str
    children: list["FileTreeNode"] = []


class ChatRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    mode: str = Field(default="code", pattern=r"^(code|chat)$")


class ChatResponse(BaseModel):
    role: str = "assistant"
    content: str
    files: list[dict[str, str]] = []


class GeneratePreviewRequest(BaseModel):
    prompt: str
    auto_run: bool = True


class GeneratePreviewResponse(BaseModel):
    files_written: list[dict]  # [{path, size}]
    preview_url: str  # URL to the exported HTML5 game
    explanation: str
    export_status: str  # "success" | "failed" | "no_templates"
    export_log: str


class TemplateInfo(BaseModel):
    id: str
    name: str
    description: str = ""
    category: str = ""
    tags: list[str] = []
    thumbnail: str = ""
    features: list[str] = []
    godot_version: str = ""
    ai_customizable: dict[str, Any] = {}


# ---------------------------------------------------------------------------
# Helpers for new endpoints
# ---------------------------------------------------------------------------

SKIP_DIRS = {".godot", ".import", "__pycache__"}
SKIP_EXTENSIONS = {".import"}


def _build_nested_file_tree(root: Path, rel_prefix: str = "") -> list[dict]:
    """Walk *root* recursively and return a nested JSON-serialisable tree.

    Skips `.godot/`, `.import` files, and other non-essential entries.
    """
    nodes: list[dict] = []
    if not root.is_dir():
        return nodes
    for child in sorted(root.iterdir()):
        if child.name in SKIP_DIRS or child.name.startswith("."):
            continue
        if child.suffix in SKIP_EXTENSIONS:
            continue
        rel_path = f"{rel_prefix}/{child.name}" if rel_prefix else child.name
        if child.is_dir():
            children = _build_nested_file_tree(child, rel_path)
            nodes.append({
                "name": child.name,
                "type": "directory",
                "path": rel_path,
                "children": children,
            })
        else:
            nodes.append({
                "name": child.name,
                "type": "file",
                "path": rel_path,
            })
    return nodes


# ---------------------------------------------------------------------------
# New routes on the projects router
# ---------------------------------------------------------------------------

@router.get("/{project_id}/tree")
async def get_project_tree(
    project_id: str,
    user: Annotated[dict, Depends(get_current_user)],
):
    """Return the project's file tree as a nested JSON structure."""
    proj = _find_project(user["id"], project_id)
    if proj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    proj_dir = _project_dir(user["id"], project_id)
    if not proj_dir.is_dir():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project directory not found")

    tree = _build_nested_file_tree(proj_dir)
    return tree


@router.post("/{project_id}/chat", response_model=ChatResponse)
async def project_chat(
    project_id: str,
    body: ChatRequest,
    user: Annotated[dict, Depends(get_current_user)],
):
    """Chat proxy endpoint — forwards to codegen or returns a plain response."""
    proj = _find_project(user["id"], project_id)
    if proj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    if body.mode == "code":
        try:
            result = await generate_gdscript(
                prompt=body.prompt,
                godot_version=proj.get("godot_version", "4.4"),
            )
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Code generation failed: {exc}",
            )

        content = result.get("explanation", "")
        files = result.get("files", [])
        return ChatResponse(role="assistant", content=content, files=files)

    # Default / "chat" mode — echo back (placeholder for a future general chat LLM call)
    return ChatResponse(
        role="assistant",
        content=f"(chat mode not yet implemented) You said: {body.prompt}",
        files=[],
    )


# ---------------------------------------------------------------------------
# Templates router  (mounted separately at /api/v1/templates)
# ---------------------------------------------------------------------------

@templates_router.get("", response_model=list[TemplateInfo])
async def list_templates():
    """List available game templates by reading template.json from each template directory."""
    templates: list[dict] = []

    if not TEMPLATES_ROOT.is_dir():
        return templates

    for entry in sorted(TEMPLATES_ROOT.iterdir()):
        if not entry.is_dir():
            continue
        meta_file = entry / "template.json"
        if not meta_file.exists():
            continue
        try:
            data = json.loads(meta_file.read_text())
            data.setdefault("id", entry.name)
            templates.append(data)
        except (json.JSONDecodeError, OSError):
            continue

    return templates


# ---------------------------------------------------------------------------
# Generate-and-Preview helpers
# ---------------------------------------------------------------------------

def _resolve_godot_binary() -> str:
    """Return the path to the Godot binary.

    Priority:
      1. ``settings.godot_path`` if explicitly set (and not the bare default)
      2. macOS application bundle path
      3. Fall back to ``godot`` (rely on PATH)
    """
    configured = getattr(settings, "godot_path", "godot")

    # If the user explicitly configured a full path, honour it
    if configured and configured != "godot" and Path(configured).exists():
        return configured

    # macOS application bundle
    mac_path = Path("/Applications/Godot.app/Contents/MacOS/Godot")
    if mac_path.exists():
        return str(mac_path)

    return configured or "godot"


def _ensure_project_godot(project_dir: Path, project_name: str = "GeneratedProject") -> None:
    """Create a minimal ``project.godot`` if one does not already exist."""
    godot_file = project_dir / "project.godot"
    if godot_file.exists():
        return
    godot_file.write_text(_default_project_godot(project_name, "4.4"))


def _generate_export_presets(project_dir: Path) -> None:
    """Write an ``export_presets.cfg`` configured for Web (HTML5) export."""
    cfg = project_dir / "export_presets.cfg"
    cfg.write_text(
        '[preset.0]\n'
        '\n'
        'name="Web"\n'
        'platform="Web"\n'
        'runnable=true\n'
        'dedicated_server=false\n'
        'custom_features=""\n'
        'export_filter="all_resources"\n'
        'include_filter=""\n'
        'exclude_filter=""\n'
        'export_path=""\n'
        'encryption_include_filters=""\n'
        'encryption_exclude_filters=""\n'
        'encrypt_pck=false\n'
        'encrypt_directory=false\n'
        '\n'
        '[preset.0.options]\n'
        '\n'
        'custom_template/debug=""\n'
        'custom_template/release=""\n'
        'variant/extensions_support=false\n'
        'vram_texture_compression/for_desktop=true\n'
        'vram_texture_compression/for_mobile=false\n'
        'html/export_icon=true\n'
        'html/custom_html_shell=""\n'
        'html/head_include=""\n'
        'html/canvas_resize_policy=2\n'
        'html/focus_canvas_on_start=true\n'
        'html/experimental_virtual_keyboard=false\n'
        'progressive_web_app/enabled=false\n'
    )


async def _run_godot_export(
    project_dir: Path,
    output_dir: Path,
    timeout: float = 300.0,
) -> tuple[bool, str]:
    """Run Godot headless export targeting Web (HTML5).

    Returns ``(success, log_text)``.
    """
    godot_bin = _resolve_godot_binary()
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "index.html"

    cmd = [
        godot_bin,
        "--headless",
        "--path", str(project_dir),
        "--export-release", "Web",
        str(output_file),
    ]

    logger.info("Running Godot export: %s", " ".join(cmd))

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        stdout_bytes, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        log_text = stdout_bytes.decode(errors="replace") if stdout_bytes else ""
    except FileNotFoundError:
        return False, f"Godot binary not found at '{godot_bin}'. Set GODOTFORGE_GODOT_PATH or install Godot."
    except asyncio.TimeoutError:
        try:
            proc.kill()  # type: ignore[union-attr]
        except Exception:
            pass
        return False, f"Godot export timed out after {timeout}s"
    except Exception as exc:
        return False, f"Failed to run Godot export: {exc}"

    if proc.returncode != 0:
        # Detect missing export templates
        if "no export template" in log_text.lower() or "export template" in log_text.lower():
            return False, f"NO_TEMPLATES: {log_text}"
        return False, log_text

    # Verify the output was actually created
    if not output_file.exists():
        return False, f"Export command succeeded (rc=0) but {output_file} was not created.\n{log_text}"

    return True, log_text


# ---------------------------------------------------------------------------
# Generate-and-Preview endpoints
# ---------------------------------------------------------------------------

@router.post("/{project_id}/generate-and-preview", response_model=GeneratePreviewResponse)
async def generate_and_preview(
    project_id: str,
    body: GeneratePreviewRequest,
    user: Annotated[dict, Depends(get_current_user)],
):
    """Generate GDScript from a prompt, write files, export to Web, return preview URL."""
    proj = _find_project(user["id"], project_id)
    if proj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    proj_dir = _project_dir(user["id"], project_id)
    proj_dir.mkdir(parents=True, exist_ok=True)

    # ----- Step 1: AI code generation ----- #
    try:
        result = await generate_gdscript(
            prompt=body.prompt,
            godot_version=proj.get("godot_version", "4.4"),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Code generation failed: {exc}",
        )

    explanation = result.get("explanation", "")
    generated_files = result.get("files", [])

    # DEBUG: write raw result to a file for inspection
    import json as _json
    debug_path = proj_dir / "_debug_codegen_result.json"
    debug_path.write_text(_json.dumps({
        "code_len": len(result.get("code", "")),
        "files_count": len(generated_files),
        "files_paths": [f.get("path","") for f in generated_files],
        "files_content_lens": [len(f.get("content","")) for f in generated_files],
        "explanation_len": len(explanation),
    }, indent=2))

    # Ensure we always have writable files — LLM parsers can be unreliable
    code_text = result.get("code", "")

    # Filter out files with empty content
    generated_files = [f for f in generated_files if f.get("content", "").strip()]

    # If no usable files but raw code exists, save as a single file
    if not generated_files and code_text.strip():
        generated_files = [{"path": "res://scripts/main.gd", "content": code_text}]

    # Also always write the raw code as main.gd if not already present
    has_main = any("main.gd" in f.get("path", "") for f in generated_files)
    if not has_main and code_text.strip():
        generated_files.insert(0, {"path": "res://scripts/main.gd", "content": code_text})

    # ----- Step 2: Write generated files to project directory ----- #
    files_written: list[dict] = []
    for f in generated_files:
        raw_path: str = f.get("path", "")
        content: str = f.get("content", "")

        # Strip the res:// prefix so we get a relative path within the project
        rel_path = raw_path
        if rel_path.startswith("res://"):
            rel_path = rel_path[len("res://"):]
        rel_path = rel_path.lstrip("/")

        if not rel_path or not content:
            logger.warning("Skipping empty file: path=%r content_len=%d", rel_path, len(content))
            continue

        dest = (proj_dir / rel_path).resolve()

        # Prevent path traversal (resolve proj_dir too for symlink consistency)
        if not str(dest).startswith(str(proj_dir.resolve())):
            logger.warning("Skipping path traversal attempt: %s", raw_path)
            continue

        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content)
        files_written.append({"path": rel_path, "size": len(content.encode())})

    # Ensure a main scene exists so Godot has something to export
    main_scene_path = proj_dir / "main.tscn"
    if not main_scene_path.exists():
        # Find the first .gd script to attach
        first_script = ""
        for fw in files_written:
            if fw["path"].endswith(".gd"):
                first_script = fw["path"]
                break
        tscn = '[gd_scene format=3]\n\n[node name="Main" type="Node2D"]\n'
        if first_script:
            tscn = (
                f'[gd_scene load_steps=2 format=3]\n\n'
                f'[ext_resource type="Script" path="res://{first_script}" id="1"]\n\n'
                f'[node name="Main" type="Node2D"]\n'
                f'script = ExtResource("1")\n'
            )
        main_scene_path.write_text(tscn)
        files_written.append({"path": "main.tscn", "size": len(tscn.encode())})

    # ----- Step 3: Ensure project.godot exists ----- #
    _ensure_project_godot(proj_dir, proj.get("name", "GeneratedProject"))

    # ----- Step 4: Generate export_presets.cfg ----- #
    _generate_export_presets(proj_dir)

    # ----- Step 5: Run Godot headless export ----- #
    output_dir = proj_dir / "_web_export"
    success, log_text = await _run_godot_export(proj_dir, output_dir)

    if success:
        export_status = "success"
    elif "NO_TEMPLATES:" in log_text:
        export_status = "no_templates"
        log_text = log_text.replace("NO_TEMPLATES: ", "", 1)
    else:
        export_status = "failed"

    # ----- Step 6: Build preview URL ----- #
    preview_url = f"/api/v1/projects/{project_id}/preview/index.html"

    _touch_updated(user["id"], project_id)

    return GeneratePreviewResponse(
        files_written=files_written,
        preview_url=preview_url,
        explanation=explanation,
        export_status=export_status,
        export_log=log_text,
    )


@router.get("/{project_id}/preview/{file_path:path}")
async def serve_preview(
    project_id: str,
    file_path: str,
    user: Annotated[dict, Depends(get_current_user)],
):
    """Serve static files from the project's Web export output directory.

    This allows an iframe to load the exported game at
    ``/api/v1/projects/{project_id}/preview/index.html``.
    """
    proj = _find_project(user["id"], project_id)
    if proj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    proj_dir = _project_dir(user["id"], project_id)
    export_dir = proj_dir / "_web_export"

    target = (export_dir / file_path).resolve()

    # Prevent path traversal
    if not str(target).startswith(str(export_dir.resolve())):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Path traversal not allowed")

    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Preview file not found")

    # Determine content type
    content_type, _ = mimetypes.guess_type(str(target))
    if content_type is None:
        suffix = target.suffix.lower()
        extra_types = {
            ".wasm": "application/wasm",
            ".pck": "application/octet-stream",
        }
        content_type = extra_types.get(suffix, "application/octet-stream")

    return FastAPIFileResponse(
        path=str(target),
        media_type=content_type,
        filename=target.name,
    )
