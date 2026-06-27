"""精灵图生成管线 — 从角色描述生成动画精灵图表

完整流程:
1. 为每个动画阶段生成带上下文的 prompt
2. 调用图像生成服务逐帧生成
3. 将所有帧合并为单张精灵图表
4. 生成 Godot SpriteFrames .tres 资源文件
"""
import base64
import io
import json
import logging
import uuid
from pathlib import Path
from typing import Any

from ..config import settings
from ..services.image_service import generate_image

logger = logging.getLogger(__name__)

SPRITE_OUTPUT_DIR = Path("/tmp/godotforge/sprites")
SPRITE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


class SpriteSheetPipeline:
    """精灵图生成管线

    从角色描述和动画规格生成完整的精灵图表及 Godot 资源。
    """

    async def generate(
        self,
        character_desc: str,
        animations: dict[str, int],
        style: str = "pixel_art",
        frame_size: tuple[int, int] = (64, 64),
    ) -> dict[str, Any]:
        """生成完整的精灵图表及 Godot 资源

        Args:
            character_desc: 角色外观描述 (例如 "a knight in silver armor with a red cape")
            animations: 动画名称到帧数的映射 (例如 {"idle": 4, "run": 6, "attack": 4})
            style: 图像风格预设 (pixel_art, hand_drawn, anime, realistic)
            frame_size: 单帧尺寸 (width, height)

        Returns:
            dict with keys:
                - sheet_path: 合并后精灵图表路径
                - sheet_base64: 精灵图表 base64
                - tres_path: Godot .tres 资源路径
                - tres_content: .tres 文件内容
                - frame_size: (width, height)
                - animations: {name: frame_count}
                - total_frames: 总帧数
        """
        session_id = uuid.uuid4().hex[:8]
        session_dir = SPRITE_OUTPUT_DIR / session_id
        session_dir.mkdir(parents=True, exist_ok=True)

        frame_w, frame_h = frame_size
        total_frames = sum(animations.values())

        logger.info(
            "Generating sprite sheet: %s (%d animations, %d total frames, %dx%d)",
            character_desc[:50],
            len(animations),
            total_frames,
            frame_w,
            frame_h,
        )

        # Step 1 & 2: 逐动画逐帧生成图像
        all_frames: list[bytes] = []
        frame_index = 0

        for anim_name, frame_count in animations.items():
            logger.info("Generating %d frames for animation '%s'", frame_count, anim_name)

            for i in range(frame_count):
                prompt = self._get_animation_prompt(
                    character_desc=character_desc,
                    animation_name=anim_name,
                    frame_index=i,
                    total_frames=frame_count,
                )

                result = await generate_image(
                    prompt=prompt,
                    style=style,
                    width=frame_w,
                    height=frame_h,
                    transparent_bg=True,
                )

                image_bytes = base64.b64decode(result["image_base64"])
                all_frames.append(image_bytes)

                # 保存单帧用于调试
                frame_path = session_dir / f"frame_{frame_index:04d}_{anim_name}_{i}.png"
                frame_path.write_bytes(image_bytes)
                frame_index += 1

        # Step 3: 合并为精灵图表
        sheet_bytes = self._combine_to_sheet(
            frames=all_frames,
            frame_width=frame_w,
            frame_height=frame_h,
        )

        sheet_path = session_dir / "spritesheet.png"
        sheet_path.write_bytes(sheet_bytes)
        sheet_base64 = base64.b64encode(sheet_bytes).decode("utf-8")

        # Step 4: 生成 Godot .tres 资源
        tres_content = self._generate_sprite_frames_tres(
            sheet_filename="spritesheet.png",
            animations=animations,
            frame_width=frame_w,
            frame_height=frame_h,
        )

        tres_path = session_dir / "sprite_frames.tres"
        tres_path.write_text(tres_content, encoding="utf-8")

        logger.info("Sprite sheet generated: %s (%d frames)", sheet_path, total_frames)

        return {
            "sheet_path": str(sheet_path),
            "sheet_base64": sheet_base64,
            "tres_path": str(tres_path),
            "tres_content": tres_content,
            "frame_size": frame_size,
            "animations": animations,
            "total_frames": total_frames,
            "session_dir": str(session_dir),
        }

    def _get_animation_prompt(
        self,
        character_desc: str,
        animation_name: str,
        frame_index: int,
        total_frames: int,
    ) -> str:
        """为特定动画阶段生成上下文感知的提示词

        根据动画类型和帧位置，生成描述角色当前姿态的精确提示词。

        Args:
            character_desc: 角色外观描述
            animation_name: 动画名称 (idle, run, attack, jump, etc.)
            frame_index: 当前帧索引 (0-based)
            total_frames: 该动画总帧数

        Returns:
            增强的生成提示词
        """
        # 计算动画进度 (0.0 - 1.0)
        progress = frame_index / max(total_frames - 1, 1)

        # 根据动画类型定义姿态描述
        animation_phases: dict[str, list[str]] = {
            "idle": [
                "standing relaxed, slight breathing motion",
                "standing with subtle weight shift",
                "standing relaxed, arms at sides",
                "standing with gentle idle movement",
            ],
            "run": [
                "starting to run, right foot forward",
                "mid-stride running, arms swinging",
                "full stride running, left foot forward",
                "pushing off ground, dynamic running pose",
                "legs crossing mid-run",
                "completing stride cycle, right foot landing",
            ],
            "walk": [
                "stepping forward with right foot",
                "mid-step, weight transferring",
                "stepping forward with left foot",
                "completing step, weight on left foot",
            ],
            "attack": [
                "winding up attack, pulling arm back",
                "mid-swing, weapon extended",
                "attack at full extension, impact moment",
                "follow-through after attack",
            ],
            "jump": [
                "crouching before jump, knees bent",
                "launching upward, legs extending",
                "at peak of jump, arms up",
                "descending, preparing to land",
                "landing, knees absorbing impact",
            ],
            "death": [
                "hit reaction, leaning back",
                "falling backward",
                "hitting ground",
                "lying on ground, defeated",
            ],
            "cast": [
                "raising hands, gathering energy",
                "channeling spell, glowing effects",
                "releasing spell, arms extended",
                "spell cast complete, lowering arms",
            ],
            "hurt": [
                "recoiling from hit",
                "staggering back, pain expression",
                "recovering from hit",
            ],
        }

        # 获取动画阶段描述
        phases = animation_phases.get(
            animation_name.lower(),
            [f"performing {animation_name} action, frame {frame_index + 1} of {total_frames}"],
        )

        # 选择与当前进度最接近的阶段描述
        phase_index = min(int(progress * len(phases)), len(phases) - 1)
        phase_desc = phases[phase_index]

        return (
            f"{character_desc}, {phase_desc}, "
            f"game character sprite, single character, centered, "
            f"transparent background, consistent design, "
            f"frame {frame_index + 1} of {total_frames} in {animation_name} animation"
        )

    def _combine_to_sheet(
        self,
        frames: list[bytes],
        frame_width: int,
        frame_height: int,
    ) -> bytes:
        """将多帧图像合并为单张精灵图表

        帧按行排列，每行最多 columns_per_row 帧。

        Args:
            frames: 各帧的 PNG 图像字节数据
            frame_width: 单帧宽度
            frame_height: 单帧高度

        Returns:
            合并后精灵图表的 PNG 字节数据
        """
        from PIL import Image

        num_frames = len(frames)
        if num_frames == 0:
            # 返回空白单帧
            blank = Image.new("RGBA", (frame_width, frame_height), (0, 0, 0, 0))
            buffer = io.BytesIO()
            blank.save(buffer, format="PNG")
            return buffer.getvalue()

        # 每行放置的帧数 — 尽量让图表接近正方形
        columns_per_row = min(num_frames, max(1, int(num_frames**0.5) + 1))
        if num_frames <= 8:
            columns_per_row = num_frames  # 少量帧排成一行

        rows = (num_frames + columns_per_row - 1) // columns_per_row

        sheet_width = frame_width * columns_per_row
        sheet_height = frame_height * rows

        sheet = Image.new("RGBA", (sheet_width, sheet_height), (0, 0, 0, 0))

        for idx, frame_bytes in enumerate(frames):
            frame_image = Image.open(io.BytesIO(frame_bytes)).convert("RGBA")
            # 确保帧尺寸正确
            if frame_image.size != (frame_width, frame_height):
                frame_image = frame_image.resize(
                    (frame_width, frame_height),
                    Image.Resampling.LANCZOS,
                )

            col = idx % columns_per_row
            row = idx // columns_per_row
            x = col * frame_width
            y = row * frame_height

            sheet.paste(frame_image, (x, y))

        buffer = io.BytesIO()
        sheet.save(buffer, format="PNG")
        return buffer.getvalue()

    def _generate_sprite_frames_tres(
        self,
        sheet_filename: str,
        animations: dict[str, int],
        frame_width: int,
        frame_height: int,
    ) -> str:
        """生成 Godot SpriteFrames .tres 资源文件

        Args:
            sheet_filename: 精灵图表文件名
            animations: 动画名称到帧数的映射
            frame_width: 单帧宽度
            frame_height: 单帧高度

        Returns:
            .tres 文件内容字符串
        """
        total_frames = sum(animations.values())

        # 计算精灵图表布局
        columns_per_row = total_frames if total_frames <= 8 else min(
            total_frames, max(1, int(total_frames**0.5) + 1)
        )

        # 收集所有 AtlasTexture 子资源
        atlas_resources: list[str] = []
        animation_sections: list[str] = []

        resource_id = 1
        frame_global_index = 0

        for anim_name, frame_count in animations.items():
            frame_refs: list[str] = []

            for i in range(frame_count):
                col = frame_global_index % columns_per_row
                row = frame_global_index // columns_per_row
                x = col * frame_width
                y = row * frame_height

                atlas_resources.append(
                    f'[sub_resource type="AtlasTexture" id="AtlasTexture_{resource_id}"]\n'
                    f'atlas = ExtResource("1_sheet")\n'
                    f"region = Rect2({x}, {y}, {frame_width}, {frame_height})"
                )

                frame_refs.append(
                    f'{{"duration": 1.0, "texture": SubResource("AtlasTexture_{resource_id}")}}'
                )

                resource_id += 1
                frame_global_index += 1

            # 默认动画速度
            fps = 8.0
            if anim_name.lower() in ("run", "attack"):
                fps = 12.0
            elif anim_name.lower() in ("idle",):
                fps = 6.0

            loop = "true" if anim_name.lower() in ("idle", "run", "walk") else "false"

            frames_str = ", ".join(frame_refs)
            animation_sections.append(
                f'{{"frames": [{frames_str}], '
                f'"loop": {loop}, '
                f'"name": &"{anim_name}", '
                f'"speed": {fps}}}'
            )

        # 组装 .tres 文件
        atlas_block = "\n\n".join(atlas_resources)
        animations_block = ", ".join(animation_sections)

        tres_content = (
            f'[gd_resource type="SpriteFrames" load_steps={resource_id} format=3]\n\n'
            f'[ext_resource type="Texture2D" '
            f'path="res://assets/sprites/{sheet_filename}" '
            f'id="1_sheet"]\n\n'
            f"{atlas_block}\n\n"
            f"[resource]\n"
            f"animations = [{animations_block}]"
        )

        return tres_content


# ---------------------------------------------------------------------------
# 单例
# ---------------------------------------------------------------------------

sprite_sheet_pipeline = SpriteSheetPipeline()
