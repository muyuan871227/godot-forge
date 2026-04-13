"""音频生成路由 — SFX / BGM / TTS"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..services.audio_service import (
    generate_background_music,
    generate_sound_effect,
    generate_speech,
)

router = APIRouter()


class SFXRequest(BaseModel):
    description: str = Field(..., description="音效描述 (例如 sword clash, explosion)")
    duration_seconds: float = Field(default=3.0, ge=0.5, le=30.0, description="时长（秒）")
    sample_rate: int = Field(default=24000, description="采样率")


class BGMRequest(BaseModel):
    description: str = Field(
        ..., description="音乐描述 (例如 upbeat chiptune battle theme)"
    )
    duration_seconds: float = Field(default=30.0, ge=5.0, le=300.0, description="时长（秒）")
    sample_rate: int = Field(default=32000, description="采样率")


class TTSRequest(BaseModel):
    text: str = Field(..., description="要转换为语音的文本")
    voice_preset: str | None = Field(
        default=None,
        description="Bark 语音预设 (例如 v2/en_speaker_6)",
    )
    sample_rate: int = Field(default=24000, description="采样率")


class AudioResponse(BaseModel):
    audio_base64: str
    format: str
    sample_rate: int
    duration_seconds: float


class TTSResponse(AudioResponse):
    text: str


@router.post("/sfx", response_model=AudioResponse)
async def api_generate_sfx(req: SFXRequest):
    """生成游戏音效"""
    try:
        result = await generate_sound_effect(
            description=req.description,
            duration_seconds=req.duration_seconds,
            sample_rate=req.sample_rate,
        )
        if result.get("status") == "not_available":
            raise HTTPException(status_code=503, detail=result.get("message", ""))

        return AudioResponse(
            audio_base64=result["audio_base64"],
            format=result["format"],
            sample_rate=result["sample_rate"],
            duration_seconds=result["duration_seconds"],
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/bgm", response_model=AudioResponse)
async def api_generate_bgm(req: BGMRequest):
    """生成背景音乐"""
    try:
        result = await generate_background_music(
            description=req.description,
            duration_seconds=req.duration_seconds,
            sample_rate=req.sample_rate,
        )
        if result.get("status") == "not_available":
            raise HTTPException(status_code=503, detail=result.get("message", ""))

        return AudioResponse(
            audio_base64=result["audio_base64"],
            format=result["format"],
            sample_rate=result["sample_rate"],
            duration_seconds=result["duration_seconds"],
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/tts", response_model=TTSResponse)
async def api_generate_tts(req: TTSRequest):
    """生成 NPC 对话语音 (TTS)"""
    try:
        result = await generate_speech(
            text=req.text,
            voice_preset=req.voice_preset,
            sample_rate=req.sample_rate,
        )
        if result.get("status") == "not_available":
            raise HTTPException(status_code=503, detail=result.get("message", ""))

        return TTSResponse(
            audio_base64=result["audio_base64"],
            format=result["format"],
            sample_rate=result["sample_rate"],
            duration_seconds=result["duration_seconds"],
            text=result.get("text", req.text),
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
