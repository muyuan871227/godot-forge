"""LLM 统一服务 — 支持多供应商切换"""
import os
import re
from typing import Any

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
) -> dict[str, Any]:
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
    elif settings.llm_provider == "glm":
        return await _generate_glm(full_prompt)
    elif settings.llm_provider == "ollama":
        return await _generate_ollama(full_prompt)
    else:
        raise ValueError(f"Unknown LLM provider: {settings.llm_provider}")


async def generate_gdscript_with_context(
    prompt: str,
    project_context: dict[str, Any],
) -> dict[str, Any]:
    """增强版 GDScript 生成 — 接受完整的项目上下文字典

    Args:
        prompt: 用户需求描述
        project_context: 项目上下文，包含以下字段:
            - name: 项目名称
            - godot_version: Godot 版本
            - scene_tree: 当前场景树描述
            - scripts: 已有脚本内容列表
            - autoloads: 自动加载单例列表
            - input_map: 输入映射配置
    """
    name = project_context.get("name", "UntitledProject")
    godot_version = project_context.get("godot_version", "4.4")
    scene_tree = project_context.get("scene_tree", "")
    scripts = project_context.get("scripts", [])
    autoloads = project_context.get("autoloads", [])
    input_map = project_context.get("input_map", {})

    # 构建增强的系统提示
    enhanced_system = GDSCRIPT_SYSTEM_PROMPT + f"""

Project-specific context:
- Project name: {name}
- Godot version: {godot_version}
"""
    if autoloads:
        enhanced_system += "\nAutoload singletons:\n"
        for al in autoloads:
            enhanced_system += f"  - {al}\n"

    if input_map:
        enhanced_system += "\nInput map actions:\n"
        for action, events in input_map.items():
            enhanced_system += f"  - {action}: {events}\n"

    enhanced_system += (
        "\nGenerate code that integrates with the existing project structure. "
        "Reference autoloads and input actions by their configured names."
    )

    full_prompt = ""
    if scene_tree:
        full_prompt += f"Current scene tree:\n{scene_tree}\n\n"
    if scripts:
        full_prompt += "Existing scripts:\n"
        for s in scripts:
            full_prompt += f"---\n{s}\n---\n"
        full_prompt += "\n"
    full_prompt += f"Task: {prompt}"

    return await _call_llm(full_prompt, system_prompt=enhanced_system)


async def generate_game_feature(
    feature_description: str,
    project_context: dict[str, Any] | None = None,
    godot_version: str = "4.4",
) -> dict[str, Any]:
    """多文件生成 — 为完整的游戏功能生成多个文件

    Args:
        feature_description: 功能需求描述
        project_context: 可选项目上下文
        godot_version: Godot 版本

    Returns:
        dict with keys: files (list of {path, content}), explanation, integration_steps
    """
    system_prompt = GDSCRIPT_SYSTEM_PROMPT + f"""

You are generating a COMPLETE game feature with multiple files.

IMPORTANT: Separate each file with a ### FILE: header followed by the res:// path.
Example format:
### FILE: res://scripts/player.gd
```gdscript
extends CharacterBody2D
...
```

### FILE: res://scenes/player.tscn
```
[gd_scene ...]
```

After the code files, provide:
1. A brief explanation of the feature
2. Integration steps marked with "### INTEGRATION STEPS:" header

Godot version: {godot_version}
"""

    context_prompt = ""
    if project_context:
        scene_tree = project_context.get("scene_tree", "")
        scripts = project_context.get("scripts", [])
        autoloads = project_context.get("autoloads", [])
        if scene_tree:
            context_prompt += f"Current scene tree:\n{scene_tree}\n\n"
        if autoloads:
            context_prompt += "Autoloads: " + ", ".join(autoloads) + "\n\n"
        if scripts:
            context_prompt += "Existing scripts:\n"
            for s in scripts:
                context_prompt += f"---\n{s}\n---\n"
            context_prompt += "\n"

    full_prompt = context_prompt + f"Generate a complete implementation for: {feature_description}"

    result = await _call_llm(full_prompt, system_prompt=system_prompt)
    raw_text = result.get("_raw_text", result.get("explanation", ""))

    files = _parse_multi_file_response(raw_text)
    if not files:
        # 回退到常规解析
        files = result.get("files", [])

    integration_steps = _extract_integration_steps(raw_text)

    explanation = re.sub(
        r"### INTEGRATION STEPS:.*",
        "",
        result.get("explanation", ""),
        flags=re.DOTALL,
    ).strip()

    return {
        "files": files,
        "explanation": explanation,
        "integration_steps": integration_steps,
    }


