"""3D 模型生成路由 — Hunyuan3D / TripoSR 多后端支持"""
import base64
import logging
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..config import settings
from ..providers.hunyuan3d import hunyuan3d_service
from ..providers.triposr import triposr_service

logger = logging.getLogger(__name__)

router = APIRouter()

# 临时文件目录
TMP_DIR = Path("/tmp/godotforge/models")
TMP_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class Model3DRequest(BaseModel):
    prompt: str = Field(default="", description="3D 模型文本描述 (用于 text-to-3D)")
    image_base64: str = Field(default="", description="输入图像 base64 (用于 image-to-3D)")
    provider: str = Field(
        default="",
        description="指定供应商: hunyuan3d | triposr (留空使用配置默认值)",
    )
    with_texture: bool = Field(default=True, description="是否生成纹理贴图 (仅 Hunyuan3D)")
    output_format: str = Field(default="glb", description="输出格式: glb | obj")


class Model3DResponse(BaseModel):
    status: str
    model_path: str = ""
    format: str = "glb"
    vertices: int = 0
    faces: int = 0
    has_texture: bool = False
    duration_seconds: float = 0.0
    message: str = ""


class TextureRequest(BaseModel):
    model_path: str = Field(..., description="现有模型文件路径")
    texture_prompt: str = Field(..., description="纹理描述 (例如 'weathered stone texture')")
    style: str = Field(default="realistic", description="风格: realistic | stylized | pixel")


class TextureResponse(BaseModel):
    status: str
    model_path: str = ""
    texture_applied: bool = False
    message: str = ""


class OptimizeRequest(BaseModel):
    model_path: str = Field(..., description="要优化的模型文件路径")
    target_faces: int = Field(
        default=5000,
        ge=100,
        le=100000,
        description="目标面数",
    )
    preserve_uv: bool = Field(default=True, description="是否保留 UV 映射")


