"""音频生成路由 — Phase 0 骨架"""
from fastapi import APIRouter

router = APIRouter()


@router.post("/generate")
async def generate_audio(prompt: str, type: str = "sfx"):
    """生成音频资产（Phase 2 实现）"""
    return {"status": "not_implemented", "message": "Audio generation coming in Phase 2"}
