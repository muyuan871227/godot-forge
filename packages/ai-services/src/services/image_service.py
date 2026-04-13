"""图像生成服务 — 支持 ComfyUI / Replicate 等多后端"""
import asyncio
import base64
import json
import uuid
from typing import Any

import httpx

from ..config import settings

# 预定义风格提示词
STYLE_PROMPTS: dict[str, str] = {
    "pixel_art": (
        "pixel art style, 16-bit retro game art, clean pixel edges, "
        "limited color palette, no anti-aliasing, game asset"
    ),
    "hand_drawn": (
        "hand drawn illustration style, pencil sketch, watercolor texture, "
        "organic lines, storybook art, game asset"
    ),
    "anime": (
        "anime style, cel shading, vibrant colors, clean lines, "
        "Japanese animation aesthetic, game character art"
    ),
    "realistic": (
        "photorealistic style, detailed textures, physically based rendering, "
        "high quality game asset, AAA game quality"
    ),
}


async def generate_image(
    prompt: str,
    style: str = "pixel_art",
    width: int = 512,
    height: int = 512,
    negative_prompt: str = "",
    transparent_bg: bool = False,
) -> dict[str, Any]:
    """统一图像生成接口

    Args:
        prompt: 图像描述
        style: 风格预设 (pixel_art, hand_drawn, anime, realistic)
        width: 图像宽度
        height: 图像高度
        negative_prompt: 负面提示词
        transparent_bg: 是否透明背景

    Returns:
        dict with keys: image_base64, width, height, format
    """
    # 用风格提示词增强用户提示
    style_suffix = STYLE_PROMPTS.get(style, STYLE_PROMPTS["pixel_art"])
    enhanced_prompt = f"{prompt}, {style_suffix}"

    if transparent_bg:
        enhanced_prompt += ", transparent background, PNG"

    default_negative = (
        "blurry, low quality, watermark, text, signature, deformed, "
        "ugly, duplicate, morbid"
    )
    full_negative = f"{default_negative}, {negative_prompt}" if negative_prompt else default_negative

    if settings.image_provider == "comfyui":
        return await _generate_comfyui(
            prompt=enhanced_prompt,
            negative_prompt=full_negative,
            width=width,
            height=height,
        )
    elif settings.image_provider == "replicate":
        return await _generate_replicate(
            prompt=enhanced_prompt,
            negative_prompt=full_negative,
            width=width,
            height=height,
        )
    else:
        raise ValueError(f"Unknown image provider: {settings.image_provider}")


async def _generate_comfyui(
    prompt: str,
    negative_prompt: str,
    width: int,
    height: int,
) -> dict[str, Any]:
    """通过 ComfyUI API 生成图像 — 提交 SDXL 工作流并轮询结果"""

    # SDXL txt2img 基础工作流
    workflow = {
        "3": {
            "class_type": "KSampler",
            "inputs": {
                "seed": -1,
                "steps": 25,
                "cfg": 7.0,
                "sampler_name": "euler_ancestral",
                "scheduler": "normal",
                "denoise": 1.0,
                "model": ["4", 0],
                "positive": ["6", 0],
                "negative": ["7", 0],
                "latent_image": ["5", 0],
            },
        },
        "4": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {
                "ckpt_name": "sd_xl_base_1.0.safetensors",
            },
        },
        "5": {
            "class_type": "EmptyLatentImage",
            "inputs": {
                "width": width,
                "height": height,
                "batch_size": 1,
            },
        },
        "6": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": prompt,
                "clip": ["4", 1],
            },
        },
        "7": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": negative_prompt,
                "clip": ["4", 1],
            },
        },
        "8": {
            "class_type": "VAEDecode",
            "inputs": {
                "samples": ["3", 0],
                "vae": ["4", 2],
            },
        },
        "9": {
            "class_type": "SaveImage",
            "inputs": {
                "filename_prefix": "godotforge",
                "images": ["8", 0],
            },
        },
    }

    client_id = str(uuid.uuid4())
    base_url = settings.comfyui_url.rstrip("/")

    async with httpx.AsyncClient(timeout=180.0) as client:
        # 提交工作流
        queue_resp = await client.post(
            f"{base_url}/prompt",
            json={"prompt": workflow, "client_id": client_id},
        )
        queue_resp.raise_for_status()
        prompt_id = queue_resp.json()["prompt_id"]

        # 轮询直到完成
        for _ in range(120):  # 最多等 120 秒
            await asyncio.sleep(1.0)
            history_resp = await client.get(f"{base_url}/history/{prompt_id}")
            history_resp.raise_for_status()
            history = history_resp.json()

            if prompt_id in history:
                outputs = history[prompt_id].get("outputs", {})
                # SaveImage 节点 ID 为 "9"
                save_output = outputs.get("9", {})
                images = save_output.get("images", [])
                if images:
                    image_info = images[0]
                    filename = image_info["filename"]
                    subfolder = image_info.get("subfolder", "")
                    img_type = image_info.get("type", "output")

                    # 下载图像
                    params = {
                        "filename": filename,
                        "subfolder": subfolder,
                        "type": img_type,
                    }
                    img_resp = await client.get(f"{base_url}/view", params=params)
                    img_resp.raise_for_status()

                    image_base64 = base64.b64encode(img_resp.content).decode("utf-8")
                    return {
                        "image_base64": image_base64,
                        "width": width,
                        "height": height,
                        "format": "png",
                    }

        raise TimeoutError("ComfyUI generation timed out after 120 seconds")


async def _generate_replicate(
    prompt: str,
    negative_prompt: str,
    width: int,
    height: int,
) -> dict[str, Any]:
    """通过 Replicate API 生成图像（预留接口）

    需要设置 GODOTFORGE_REPLICATE_API_TOKEN 环境变量。
    当前为 stub 实现 — 返回占位结果。
    """
    # TODO: Phase 2 — 对接 Replicate SDXL API
    # 完整实现将:
    # 1. 调用 replicate.run("stability-ai/sdxl:...") 提交生成任务
    # 2. 轮询获取结果 URL
    # 3. 下载并转换为 base64
    return {
        "image_base64": "",
        "width": width,
        "height": height,
        "format": "png",
        "status": "not_implemented",
        "message": "Replicate provider coming soon. Use ComfyUI for now.",
    }
