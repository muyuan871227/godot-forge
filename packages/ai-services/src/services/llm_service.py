"""LLM 统一服务 — 支持多供应商切换"""
import re

from ..config import settings

GDSCRIPT_SYSTEM_PROMPT = """You are an expert Godot 4.x game developer.
You write clean, efficient GDScript that follows Godot 4 conventions.

Key rules:
- Use @export, @onready annotations
- Use typed variables (var speed: float = 100.0)
- Use signal declarations (signal health_changed(new_health: int))
- Use StringName for signal connections
- Use Node paths with $ shorthand where appropriate
- Follow Godot 4 API (not Godot 3)

Always respond with valid, complete GDScript code.
Include explanatory comments.
If creating multiple files, clearly separate them with file paths."""


async def generate_gdscript(
    prompt: str,
    context: str = "",
    scene_tree: str = "",
    existing_scripts: list[str] | None = None,
    godot_version: str = "4.4",
) -> dict:
    """统一 GDScript 生成接口"""

    # 构建上下文
    full_prompt = f"Godot {godot_version} project.\n"
    if scene_tree:
        full_prompt += f"\nCurrent scene tree:\n{scene_tree}\n"
    if context:
        full_prompt += f"\nAdditional context:\n{context}\n"
    if existing_scripts:
        for s in existing_scripts:
            full_prompt += f"\nExisting script:\n{s}\n"
    full_prompt += f"\nTask: {prompt}"

    if settings.llm_provider == "anthropic":
        return await _generate_anthropic(full_prompt)
    elif settings.llm_provider == "openai":
        return await _generate_openai(full_prompt)
    elif settings.llm_provider == "ollama":
        return await _generate_ollama(full_prompt)
    else:
        raise ValueError(f"Unknown LLM provider: {settings.llm_provider}")


async def _generate_anthropic(prompt: str) -> dict:
    import anthropic

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    response = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=8192,
        system=GDSCRIPT_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    text = response.content[0].text
    return _parse_code_response(text)


async def _generate_openai(prompt: str) -> dict:
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": GDSCRIPT_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        max_tokens=8192,
    )
    text = response.choices[0].message.content
    return _parse_code_response(text)


async def _generate_ollama(prompt: str) -> dict:
    import httpx

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{settings.ollama_base_url}/api/chat",
            json={
                "model": settings.ollama_model,
                "messages": [
                    {"role": "system", "content": GDSCRIPT_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                "stream": False,
            },
        )
        data = response.json()
        text = data.get("message", {}).get("content", "")
        return _parse_code_response(text)


def _parse_code_response(text: str) -> dict:
    """解析 LLM 响应，提取代码块和说明"""
    files = []
    code_blocks = re.findall(r"```(?:gdscript|gd)?\s*\n(.*?)```", text, re.DOTALL)

    # 尝试提取文件路径
    path_pattern = re.compile(r"#\s*(?:File|Path|file|path):\s*(res://\S+)")
    for block in code_blocks:
        path_match = path_pattern.search(block)
        path = (
            path_match.group(1)
            if path_match
            else f"res://scripts/generated_{len(files)}.gd"
        )
        files.append({"path": path, "content": block.strip()})

    # 提取非代码部分作为说明
    explanation = re.sub(r"```.*?```", "", text, flags=re.DOTALL).strip()

    return {
        "code": code_blocks[0] if code_blocks else "",
        "explanation": explanation,
        "files": files,
    }
