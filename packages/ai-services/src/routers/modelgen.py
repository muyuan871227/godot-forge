"""3D 模型生成路由 — Phase 0 骨架"""
from fastapi import APIRouter

router = APIRouter()


@router.post("/generate")
async def generate_model(prompt: str, format: str = "glb"):
    """生成 3D 模型（Phase 2 实现）"""
    return {"status": "not_implemented", "message": "3D model generation coming in Phase 2"}
