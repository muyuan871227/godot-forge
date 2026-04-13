"""NPC AI 路由 — 对话生成与行为树生成"""
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..services.llm_service import generate_gdscript

router = APIRouter()


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class DialogueRequest(BaseModel):
    npc_name: str = Field(..., description="NPC 名称")
    npc_personality: str = Field(
        default="friendly", description="NPC 性格描述 (例如 friendly, grumpy, mysterious)"
    )
    npc_background: str = Field(default="", description="NPC 背景故事")
    player_message: str = Field(..., description="玩家对 NPC 说的话")
    conversation_history: list[dict[str, str]] = Field(
        default_factory=list,
        description="对话历史 [{role: 'player'|'npc', content: '...'}]",
    )
    game_context: str = Field(default="", description="当前游戏状态上下文")
    max_tokens: int = Field(default=256, ge=32, le=1024, description="最大回复长度")


class DialogueResponse(BaseModel):
    npc_reply: str
    emotion: str
    suggested_actions: list[str]


class BehaviorRequest(BaseModel):
    npc_type: str = Field(
        ..., description="NPC 类型 (例如 enemy, shopkeeper, quest_giver, companion)"
    )
    behavior_description: str = Field(
        ..., description="期望的行为描述 (例如 patrol between waypoints and chase player on sight)"
    )
    npc_stats: dict[str, Any] = Field(
        default_factory=dict,
        description="NPC 属性 (例如 {health: 100, speed: 50, attack: 10})",
    )
    godot_version: str = Field(default="4.4", description="Godot 版本")


class BehaviorResponse(BaseModel):
    code: str
    explanation: str
    files: list[dict[str, str]]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/dialogue", response_model=DialogueResponse)
async def api_generate_dialogue(req: DialogueRequest):
    """生成 NPC 对话回复"""
    # 构建角色系统提示
    system_context = (
        f"You are {req.npc_name}, an NPC in a video game.\n"
        f"Personality: {req.npc_personality}\n"
    )
    if req.npc_background:
        system_context += f"Background: {req.npc_background}\n"
    if req.game_context:
        system_context += f"Current game state: {req.game_context}\n"

    system_context += (
        "\nRespond in character. Keep responses concise and game-appropriate.\n"
        "After your reply, on a new line write EMOTION: <emotion> "
        "(one of: neutral, happy, angry, sad, surprised, scared, suspicious)\n"
        "Then on a new line write ACTIONS: <comma-separated suggested actions>\n"
        "(Examples: give_quest, open_shop, attack, flee, hint)"
    )

    # 构建对话历史
    prompt_parts: list[str] = []
    for entry in req.conversation_history:
        role = entry.get("role", "player")
        content = entry.get("content", "")
        label = "Player" if role == "player" else req.npc_name
        prompt_parts.append(f"{label}: {content}")

    prompt_parts.append(f"Player: {req.player_message}")
    prompt_parts.append(f"{req.npc_name}:")

    full_prompt = "\n".join(prompt_parts)

    try:
        result = await generate_gdscript(prompt=full_prompt, context=system_context)
        raw_text = result.get("explanation", "") or result.get("code", "")

        # 解析响应
        npc_reply, emotion, actions = _parse_dialogue_response(raw_text, req.npc_name)

        return DialogueResponse(
            npc_reply=npc_reply,
            emotion=emotion,
            suggested_actions=actions,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/behavior", response_model=BehaviorResponse)
async def api_generate_behavior(req: BehaviorRequest):
    """生成 NPC 行为树 GDScript 代码"""
    stats_desc = ""
    if req.npc_stats:
        stats_desc = "NPC stats:\n"
        for key, val in req.npc_stats.items():
            stats_desc += f"  - {key}: {val}\n"

    prompt = (
        f"Generate a complete behavior tree implementation in GDScript for a "
        f"{req.npc_type} NPC in Godot {req.godot_version}.\n\n"
        f"Desired behavior: {req.behavior_description}\n\n"
        f"{stats_desc}\n"
        "Requirements:\n"
        "- Use a state machine or behavior tree pattern\n"
        "- Include states/nodes for: idle, patrol, chase, attack, flee as appropriate\n"
        "- Use NavigationAgent2D or NavigationAgent3D for pathfinding\n"
        "- Include @export variables for tunable parameters\n"
        "- Add signal emissions for state changes\n"
        "- Include clear comments explaining each state transition"
    )

    try:
        result = await generate_gdscript(
            prompt=prompt,
            godot_version=req.godot_version,
        )
        return BehaviorResponse(
            code=result.get("code", ""),
            explanation=result.get("explanation", ""),
            files=result.get("files", []),
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _parse_dialogue_response(
    text: str,
    npc_name: str,
) -> tuple[str, str, list[str]]:
    """解析 NPC 对话响应，提取回复、情绪和建议动作"""
    lines = text.strip().split("\n")
    reply_lines: list[str] = []
    emotion = "neutral"
    actions: list[str] = []

    for line in lines:
        stripped = line.strip()
        if stripped.upper().startswith("EMOTION:"):
            emotion = stripped.split(":", 1)[1].strip().lower()
        elif stripped.upper().startswith("ACTIONS:"):
            raw_actions = stripped.split(":", 1)[1].strip()
            actions = [a.strip() for a in raw_actions.split(",") if a.strip()]
        else:
            # 移除可能的 NPC 名称前缀
            if stripped.startswith(f"{npc_name}:"):
                stripped = stripped[len(npc_name) + 1 :].strip()
            reply_lines.append(stripped)

    npc_reply = "\n".join(reply_lines).strip()
    if not npc_reply:
        npc_reply = "..."

    return npc_reply, emotion, actions
