"""代码生成路由"""
from fastapi import APIRouter
from pydantic import BaseModel

from ..services.llm_service import generate_gdscript

router = APIRouter()


class CodeGenRequest(BaseModel):
    prompt: str
    context: str = ""
    scene_tree: str = ""
    existing_scripts: list[str] = []
    godot_version: str = "4.4"


class CodeGenResponse(BaseModel):
    code: str
    explanation: str
    files: list[dict]


@router.post("/generate", response_model=CodeGenResponse)
async def generate_code(req: CodeGenRequest):
    result = await generate_gdscript(
        prompt=req.prompt,
        context=req.context,
        scene_tree=req.scene_tree,
        existing_scripts=req.existing_scripts,
        godot_version=req.godot_version,
    )
    return result


@router.post("/fix")
async def fix_errors(errors: list[str], script_content: str):
    """根据错误信息修复 GDScript"""
    result = await generate_gdscript(
        prompt=f"Fix these GDScript errors:\n" + "\n".join(errors),
        context=script_content,
    )
    return result


@router.post("/explain")
async def explain_code(code: str):
    """解释 GDScript 代码"""
    result = await generate_gdscript(
        prompt=f"Explain this GDScript code in detail:\n{code}",
    )
    return {"explanation": result.get("explanation", "")}
