"""TripoSR 本地 3D 模型生成服务

轻量级单图像到 3D 模型生成器，适合快速原型。
GPU 依赖通过 try/except 保护，在无 GPU 环境下提供优雅降级。
"""
import asyncio
import logging
import time
import uuid
from pathlib import Path
from typing import Any

from ..config import settings

logger = logging.getLogger(__name__)

# 模型输出目录
MODEL_OUTPUT_DIR = Path("/tmp/godotforge/models")
MODEL_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


class TripoSRService:
    """TripoSR 单图像到 3D 模型生成服务

    基于 StabilityAI 的 TripoSR 模型，从单张图像快速生成 3D 网格。
    相比 Hunyuan3D 更轻量，适合快速迭代。
    """

    def __init__(self) -> None:
        self._model: Any = None
        self._available: bool = True
        self._unavailable_reason: str = ""
        self._load_attempted: bool = False

        self._try_load_model()

    def _try_load_model(self) -> None:
        """尝试加载 TSR 模型"""
        if self._load_attempted:
            return
        self._load_attempted = True

        try:
            import torch
            from tsr.system import TSR

            device = "cuda:0" if torch.cuda.is_available() else "cpu"

            logger.info("Loading TripoSR model on %s ...", device)
            self._model = TSR.from_pretrained(
                "stabilityai/TripoSR",
                config_name="config.yaml",
                weight_name="model.ckpt",
            )
            self._model.renderer.set_chunk_size(8192)
            self._model.to(device)

            logger.info("TripoSR model loaded successfully on %s", device)

        except ImportError as exc:
            self._available = False
            self._unavailable_reason = (
                f"TripoSR dependencies not installed: {exc}. "
                "Install from: https://github.com/VAST-AI-Research/TripoSR"
            )
            logger.warning(self._unavailable_reason)

        except Exception as exc:
            self._available = False
            self._unavailable_reason = f"TripoSR model loading failed: {exc}"
            logger.error(self._unavailable_reason)

    async def generate(
        self,
        image_path: str,
    ) -> dict[str, Any]:
        """从单张图像生成 3D 模型

        Args:
            image_path: 输入图像的本地路径

        Returns:
            dict with keys: model_path, format, vertices, faces, duration_seconds
        """
        if not self._available:
            return {
                "status": "not_available",
                "message": self._unavailable_reason,
                "model_path": "",
                "format": "obj",
            }

        if self._model is None:
            return {
                "status": "error",
                "message": "TripoSR model is not loaded",
                "model_path": "",
                "format": "obj",
            }

        start_time = time.monotonic()

        # 在线程池中运行 GPU 推理
        result = await asyncio.get_event_loop().run_in_executor(
            None,
            self._run_inference,
            image_path,
        )

        elapsed = time.monotonic() - start_time
        result["duration_seconds"] = round(elapsed, 2)
        return result

    def _run_inference(self, image_path: str) -> dict[str, Any]:
        """同步执行 TripoSR 推理（在线程池中调用）"""
        try:
            import numpy as np
            from PIL import Image

            # 加载并预处理图像
            input_image = Image.open(image_path).convert("RGB")

            # TripoSR 期望 512x512 输入
            input_image = input_image.resize((512, 512), Image.Resampling.LANCZOS)

            # 运行推理
            logger.info("Running TripoSR inference on %s ...", image_path)

            with __import__("torch").no_grad():
                scene_codes = self._model([input_image], device=self._model.device)

            # 提取网格
            meshes = self._model.extract_mesh(scene_codes, resolution=256)
            mesh = meshes[0]

            # 生成输出路径
            output_filename = f"triposr_{uuid.uuid4().hex[:12]}.obj"
            output_path = MODEL_OUTPUT_DIR / output_filename

            # 导出网格
            vertices_count, faces_count = self._export_mesh(mesh, str(output_path))

            logger.info(
                "Generated 3D model: %s (vertices=%d, faces=%d)",
                output_path,
                vertices_count,
                faces_count,
            )

            return {
                "status": "success",
                "model_path": str(output_path),
                "format": "obj",
                "vertices": vertices_count,
                "faces": faces_count,
            }

        except Exception as exc:
            logger.error("TripoSR inference failed: %s", exc)
            return {
                "status": "error",
                "message": str(exc),
                "model_path": "",
                "format": "obj",
                "vertices": 0,
                "faces": 0,
            }

    def _export_mesh(
        self,
        mesh: Any,
        output_path: str,
    ) -> tuple[int, int]:
        """导出网格为 OBJ 文件

        Args:
            mesh: TripoSR 输出的网格对象
            output_path: 输出文件路径

        Returns:
            (vertices_count, faces_count)
        """
        try:
            import trimesh

            # TripoSR 网格输出通常有 vertices 和 faces 属性
            if hasattr(mesh, "vertices") and hasattr(mesh, "faces"):
                import numpy as np

                verts = np.array(mesh.vertices)
                face_data = np.array(mesh.faces)

                tri_mesh = trimesh.Trimesh(vertices=verts, faces=face_data)
            elif isinstance(mesh, trimesh.Trimesh):
                tri_mesh = mesh
            else:
                # 尝试直接从 mesh 对象转换
                tri_mesh = trimesh.Trimesh(
                    vertices=getattr(mesh, "v", mesh.vertices),
                    faces=getattr(mesh, "f", mesh.faces),
                )

            vertices_count = len(tri_mesh.vertices)
            faces_count = len(tri_mesh.faces)

            tri_mesh.export(output_path, file_type="obj")
            return vertices_count, faces_count

        except ImportError:
            # trimesh 不可用 — 手动写 OBJ
            logger.warning("trimesh not installed, writing basic OBJ manually")
            return self._manual_obj_export(mesh, output_path)

    def _manual_obj_export(
        self,
        mesh: Any,
        output_path: str,
    ) -> tuple[int, int]:
        """手动 OBJ 导出（trimesh 不可用时的后备）"""
        import numpy as np

        vertices = np.array(mesh.vertices)
        faces = np.array(mesh.faces)

        lines: list[str] = [
            "# Generated by GodotForge TripoSR",
        ]

        for v in vertices:
            lines.append(f"v {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}")

        for f in faces:
            # OBJ 使用 1-indexed 面索引
            lines.append(f"f {f[0] + 1} {f[1] + 1} {f[2] + 1}")

        Path(output_path).write_text("\n".join(lines), encoding="utf-8")
        return len(vertices), len(faces)


# ---------------------------------------------------------------------------
# 单例
# ---------------------------------------------------------------------------

triposr_service = TripoSRService()
