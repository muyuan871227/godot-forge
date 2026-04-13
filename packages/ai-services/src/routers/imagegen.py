"""图像生成路由 — Phase 0 骨架"""
from fastapi import APIRouter

router = APIRouter()


@router.post("/generate")
async def generate_image(prompt: str, style: str = "pixel_art"):
    """生成游戏图像资产（Phase 2 实现）"""
    return {"status": "not_implemented", "message": "Image generation coming in Phase 2"}
