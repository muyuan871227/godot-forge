"""音频生成服务 — Bark (SFX/TTS) + MusicGen (BGM)"""
import base64
import io
from typing import Any

from ..config import settings


async def generate_sound_effect(
    description: str,
    duration_seconds: float = 3.0,
    sample_rate: int = 24000,
) -> dict[str, Any]:
    """使用 Bark 生成游戏音效

    Args:
        description: 音效描述 (例如 "sword clash", "explosion", "coin pickup")
        duration_seconds: 目标时长（秒）
        sample_rate: 采样率

    Returns:
        dict with keys: audio_base64, format, sample_rate, duration_seconds
    """
    # Bark 使用文本提示词生成音频
    # 添加音效提示标记以引导生成方向
    sfx_prompt = f"[SFX] {description}"

    try:
        from bark import SAMPLE_RATE, generate_audio, preload_models

        preload_models()
        audio_array = generate_audio(sfx_prompt)

        # 截取到目标时长
        target_samples = int(duration_seconds * SAMPLE_RATE)
        if len(audio_array) > target_samples:
            audio_array = audio_array[:target_samples]

        audio_base64 = _numpy_to_wav_base64(audio_array, SAMPLE_RATE)

        return {
            "audio_base64": audio_base64,
            "format": "wav",
            "sample_rate": SAMPLE_RATE,
            "duration_seconds": len(audio_array) / SAMPLE_RATE,
        }
    except ImportError:
        return _bark_not_available_response("sound_effect", description)


async def generate_background_music(
    description: str,
    duration_seconds: float = 30.0,
    sample_rate: int = 32000,
) -> dict[str, Any]:
    """使用 MusicGen 生成背景音乐

    Args:
        description: 音乐描述 (例如 "upbeat chiptune battle theme", "calm forest ambience")
        duration_seconds: 目标时长（秒）
        sample_rate: 采样率

    Returns:
        dict with keys: audio_base64, format, sample_rate, duration_seconds
    """
    try:
        from audiocraft.models import MusicGen

        model = MusicGen.get_pretrained("facebook/musicgen-small")
        model.set_generation_params(duration=duration_seconds)

        # MusicGen 接受文本描述列表
        wav = model.generate([description])
        audio_array = wav[0].cpu().numpy().squeeze()

        actual_sr = model.sample_rate
        audio_base64 = _numpy_to_wav_base64(audio_array, actual_sr)

        return {
            "audio_base64": audio_base64,
            "format": "wav",
            "sample_rate": actual_sr,
            "duration_seconds": len(audio_array) / actual_sr,
        }
    except ImportError:
        return {
            "audio_base64": "",
            "format": "wav",
            "sample_rate": sample_rate,
            "duration_seconds": 0.0,
            "status": "not_available",
            "message": (
                "MusicGen (audiocraft) is not installed. "
                "Install with: pip install audiocraft"
            ),
            "description": description,
        }


async def generate_speech(
    text: str,
    voice_preset: str | None = None,
    sample_rate: int = 24000,
) -> dict[str, Any]:
    """使用 Bark TTS 生成 NPC 对话语音

    Args:
        text: 要转换为语音的文本
        voice_preset: Bark 语音预设 (例如 "v2/en_speaker_6")
        sample_rate: 采样率

    Returns:
        dict with keys: audio_base64, format, sample_rate, duration_seconds, text
    """
    try:
        from bark import SAMPLE_RATE, generate_audio, preload_models

        preload_models()
        audio_array = generate_audio(
            text,
            history_prompt=voice_preset,
        )

        audio_base64 = _numpy_to_wav_base64(audio_array, SAMPLE_RATE)

        return {
            "audio_base64": audio_base64,
            "format": "wav",
            "sample_rate": SAMPLE_RATE,
            "duration_seconds": len(audio_array) / SAMPLE_RATE,
            "text": text,
        }
    except ImportError:
        return _bark_not_available_response("speech", text)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _numpy_to_wav_base64(audio_array: Any, sample_rate: int) -> str:
    """将 numpy 音频数组转换为 base64 编码的 WAV"""
    import numpy as np
    from scipy.io import wavfile

    # 确保是 float32 范围 [-1, 1] 然后转 int16
    audio_np = np.array(audio_array, dtype=np.float32)
    audio_np = np.clip(audio_np, -1.0, 1.0)
    audio_int16 = (audio_np * 32767).astype(np.int16)

    buffer = io.BytesIO()
    wavfile.write(buffer, sample_rate, audio_int16)
    buffer.seek(0)
    return base64.b64encode(buffer.read()).decode("utf-8")


def _bark_not_available_response(
    generation_type: str,
    description: str,
) -> dict[str, Any]:
    """Bark 未安装时的占位响应"""
    return {
        "audio_base64": "",
        "format": "wav",
        "sample_rate": 24000,
        "duration_seconds": 0.0,
        "status": "not_available",
        "message": (
            "Bark is not installed. "
            "Install with: pip install git+https://github.com/suno-ai/bark.git"
        ),
        "type": generation_type,
        "description": description,
    }
