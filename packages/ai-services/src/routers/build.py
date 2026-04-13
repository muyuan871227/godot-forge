"""Build / export — run Godot headless export for multiple platforms."""
import asyncio
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse as FastAPIFileResponse
from pydantic import BaseModel, Field

from ..config import settings
from .users import get_current_user
from .projects import _find_project, _project_dir, PROJECTS_ROOT

router = APIRouter()

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

SUPPORTED_PLATFORMS = ("windows", "macos", "linux", "android", "web")

class BuildConfig(BaseModel):
    debug: bool = False
    optimize_size: bool = False
    extra_args: list[str] = []


class BuildRequest(BaseModel):
    project_id: str
    platform: str = Field(..., pattern=r"^(windows|macos|linux|android|web)$")
    config: BuildConfig = BuildConfig()


class BuildResponse(BaseModel):
    build_id: str
    project_id: str
    platform: str
    status: str  # queued | running | success | failed
    output_path: str = ""
    log: str = ""
    started_at: str = ""
    finished_at: str = ""


# ---------------------------------------------------------------------------
# Platform export presets
# ---------------------------------------------------------------------------

_PLATFORM_PRESETS = {
    "windows": {
        "preset_name": "Windows Desktop",
        "export_ext": ".exe",
        "template_name": "windows",
        "preset_cfg": """\
[preset.{idx}]

name="Windows Desktop"
platform="Windows Desktop"
runnable=true
dedicated_server=false
custom_features=""
export_filter="all_resources"
include_filter=""
exclude_filter=""

[preset.{idx}.options]

custom_template/debug=""
custom_template/release=""
binary_format/embed_pck=true
texture_format/s3tc_bptc=true
texture_format/etc2_astc=false
codesign/enable=false
""",
    },
    "macos": {
        "preset_name": "macOS",
        "export_ext": ".zip",
        "template_name": "macos",
        "preset_cfg": """\
[preset.{idx}]

name="macOS"
platform="macOS"
runnable=true
dedicated_server=false
custom_features=""
export_filter="all_resources"
include_filter=""
exclude_filter=""

[preset.{idx}.options]

custom_template/debug=""
custom_template/release=""
codesign/codesign=0
""",
    },
    "linux": {
        "preset_name": "Linux",
        "export_ext": ".x86_64",
        "template_name": "linux",
        "preset_cfg": """\
[preset.{idx}]

name="Linux"
platform="Linux/X11"
runnable=true
dedicated_server=false
custom_features=""
export_filter="all_resources"
include_filter=""
exclude_filter=""

[preset.{idx}.options]

custom_template/debug=""
custom_template/release=""
binary_format/embed_pck=true
texture_format/s3tc_bptc=true
texture_format/etc2_astc=false
""",
    },
    "android": {
        "preset_name": "Android",
        "export_ext": ".apk",
        "template_name": "android",
        "preset_cfg": """\
[preset.{idx}]

name="Android"
platform="Android"
runnable=true
dedicated_server=false
custom_features=""
export_filter="all_resources"
include_filter=""
exclude_filter=""

[preset.{idx}.options]

custom_template/debug=""
custom_template/release=""
package/unique_name="com.godotforge.game"
package/name=""
screen/immersive_mode=true
""",
    },
    "web": {
        "preset_name": "Web",
        "export_ext": ".html",
        "template_name": "web",
        "preset_cfg": """\
[preset.{idx}]

name="Web"
platform="Web"
runnable=true
dedicated_server=false
custom_features=""
export_filter="all_resources"
include_filter=""
exclude_filter=""

[preset.{idx}.options]

custom_template/debug=""
custom_template/release=""
variant/extensions_support=false
vram_texture_compression/for_desktop=true
vram_texture_compression/for_mobile=false
html/export_icon=true
html/canvas_resize_policy=2
""",
    },
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _builds_dir(owner_id: str, project_id: str) -> Path:
    d = PROJECTS_ROOT / owner_id / project_id / ".builds"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _ensure_export_presets(proj_dir: Path, platform: str) -> None:
    """Write an export_presets.cfg if one doesn't exist yet."""
    cfg_path = proj_dir / "export_presets.cfg"
    preset_info = _PLATFORM_PRESETS[platform]

    if cfg_path.exists():
        content = cfg_path.read_text()
        # Check if the platform preset already exists
        if preset_info["preset_name"] in content:
            return
        # Append new preset — count existing presets to get next index
        idx = content.count("[preset.")
        # Each preset has sub-sections, so count unique preset blocks
        existing_indexes = set()
        for line in content.splitlines():
            if line.startswith("[preset.") and "]" in line:
                part = line.split(".")[1].split("]")[0].split(".")[0]
                try:
                    existing_indexes.add(int(part))
                except ValueError:
                    pass
        next_idx = max(existing_indexes, default=-1) + 1
        content += "\n" + preset_info["preset_cfg"].format(idx=next_idx)
        cfg_path.write_text(content)
    else:
        cfg_path.write_text(preset_info["preset_cfg"].format(idx=0))


async def _run_godot_export(
    proj_dir: Path,
    preset_name: str,
    output_path: Path,
    debug: bool,
    extra_args: list[str],
) -> tuple[int, str]:
    """Run Godot headless export and return (return_code, log)."""
    godot = settings.godot_path
    mode_flag = "--export-debug" if debug else "--export-release"

    cmd = [
        godot,
        "--headless",
        "--path", str(proj_dir),
        mode_flag, preset_name, str(output_path),
        *extra_args,
    ]

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=str(proj_dir),
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=300)
        log = stdout.decode(errors="replace") if stdout else ""
        return proc.returncode or 0, log
    except FileNotFoundError:
        return -1, f"Godot executable not found at '{godot}'. Set GODOTFORGE_GODOT_PATH."
    except asyncio.TimeoutError:
        return -2, "Export timed out after 300 seconds."
    except Exception as exc:
        return -3, f"Export error: {exc}"


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/export", response_model=BuildResponse)
async def export_project(body: BuildRequest, user: Annotated[dict, Depends(get_current_user)]):
    """Run a Godot headless export for the specified platform."""
    owner_id = user["id"]
    proj = _find_project(owner_id, body.project_id)
    if proj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    proj_dir = _project_dir(owner_id, body.project_id)
    if not (proj_dir / "project.godot").exists():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Not a valid Godot project (missing project.godot)",
        )

    platform_info = _PLATFORM_PRESETS[body.platform]
    build_id = uuid.uuid4().hex[:10]
    builds = _builds_dir(owner_id, body.project_id)
    output_dir = builds / body.platform
    output_dir.mkdir(parents=True, exist_ok=True)

    game_name = proj.get("name", "game").replace(" ", "_").lower()
    output_file = output_dir / (game_name + platform_info["export_ext"])

    # Ensure export presets config exists
    _ensure_export_presets(proj_dir, body.platform)

    started = datetime.now(timezone.utc).isoformat()
    return_code, log = await _run_godot_export(
        proj_dir=proj_dir,
        preset_name=platform_info["preset_name"],
        output_path=output_file,
        debug=body.config.debug,
        extra_args=body.config.extra_args,
    )
    finished = datetime.now(timezone.utc).isoformat()

    build_status = "success" if return_code == 0 else "failed"

    return BuildResponse(
        build_id=build_id,
        project_id=body.project_id,
        platform=body.platform,
        status=build_status,
        output_path=str(output_file) if return_code == 0 else "",
        log=log,
        started_at=started,
        finished_at=finished,
    )