class OptimizeResponse(BaseModel):
    status: str
    model_path: str = ""
    original_faces: int = 0
    optimized_faces: int = 0
    reduction_percent: float = 0.0
    message: str = ""


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/generate", response_model=Model3DResponse)
async def generate_model(req: Model3DRequest):
    """生成 3D 模型

    支持两种模式:
    - text-to-3D: 提供 prompt (仅 Hunyuan3D)
    - image-to-3D: 提供 image_base64 (Hunyuan3D 或 TripoSR)
    """
    # 确定使用哪个供应商
    provider = req.provider or settings.model3d_provider

    if not req.prompt and not req.image_base64:
        raise HTTPException(
            status_code=400,
            detail="Either 'prompt' (text-to-3D) or 'image_base64' (image-to-3D) is required",
        )

    try:
        if req.image_base64:
            # Image-to-3D 模式
            image_path = _save_base64_image(req.image_base64)

            if provider == "triposr":
                result = await triposr_service.generate(image_path=image_path)
            else:
                result = await hunyuan3d_service.generate_from_image(
                    image_path=image_path,
                    with_texture=req.with_texture,
                )
        else:
            # Text-to-3D 模式
            if provider == "triposr":
                # TripoSR 不支持直接 text-to-3D，先生成参考图
                from ..services.image_service import generate_image

                img_result = await generate_image(
                    prompt=f"3D model reference, {req.prompt}, white background, studio lighting",
                    style="realistic",
                    width=512,
                    height=512,
                )
                image_path = _save_base64_image(img_result["image_base64"])
                result = await triposr_service.generate(image_path=image_path)
            else:
                result = await hunyuan3d_service.generate_from_text(
                    prompt=req.prompt,
                    with_texture=req.with_texture,
                )

        status = result.get("status", "error")
        if status == "not_available":
            raise HTTPException(
                status_code=503,
                detail=result.get("message", "Service not available"),
            )

        return Model3DResponse(
            status=status,
            model_path=result.get("model_path", ""),
            format=result.get("format", req.output_format),
            vertices=result.get("vertices", 0),
            faces=result.get("faces", 0),
            has_texture=result.get("has_texture", False),
            duration_seconds=result.get("duration_seconds", 0.0),
            message=result.get("message", ""),
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("3D model generation failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/texture", response_model=TextureResponse)
async def retexture_model(req: TextureRequest):
    """为现有 3D 模型重新生成纹理

    使用图像生成服务创建纹理贴图，然后应用到模型上。
    """
    model_path = Path(req.model_path)
    if not model_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Model file not found: {req.model_path}",
        )

    try:
        import trimesh
    except ImportError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"trimesh not installed: {exc}. Install with: pip install trimesh",
        ) from exc

    try:
        # 加载模型
        mesh = trimesh.load(str(model_path))
        if isinstance(mesh, trimesh.Scene):
            geometries = [
                g for g in mesh.geometry.values() if isinstance(g, trimesh.Trimesh)
            ]
            if not geometries:
                raise HTTPException(
                    status_code=400,
                    detail="Model contains no valid geometry",
                )
            mesh = trimesh.util.concatenate(geometries)

        # 生成纹理图像
        from ..services.image_service import generate_image

        style_map: dict[str, str] = {
            "realistic": "realistic",
            "stylized": "hand_drawn",
            "pixel": "pixel_art",
        }
        img_style = style_map.get(req.style, "realistic")

        texture_result = await generate_image(
            prompt=f"{req.texture_prompt}, seamless texture, tileable, PBR material",
            style=img_style,
            width=1024,
            height=1024,
            transparent_bg=False,
        )

        # 将纹理应用到模型
        texture_bytes = base64.b64decode(texture_result["image_base64"])

        import io

        import numpy as np
        from PIL import Image

        texture_image = Image.open(io.BytesIO(texture_bytes)).convert("RGB")

        # 创建 UV 映射（如果不存在）
        if not hasattr(mesh.visual, "uv") or mesh.visual.uv is None:
            # 简单的球形 UV 映射
            vertices = mesh.vertices
            center = vertices.mean(axis=0)
            normals = vertices - center
            norms = np.linalg.norm(normals, axis=1, keepdims=True)
            norms = np.where(norms == 0, 1, norms)
            normals = normals / norms

            u = 0.5 + np.arctan2(normals[:, 0], normals[:, 2]) / (2 * np.pi)
            v = 0.5 + np.arcsin(np.clip(normals[:, 1], -1, 1)) / np.pi
            uv = np.column_stack([u, v])
        else:
            uv = mesh.visual.uv

        # 应用纹理
        material = trimesh.visual.texture.SimpleMaterial(image=texture_image)
        color_visuals = trimesh.visual.TextureVisuals(uv=uv, material=material)
        mesh.visual = color_visuals

        # 保存新模型
        output_filename = f"textured_{uuid.uuid4().hex[:8]}{model_path.suffix}"
        output_path = TMP_DIR / output_filename

        file_type = "glb" if model_path.suffix.lower() == ".glb" else "obj"
        mesh.export(str(output_path), file_type=file_type)

        return TextureResponse(
            status="success",
            model_path=str(output_path),
            texture_applied=True,
            message=f"Texture applied successfully. New model saved at: {output_path}",
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Model retexturing failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/optimize", response_model=OptimizeResponse)
async def optimize_model(req: OptimizeRequest):
    """优化 3D 模型 — 减少面数

    使用 trimesh 的网格简化算法减少三角面数量，
    使模型适合实时游戏渲染。
    """
    model_path = Path(req.model_path)
    if not model_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Model file not found: {req.model_path}",
        )

    try:
        import trimesh
    except ImportError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"trimesh not installed: {exc}. Install with: pip install trimesh",
        ) from exc

    try:
        mesh = trimesh.load(str(model_path))
        if isinstance(mesh, trimesh.Scene):
            geometries = [
                g for g in mesh.geometry.values() if isinstance(g, trimesh.Trimesh)
            ]
            if not geometries:
                raise HTTPException(
                    status_code=400,
                    detail="Model contains no valid geometry",
                )
            mesh = trimesh.util.concatenate(geometries)

        original_faces = len(mesh.faces)

        if original_faces <= req.target_faces:
            return OptimizeResponse(
                status="success",
                model_path=req.model_path,
                original_faces=original_faces,
                optimized_faces=original_faces,
                reduction_percent=0.0,
                message="Model already has fewer faces than target. No optimization needed.",
            )

        # 使用 trimesh 的二次误差度量简化
        simplified = mesh.simplify_quadric_decimation(req.target_faces)

        optimized_faces = len(simplified.faces)
        reduction = ((original_faces - optimized_faces) / original_faces) * 100

        # 保存优化后的模型
        output_filename = f"optimized_{uuid.uuid4().hex[:8]}{model_path.suffix}"
        output_path = TMP_DIR / output_filename

        file_type = "glb" if model_path.suffix.lower() == ".glb" else "obj"
        simplified.export(str(output_path), file_type=file_type)

        return OptimizeResponse(
            status="success",
            model_path=str(output_path),
            original_faces=original_faces,
            optimized_faces=optimized_faces,
            reduction_percent=round(reduction, 1),
            message=(
                f"Reduced from {original_faces} to {optimized_faces} faces "
                f"({reduction:.1f}% reduction)"
            ),
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Model optimization failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _save_base64_image(image_base64: str) -> str:
    """将 base64 图像数据保存到临时文件

    Args:
        image_base64: base64 编码的图像数据

    Returns:
        保存的临时文件路径
    """
    image_bytes = base64.b64decode(image_base64)
    filename = f"input_{uuid.uuid4().hex[:12]}.png"
    file_path = TMP_DIR / filename
    file_path.write_bytes(image_bytes)
    return str(file_path)