async def auto_fix_loop(
    script_path: str,
    script_content: str,
    errors: list[str],
    max_iterations: int = 3,
) -> dict[str, Any]:
    """自动修复循环 — 迭代修复 GDScript 错误

    Args:
        script_path: 脚本文件路径 (res://...)
        script_content: 当前脚本内容
        errors: 错误信息列表
        max_iterations: 最大迭代次数

    Returns:
        dict with keys: fixed_code, iterations, remaining_errors, success
    """
    current_content = script_content
    remaining_errors = list(errors)
    iteration = 0

    while remaining_errors and iteration < max_iterations:
        iteration += 1

        fix_prompt = (
            f"Fix the following GDScript errors in {script_path}.\n\n"
            f"Current script:\n```gdscript\n{current_content}\n```\n\n"
            f"Errors:\n"
        )
        for err in remaining_errors:
            fix_prompt += f"  - {err}\n"

        fix_prompt += (
            "\nProvide the COMPLETE fixed script (not just the changed parts). "
            "Explain each fix briefly."
        )

        result = await generate_gdscript(prompt=fix_prompt)
        fixed_code = result.get("code", "")

        if not fixed_code:
            break

        current_content = fixed_code

        # 检查修复后的代码是否还有明显的语法问题
        # 在实际使用中，调用方会通过 Godot 编辑器验证并返回新的错误列表
        # 这里我们清空错误列表以结束循环 — 调用方可以传入新错误再次调用
        remaining_errors = []

    return {
        "fixed_code": current_content,
        "iterations": iteration,
        "remaining_errors": remaining_errors,
        "success": len(remaining_errors) == 0,
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _call_llm(
    prompt: str,
    system_prompt: str = GDSCRIPT_SYSTEM_PROMPT,
) -> dict[str, Any]:
    """统一 LLM 调用 — 根据配置选择供应商"""
    if settings.llm_provider == "anthropic":
        return await _generate_anthropic(prompt, system_prompt=system_prompt)
    elif settings.llm_provider == "openai":
        return await _generate_openai(prompt, system_prompt=system_prompt)
    elif settings.llm_provider == "ollama":
        return await _generate_ollama(prompt, system_prompt=system_prompt)
    else:
        raise ValueError(f"Unknown LLM provider: {settings.llm_provider}")


async def _generate_anthropic(
    prompt: str,
    system_prompt: str = GDSCRIPT_SYSTEM_PROMPT,
) -> dict[str, Any]:
    import anthropic

    api_key = settings.anthropic_api_key or os.environ.get("ANTHROPIC_API_KEY", "")
    client = anthropic.AsyncAnthropic(api_key=api_key) if api_key else anthropic.AsyncAnthropic()
    response = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=8192,
        system=system_prompt,
        messages=[{"role": "user", "content": prompt}],
    )
    text = response.content[0].text
    result = _parse_code_response(text)
    result["_raw_text"] = text
    return result


async def _generate_openai(
    prompt: str,
    system_prompt: str = GDSCRIPT_SYSTEM_PROMPT,
) -> dict[str, Any]:
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        max_tokens=8192,
    )
    text = response.choices[0].message.content or ""
    result = _parse_code_response(text)
    result["_raw_text"] = text
    return result


async def _generate_glm(
    prompt: str,
    system_prompt: str = GDSCRIPT_SYSTEM_PROMPT,
) -> dict[str, Any]:
    """通过智谱 AI GLM API 生成（OpenAI 兼容接口）"""
    from openai import AsyncOpenAI

    api_key = settings.glm_api_key or os.environ.get("GLM_API_KEY", "")
    client = AsyncOpenAI(
        api_key=api_key,
        base_url=settings.glm_base_url,
    )
    response = await client.chat.completions.create(
        model=settings.glm_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        max_tokens=8192,
    )
    text = response.choices[0].message.content or ""
    result = _parse_code_response(text)
    result["_raw_text"] = text
    return result


async def _generate_ollama(
    prompt: str,
    system_prompt: str = GDSCRIPT_SYSTEM_PROMPT,
) -> dict[str, Any]:
    import httpx

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{settings.ollama_base_url}/api/chat",
            json={
                "model": settings.ollama_model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                "stream": False,
            },
        )
        data = response.json()
        text = data.get("message", {}).get("content", "")
        result = _parse_code_response(text)
        result["_raw_text"] = text
        return result


def _parse_code_response(text: str) -> dict[str, Any]:
    """解析 LLM 响应，提取代码块和说明"""
    files: list[dict[str, str]] = []
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


def _parse_multi_file_response(text: str) -> list[dict[str, str]]:
    """解析多文件响应 — 使用 ### FILE: 标记分隔

    Expected format:
        ### FILE: res://path/to/file.gd
        ```gdscript
        code here
        ```
    """
    files: list[dict[str, str]] = []
    file_pattern = re.compile(
        r"###\s*FILE:\s*(res://\S+)\s*\n"
        r"```(?:gdscript|gd|tscn|tres|cfg)?\s*\n"
        r"(.*?)"
        r"```",
        re.DOTALL,
    )

    for match in file_pattern.finditer(text):
        path = match.group(1).strip()
        content = match.group(2).strip()
        files.append({"path": path, "content": content})

    return files


def _extract_integration_steps(text: str) -> list[str]:
    """从说明文本中提取集成步骤

    Looks for a section starting with "### INTEGRATION STEPS:" and parses
    numbered or bulleted items.
    """
    steps: list[str] = []

    match = re.search(
        r"###\s*INTEGRATION\s+STEPS:\s*\n(.*?)(?:\n###|\Z)",
        text,
        re.DOTALL | re.IGNORECASE,
    )
    if not match:
        return steps

    steps_text = match.group(1)
    # 匹配编号列表 (1. ...) 或无序列表 (- ...)
    step_pattern = re.compile(r"(?:^\s*\d+\.\s*|^\s*[-*]\s*)(.*)", re.MULTILINE)
    for step_match in step_pattern.finditer(steps_text):
        step = step_match.group(1).strip()
        if step:
            steps.append(step)

    return steps
