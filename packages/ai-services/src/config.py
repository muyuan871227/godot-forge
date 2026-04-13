"""配置管理 — 所有 AI 供应商通过环境变量配置"""
import os

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    port: int = 8100

    # LLM
    llm_provider: str = "anthropic"  # anthropic | openai | glm | ollama
    anthropic_api_key: str = os.environ.get("ANTHROPIC_API_KEY", "")
    openai_api_key: str = os.environ.get("OPENAI_API_KEY", "")
    glm_api_key: str = os.environ.get("GLM_API_KEY", "")
    glm_base_url: str = "https://open.bigmodel.cn/api/paas/v4/"
    glm_model: str = "glm-4-flash"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "deepseek-coder-v2:16b"

    # 图像生成
    image_provider: str = "comfyui"  # comfyui | replicate | local
    comfyui_url: str = "http://localhost:8188"

    # 3D 模型
    model3d_provider: str = "hunyuan3d"  # hunyuan3d | triposr | meshy_api
    hunyuan3d_path: str = ""
    meshy_api_key: str = ""

    # 音频
    audio_provider: str = "bark"  # bark | musicgen | elevenlabs
    bark_model_path: str = ""

    # Godot
    godot_path: str = "godot"

    model_config = {
        "env_file": "../../.env",
        "env_prefix": "GODOTFORGE_",
        "extra": "ignore",
    }


settings = Settings()
