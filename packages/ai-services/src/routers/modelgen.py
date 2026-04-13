"""3D 模型生成路由 — Hunyuan3D / TripoSR"""
import base64
import tempfile
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class Model3DRequest(BaseModel):
    prompt: str = ""
    image_base64: str = ""
    provider: str = "hunyuan3d"  # hunyuan3d | triposr
    with_texture: bool = True
    output_format: str = "glb"  # glb | obj | fbx


class Model3DResponse(BaseModel):
    model_path: str
    format: str
    vertices: int = 0
    faces: int = 0
    has_texture: bool = False


class OptimizeRequest(BaseModel):
    model_path: str
    target_faces: int = 5000


class RetextureRequest(BaseModel):
    model_path: str
    style_prompt: str


@router.post("/generate", response_model=Model3DResponse)
async def generate_3d_model(req: Model3DRequest):
    """从文字或参考图生成 3D 模型"""
    if req.provider == "hunyuan3d":
        try:
            from ..providers.hunyuan3d import hunyuan3d_service

            if req.image_base64:
                # Save base64 image to temp file
                img_path = _save_temp_image(req.image_base64)
                result = await hunyuan3d_service.generate_from_image(
                    img_path, with_texture=req.with_texture
                )
            elif req.prompt:
                result = await hunyuan3d_service.generate_from_text(
                    req.prompt, with_texture=req.with_texture
                )
            else:
                return {"error": "Either prompt or image_base64 is required"}
            return result
        except ImportError:
            return {
                "model_path": "",
                "format": req.output_format,
                "error": "Hunyuan3D not available. Install dependencies first.",
            }

    elif req.provider == "triposr":
        try:
            from ..providers.triposr import triposr_service

            if req.image_base64:
                img_path = _save_temp_image(req.image_base64)
                result = await triposr_service.generate(img_path)
                return result
            elif req.prompt:
                # TripoSR needs an image — generate one first
                from ..services.image_service import generate_image

                img_result = await generate_image(
                    prompt=f"3D model reference, {req.prompt}, white background, studio lighting",
                    style="realistic",
                    width=512,
                    height=512,
                )
                img_path = _save_temp_image(img_result["image_base64"])
                return await triposr_service.generate(img_path)
            else:
                return {"error": "Either prompt or image_base64 is required"}
        except ImportError:
            return {
                "model_path": "",
                "format": req.output_format,
                "error": "TripoSR not available. Install dependencies first.",
            }

    return {"error": f"Unknown provider: {req.provider}"}


@router.post("/texture")
async def retexture_model(req: RetextureRequest):
    """为已有模型重新生成纹理"""
    try:
        from ..providers.hunyuan3d import hunyuan3d_service

        # Generate style reference image
        from ..services.image_service import generate_image

        ref = await generate_image(
            prompt=f"texture reference, {req.style_prompt}, seamless, PBR material",
            style="realistic",
            width=512,
            height=512,
        )

        result = await hunyuan3d_service.retexture(
            req.model_path, ref["image_base64"]
        )
        return result
    except (ImportError, AttributeError):
        return {"error": "Retexturing not available. Hunyuan3D required."}


@router.post("/optimize")
async def optimize_model(req: OptimizeRequest):
    """优化模型面数 (减面适配移动端)"""
    try:
        import trimesh

        mesh = trimesh.load(req.model_path)
        original_faces = len(mesh.faces)

        if original_faces <= req.target_faces:
            return {
                "model_path": req.model_path,
                "original_faces": original_faces,
                "optimized_faces": original_faces,
                "note": "Model already under target face count",
            }

        simplified = mesh.simplify_quadric_decimation(req.target_faces)
        output_path = req.model_path.replace(".glb", "_optimized.glb")
        simplified.export(output_path)

        return {
            "model_path": output_path,
            "original_faces": original_faces,
            "optimized_faces": len(simplified.faces),
            "reduction": f"{(1 - len(simplified.faces) / original_faces) * 100:.1f}%",
        }
    except ImportError:
        return {"error": "trimesh not installed. Run: pip install trimesh"}


def _save_temp_image(image_base64: str) -> str:
    """Save base64 image to a temporary file and return the path."""
    img_data = base64.b64decode(image_base64)
    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False, dir="/tmp/godotforge")
    Path(tmp.name).parent.mkdir(parents=True, exist_ok=True)
    tmp.write(img_data)
    tmp.close()
    return tmp.name
