"""Hunyuan3D 本地 3D 模型生成服务

支持从图像或文本描述生成 3D 模型（GLB 格式）。
GPU 依赖通过 try/except 保护，在无 GPU 环境下提供优雅降级。
"""
import asyncio
import base64
import logging
import os
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any

from ..config import settings

logger = logging.getLogger(__name__)

# 模型输出目录
MODEL_OUTPUT_DIR = Path("/tmp/godotforge/models")
MODEL_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


class Hunyuan3DService:
    """Hunyuan3D 3D 模型生成服务 — 懒加载模式

    支持两种生成方式:
    1. 从图像生成 3D 模型 (image-to-3D)
    2. 从文本描述生成 3D 模型 (text-to-3D, 先生成参考图再转 3D)
    """

    def __init__(self) -> None:
        self._loaded: bool = False
        self._image_to_3d_pipeline: Any = None
        self._text_to_image_pipeline: Any = None
        self._available: bool = True
        self._unavailable_reason: str = ""

    def _ensure_loaded(self) -> None:
        """懒加载 Hunyuan3D 管线 — 首次调用时加载模型到 GPU"""
        if self._loaded:
            return

        try:
            import torch
            from diffusers import DiffusionPipeline

            model_path = settings.hunyuan3d_path or "tencent/Hunyuan3D-2"

            logger.info("Loading Hunyuan3D image-to-3D pipeline from %s ...", model_path)
            self._image_to_3d_pipeline = DiffusionPipeline.from_pretrained(
                model_path,
                torch_dtype=torch.float16,
                trust_remote_code=True,
            )

            device = "cuda" if torch.cuda.is_available() else "cpu"
            self._image_to_3d_pipeline = self._image_to_3d_pipeline.to(device)
            logger.info("Hunyuan3D image-to-3D pipeline loaded on %s", device)

            # 文本到图像管线 — 用于 text-to-3D 流程中先生成参考图
            try:
                self._text_to_image_pipeline = DiffusionPipeline.from_pretrained(
                    "stabilityai/stable-diffusion-xl-base-1.0",
                    torch_dtype=torch.float16,
                    variant="fp16",
                    use_safetensors=True,
                )
                self._text_to_image_pipeline = self._text_to_image_pipeline.to(device)
                logger.info("Text-to-image pipeline loaded for text-to-3D flow")
            except Exception as exc:
                logger.warning(
                    "Could not load text-to-image pipeline: %s. "
                    "text-to-3D will not be available.",
                    exc,
                )
                self._text_to_image_pipeline = None

            self._loaded = True

        except ImportError as exc:
            self._available = False
            self._unavailable_reason = (
                f"Hunyuan3D dependencies not installed: {exc}. "
                "Install with: pip install torch diffusers transformers accelerate"
            )
            logger.warning(self._unavailable_reason)
            self._loaded = True  # 标记为已尝试，避免反复加载

    async def generate_from_image(
        self,
        image_path: str,
        with_texture: bool = True,
    ) -> dict[str, Any]:
        """从输入图像生成 3D 模型

        Args:
            image_path: 输入图像的本地路径
            with_texture: 是否生成纹理贴图

        Returns:
            dict with keys: model_path, format, vertices, faces, has_texture, duration_seconds
        """
        self._ensure_loaded()

        if not self._available:
            return {
                "status": "not_available",
                "message": self._unavailable_reason,
                "model_path": "",
                "format": "glb",
                "vertices": 0,
                "faces": 0,
                "has_texture": False,
            }

        if self._image_to_3d_pipeline is None:
            return {
                "status": "error",
                "message": "Hunyuan3D pipeline failed to load",
                "model_path": "",
                "format": "glb",
                "vertices": 0,
                "faces": 0,
                "has_texture": False,
            }

        start_time = time.monotonic()

        # 在线程池中运行 GPU 推理，避免阻塞事件循环
        result = await asyncio.get_event_loop().run_in_executor(
            None,
            self._run_image_to_3d,
            image_path,
            with_texture,
        )

        elapsed = time.monotonic() - start_time
        result["duration_seconds"] = round(elapsed, 2)
        return result

    def _run_image_to_3d(
        self,
        image_path: str,
        with_texture: bool,
    ) -> dict[str, Any]:
        """同步执行 image-to-3D 推理（在线程池中调用）"""
        from PIL import Image

        try:
            input_image = Image.open(image_path).convert("RGB")

            # 标准化输入尺寸
            input_image = input_image.resize((512, 512), Image.Resampling.LANCZOS)

            # 运行 Hunyuan3D 管线
            output = self._image_to_3d_pipeline(
                image=input_image,
                num_inference_steps=50,
                guidance_scale=7.5,
            )

            # 生成输出文件路径
            output_filename = f"hunyuan3d_{uuid.uuid4().hex[:12]}.glb"
            output_path = MODEL_OUTPUT_DIR / output_filename

            # 导出为 GLB
            vertices, faces = self._export_to_glb(output, str(output_path), with_texture)

            logger.info(
                "Generated 3D model: %s (vertices=%d, faces=%d, textured=%s)",
                output_path,
                vertices,
                faces,
                with_texture,
            )

            return {
                "status": "success",
                "model_path": str(output_path),
                "format": "glb",
                "vertices": vertices,
                "faces": faces,
                "has_texture": with_texture,
            }

        except Exception as exc:
            logger.error("Hunyuan3D generation failed: %s", exc)
            return {
                "status": "error",
                "message": str(exc),
                "model_path": "",
                "format": "glb",
                "vertices": 0,
                "faces": 0,
                "has_texture": False,
            }

    def _export_to_glb(
        self,
        pipeline_output: Any,
        output_path: str,
        with_texture: bool,
    ) -> tuple[int, int]:
        """将管线输出导出为 GLB 文件

        Returns:
            (vertices_count, faces_count)
        """
        try:
            import trimesh

            # Hunyuan3D 输出通常包含 mesh 数据
            # 根据管线输出类型提取网格
            if hasattr(pipeline_output, "meshes") and pipeline_output.meshes:
                mesh = pipeline_output.meshes[0]
            elif hasattr(pipeline_output, "mesh"):
                mesh = pipeline_output.mesh
            elif hasattr(pipeline_output, "vertices") and hasattr(pipeline_output, "faces"):
                mesh = trimesh.Trimesh(
                    vertices=pipeline_output.vertices,
                    faces=pipeline_output.faces,
                )
            else:
                # 尝试从输出字典提取
                mesh_data = (
                    pipeline_output
                    if isinstance(pipeline_output, dict)
                    else getattr(pipeline_output, "__dict__", {})
                )
                vertices = mesh_data.get("vertices")
                faces = mesh_data.get("faces")
                if vertices is not None and faces is not None:
                    mesh = trimesh.Trimesh(vertices=vertices, faces=faces)
                else:
                    raise ValueError(
                        "Cannot extract mesh from pipeline output. "
                        f"Output type: {type(pipeline_output)}"
                    )

            # 如果是 trimesh.Scene, 合并所有网格
            if isinstance(mesh, trimesh.Scene):
                combined = trimesh.util.concatenate(
                    [g for g in mesh.geometry.values() if isinstance(g, trimesh.Trimesh)]
                )
                mesh = combined

            vertices_count = len(mesh.vertices)
            faces_count = len(mesh.faces)

            # 导出 GLB
            if with_texture and hasattr(mesh, "visual") and mesh.visual is not None:
                mesh.export(output_path, file_type="glb")
            else:
                # 无纹理模式 — 导出仅几何体
                mesh.visual = trimesh.visual.ColorVisual(
                    vertex_colors=[180, 180, 180, 255] * len(mesh.vertices)
                )
                mesh.export(output_path, file_type="glb")

            return vertices_count, faces_count

        except ImportError:
            logger.warning("trimesh not installed, writing raw GLB placeholder")
            # 写入空 GLB 占位
            Path(output_path).write_bytes(b"")
            return 0, 0

    async def generate_from_text(
        self,
        prompt: str,
        with_texture: bool = True,
    ) -> dict[str, Any]:
        """从文本描述生成 3D 模型

        工作流程:
        1. 使用 text-to-image 生成参考图
        2. 使用 image-to-3D 从参考图生成模型

        Args:
            prompt: 3D 模型描述
            with_texture: 是否生成纹理贴图

        Returns:
            dict with keys: model_path, format, vertices, faces, has_texture,
                           reference_image_path, duration_seconds
        """
        self._ensure_loaded()

        if not self._available:
            return {
                "status": "not_available",
                "message": self._unavailable_reason,
                "model_path": "",
                "format": "glb",
                "vertices": 0,
                "faces": 0,
                "has_texture": False,
                "reference_image_path": "",
            }

        if self._text_to_image_pipeline is None:
            return {
                "status": "not_available",
                "message": (
                    "Text-to-image pipeline not loaded. "
                    "Cannot generate 3D from text without image generation capability."
                ),
                "model_path": "",
                "format": "glb",
                "vertices": 0,
                "faces": 0,
                "has_texture": False,
                "reference_image_path": "",
            }

        start_time = time.monotonic()

        # Step 1: 生成参考图像
        reference_image_path = await asyncio.get_event_loop().run_in_executor(
            None,
            self._generate_reference_image,
            prompt,
        )

        if reference_image_path is None:
            return {
                "status": "error",
                "message": "Failed to generate reference image from text prompt",
                "model_path": "",
                "format": "glb",
                "vertices": 0,
                "faces": 0,
                "has_texture": False,
                "reference_image_path": "",
            }

        # Step 2: 从参考图生成 3D 模型
        result = await self.generate_from_image(
            image_path=reference_image_path,
            with_texture=with_texture,
        )

        elapsed = time.monotonic() - start_time
        result["reference_image_path"] = reference_image_path
        result["duration_seconds"] = round(elapsed, 2)
        return result

    def _generate_reference_image(self, prompt: str) -> str | None:
        """使用 text-to-image 管线生成参考图像

        Returns:
            生成的图像路径，失败时返回 None
        """
        try:
            # 增强提示词以适配 3D 生成
            enhanced_prompt = (
                f"{prompt}, 3D rendering style, front view, clean background, "
                "single object centered, studio lighting, high quality"
            )
            negative_prompt = (
                "multiple objects, busy background, text, watermark, "
                "blurry, low quality, cropped"
            )

            output = self._text_to_image_pipeline(
                prompt=enhanced_prompt,
                negative_prompt=negative_prompt,
                width=512,
                height=512,
                num_inference_steps=30,
                guidance_scale=7.5,
            )

            image = output.images[0]

            # 保存参考图像
            ref_filename = f"ref_{uuid.uuid4().hex[:12]}.png"
            ref_path = MODEL_OUTPUT_DIR / ref_filename
            image.save(str(ref_path))

            logger.info("Generated reference image: %s", ref_path)
            return str(ref_path)

        except Exception as exc:
            logger.error("Reference image generation failed: %s", exc)
            return None


# ---------------------------------------------------------------------------
# 单例
# ---------------------------------------------------------------------------

hunyuan3d_service = Hunyuan3DService()