@router.get("/download/{project_id}/{platform}")
async def download_build(
    project_id: str,
    platform: str,
    user: Annotated[dict, Depends(get_current_user)],
):
    """Download the most recently built export for a project+platform."""
    if platform not in SUPPORTED_PLATFORMS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported platform. Choose from: {', '.join(SUPPORTED_PLATFORMS)}",
        )

    owner_id = user["id"]
    proj = _find_project(owner_id, project_id)
    if proj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    builds = _builds_dir(owner_id, project_id) / platform
    if not builds.is_dir():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No builds found for platform '{platform}'",
        )

    # Find the newest file in the build directory
    files = sorted(builds.iterdir(), key=lambda f: f.stat().st_mtime, reverse=True)
    files = [f for f in files if f.is_file()]
    if not files:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No build artifacts found",
        )

    target = files[0]
    media_type_map = {
        ".exe": "application/octet-stream",
        ".zip": "application/zip",
        ".x86_64": "application/octet-stream",
        ".apk": "application/vnd.android.package-archive",
        ".html": "text/html",
    }
    media = media_type_map.get(target.suffix, "application/octet-stream")

    return FastAPIFileResponse(
        path=str(target),
        filename=target.name,
        media_type=media,
    )


@router.get("/platforms")
async def list_platforms():
    """List all supported export platforms."""
    return {
        "platforms": [
            {
                "id": pid,
                "name": info["preset_name"],
                "extension": info["export_ext"],
            }
            for pid, info in _PLATFORM_PRESETS.items()
        ]
    }
