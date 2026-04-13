"""文字到游戏主管线 — 从一段自然语言描述生成完整的可运行 Godot 项目

完整流程:
1. LLM 生成游戏设计文档 (GDD)
2. 规划项目结构（场景、脚本、资产清单）
3. 生成全部 GDScript 代码
4. 生成精灵图、音频等资产
5. 组装为完整的 Godot 项目目录
6. 运行视觉 QA 检查
"""
import json
import logging
import uuid
from pathlib import Path
from typing import Any

from ..config import settings
from ..services.image_service import generate_image
from ..services.llm_service import _call_llm, generate_gdscript
from .visual_qa import visual_qa_pipeline

logger = logging.getLogger(__name__)

GAME_OUTPUT_DIR = Path("/tmp/godotforge/games")
GAME_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Godot 4 项目模板
PROJECT_GODOT_TEMPLATE = """; Engine configuration file.
; It's best edited using the editor UI and not directly,
; but it can also be manually edited.

config_version=5

[application]

config/name="{project_name}"
run/main_scene="res://scenes/main.tscn"
config/features=PackedStringArray("4.4")

[display]

window/size/viewport_width={viewport_width}
window/size/viewport_height={viewport_height}

[rendering]

renderer/rendering_method="{renderer}"
"""


class GameFromTextPipeline:
    """文字到游戏主管线

    接受一段自然语言游戏描述，输出完整的可运行 Godot 4 项目。
    """

    async def generate(
        self,
        game_description: str,
    ) -> dict[str, Any]:
        """从文字描述生成完整游戏项目

        Args:
            game_description: 自然语言游戏描述
                例如 "一个 2D 平台跳跃游戏，玩家控制一只蓝色小猫，在森林中收集星星。
                有 3 种敌人：走路的蘑菇、飞行的蝙蝠、固定的仙人掌。
                玩家有 3 条生命，收集 10 颗星星过关。"

        Returns:
            dict with keys:
                - project_path: str — 生成的项目目录路径
                - design_doc: dict — 游戏设计文档
                - files_created: list[str] — 创建的文件列表
                - qa_passed: bool — 是否通过视觉 QA
                - qa_result: dict — QA 详细结果
        """
        session_id = uuid.uuid4().hex[:8]
        project_name = f"godotforge_game_{session_id}"
        project_dir = GAME_OUTPUT_DIR / project_name

        logger.info(
            "Starting game generation from text: session=%s, desc=%s...",
            session_id,
            game_description[:80],
        )

        files_created: list[str] = []

        # Step 1: 生成游戏设计文档
        logger.info("Step 1/6: Generating design document...")
        design_doc = await self._generate_design_doc(game_description)

        # Step 2: 规划项目结构
        logger.info("Step 2/6: Planning project structure...")
        project_plan = await self._plan_project_structure(design_doc)

        # Step 3: 生成所有代码
        logger.info("Step 3/6: Generating all code...")
        code_files = await self._generate_all_code(design_doc, project_plan)

        # Step 4: 生成资产
        logger.info("Step 4/6: Generating assets...")
        asset_files = await self._generate_all_assets(design_doc, project_plan)

        # Step 5: 组装项目
        logger.info("Step 5/6: Assembling project...")
        files_created = await self._assemble_project(
            project_dir=project_dir,
            project_name=project_name,
            design_doc=design_doc,
            project_plan=project_plan,
            code_files=code_files,
            asset_files=asset_files,
        )

        # Step 6: 运行 QA
        logger.info("Step 6/6: Running visual QA...")
        qa_result = await self._run_qa(
            project_path=str(project_dir),
            design_doc=design_doc,
        )

        logger.info(
            "Game generation complete: %s (%d files, QA passed=%s)",
            project_dir,
            len(files_created),
            qa_result.get("passed", False),
        )

        return {
            "project_path": str(project_dir),
            "design_doc": design_doc,
            "files_created": files_created,
            "qa_passed": qa_result.get("passed", False),
            "qa_result": qa_result,
        }

    async def _generate_design_doc(
        self,
        game_description: str,
    ) -> dict[str, Any]:
        """使用 LLM 生成游戏设计文档

        Args:
            game_description: 用户的游戏描述

        Returns:
            游戏设计文档 dict，包含:
                - title: 游戏标题
                - genre: 游戏类型
                - description: 详细描述
                - game_type: 2d/3d
                - viewport: {width, height}
                - player: {name, description, abilities}
                - enemies: [{name, description, behavior}]
                - levels: [{name, description, objectives}]
                - mechanics: [str]
                - assets_needed: {sprites: [], audio: [], ui: []}
                - win_condition: str
                - lose_condition: str
        """
        system_prompt = (
            "You are a game designer creating a Game Design Document (GDD) for a Godot 4 game. "
            "Return ONLY a valid JSON object, no explanation, no markdown code fences."
        )

        prompt = (
            f"Create a detailed Game Design Document from this description:\n\n"
            f"{game_description}\n\n"
            "Return a JSON object with these keys:\n"
            "{\n"
            '  "title": "Game Title",\n'
            '  "genre": "platformer|rpg|puzzle|shooter|etc",\n'
            '  "description": "Detailed game description",\n'
            '  "game_type": "2d",\n'
            '  "viewport": {"width": 1280, "height": 720},\n'
            '  "renderer": "gl_compatibility",\n'
            '  "player": {\n'
            '    "name": "Player Name",\n'
            '    "description": "Visual description for sprite generation",\n'
            '    "abilities": ["move", "jump", "attack"],\n'
            '    "stats": {"health": 3, "speed": 200}\n'
            "  },\n"
            '  "enemies": [\n'
            '    {"name": "Enemy1", "description": "Visual description", '
            '"behavior": "patrol|chase|stationary", "stats": {"health": 1, "damage": 1}}\n'
            "  ],\n"
            '  "levels": [\n'
            '    {"name": "Level 1", "description": "Level theme/layout", '
            '"objectives": ["Collect 10 stars"]}\n'
            "  ],\n"
            '  "mechanics": ["jumping", "collecting", "combat"],\n'
            '  "assets_needed": {\n'
            '    "sprites": ["player_character", "enemy_mushroom"],\n'
            '    "audio": ["jump_sfx", "bgm_forest"],\n'
            '    "ui": ["health_bar", "score_display"]\n'
            "  },\n"
            '  "win_condition": "Collect all stars",\n'
            '  "lose_condition": "Lose all lives"\n'
            "}"
        )

        result = await _call_llm(prompt, system_prompt=system_prompt)
        raw_text = result.get("_raw_text", "") or result.get("explanation", "")

        return self._parse_design_doc(raw_text, game_description)

    def _parse_design_doc(
        self,
        raw_text: str,
        fallback_description: str,
    ) -> dict[str, Any]:
        """解析 LLM 返回的游戏设计文档 JSON"""
        import re

        text = raw_text.strip()
        text = re.sub(r"```(?:json)?\s*\n?", "", text).strip()

        try:
            json_match = re.search(r"\{.*\}", text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))
        except (json.JSONDecodeError, ValueError):
            pass

        # 解析失败 — 返回最小可用的设计文档
        logger.warning("Failed to parse design doc JSON, using minimal fallback")
        return {
            "title": "Generated Game",
            "genre": "platformer",
            "description": fallback_description,
            "game_type": "2d",
            "viewport": {"width": 1280, "height": 720},
            "renderer": "gl_compatibility",
            "player": {
                "name": "Player",
                "description": "A game character",
                "abilities": ["move", "jump"],
                "stats": {"health": 3, "speed": 200},
            },
            "enemies": [],
            "levels": [
                {"name": "Level 1", "description": "Main level", "objectives": ["Complete the level"]}
            ],
            "mechanics": ["movement", "jumping"],
            "assets_needed": {"sprites": ["player"], "audio": [], "ui": ["score"]},
            "win_condition": "Complete the level",
            "lose_condition": "Lose all lives",
        }

    async def _plan_project_structure(
        self,
        design_doc: dict[str, Any],
    ) -> dict[str, Any]:
        """规划 Godot 项目结构

        Args:
            design_doc: 游戏设计文档

        Returns:
            项目规划 dict:
                - scenes: [{path, type, description}]
                - scripts: [{path, attached_to, description}]
                - assets: [{path, type, description}]
                - autoloads: [{name, path}]
                - input_actions: [{name, keys}]
        """
        system_prompt = (
            "You are a Godot 4 project architect. "
            "Plan the file structure for a game project. "
            "Return ONLY a valid JSON object, no explanation, no markdown code fences."
        )

        design_summary = json.dumps(design_doc, indent=2, ensure_ascii=False)

        prompt = (
            f"Plan the Godot 4 project structure for this game:\n\n{design_summary}\n\n"
            "Return a JSON object with:\n"
            "{\n"
            '  "scenes": [\n'
            '    {"path": "res://scenes/main.tscn", "root_type": "Node2D", "description": "Main scene"}\n'
            "  ],\n"
            '  "scripts": [\n'
            '    {"path": "res://scripts/player.gd", "extends": "CharacterBody2D", '
            '"attached_to": "res://scenes/main.tscn::Player", "description": "Player controller"}\n'
            "  ],\n"
            '  "assets": [\n'
            '    {"path": "res://assets/sprites/player.png", "type": "sprite", "description": "Player sprite"}\n'
            "  ],\n"
            '  "autoloads": [\n'
            '    {"name": "GameManager", "path": "res://scripts/autoload/game_manager.gd"}\n'
            "  ],\n"
            '  "input_actions": [\n'
            '    {"name": "move_left", "keys": ["A", "Left"]},\n'
            '    {"name": "move_right", "keys": ["D", "Right"]},\n'
            '    {"name": "jump", "keys": ["Space", "W", "Up"]}\n'
            "  ]\n"
            "}\n"
            "Include at least: main scene, player scene/script, one level, a game manager autoload."
        )

        result = await _call_llm(prompt, system_prompt=system_prompt)
        raw_text = result.get("_raw_text", "") or result.get("explanation", "")

        return self._parse_project_plan(raw_text, design_doc)

    def _parse_project_plan(
        self,
        raw_text: str,
        design_doc: dict[str, Any],
    ) -> dict[str, Any]:
        """解析项目结构规划 JSON"""
        import re

        text = raw_text.strip()
        text = re.sub(r"```(?:json)?\s*\n?", "", text).strip()

        try:
            json_match = re.search(r"\{.*\}", text, re.DOTALL)
            if json_match:
                plan = json.loads(json_match.group(0))
                # 验证必要字段
                if "scenes" in plan and "scripts" in plan:
                    return plan
        except (json.JSONDecodeError, ValueError):
            pass

        # 后备：生成最小项目结构
        logger.warning("Failed to parse project plan JSON, using fallback")
        game_type = design_doc.get("game_type", "2d")
        base_node = "CharacterBody2D" if game_type == "2d" else "CharacterBody3D"
        scene_root = "Node2D" if game_type == "2d" else "Node3D"

        return {
            "scenes": [
                {"path": "res://scenes/main.tscn", "root_type": scene_root, "description": "Main game scene"},
                {"path": "res://scenes/player.tscn", "root_type": base_node, "description": "Player scene"},
            ],
            "scripts": [
                {"path": "res://scripts/player.gd", "extends": base_node, "description": "Player movement and actions"},
                {"path": "res://scripts/autoload/game_manager.gd", "extends": "Node", "description": "Game state manager"},
            ],
            "assets": [
                {"path": "res://assets/sprites/player.png", "type": "sprite", "description": design_doc.get("player", {}).get("description", "Player sprite")},
            ],
            "autoloads": [
                {"name": "GameManager", "path": "res://scripts/autoload/game_manager.gd"},
            ],
            "input_actions": [
                {"name": "move_left", "keys": ["A", "Left"]},
                {"name": "move_right", "keys": ["D", "Right"]},
                {"name": "jump", "keys": ["Space", "W", "Up"]},
                {"name": "attack", "keys": ["J", "X"]},
            ],
        }

    async def _generate_all_code(
        self,
        design_doc: dict[str, Any],
        project_plan: dict[str, Any],
    ) -> dict[str, str]:
        """生成所有 GDScript 文件

        Args:
            design_doc: 游戏设计文档
            project_plan: 项目结构规划

        Returns:
            {file_path: file_content} 映射
        """
        code_files: dict[str, str] = {}
        scripts = project_plan.get("scripts", [])
        design_summary = json.dumps(design_doc, indent=2, ensure_ascii=False)

        for script_info in scripts:
            script_path = script_info.get("path", "")
            extends = script_info.get("extends", "Node")
            description = script_info.get("description", "")

            if not script_path:
                continue

            prompt = (
                f"Generate a complete GDScript file for a Godot 4.4 game.\n\n"
                f"File: {script_path}\n"
                f"Extends: {extends}\n"
                f"Description: {description}\n\n"
                f"Game Design:\n{design_summary}\n\n"
                f"Project structure:\n"
                f"- Scenes: {json.dumps([s['path'] for s in project_plan.get('scenes', [])])}\n"
                f"- Autoloads: {json.dumps([a['name'] for a in project_plan.get('autoloads', [])])}\n"
                f"- Input actions: {json.dumps([a['name'] for a in project_plan.get('input_actions', [])])}\n\n"
                "Write complete, working GDScript code. Include all necessary:\n"
                "- @export variables for tuning\n"
                "- Signal declarations\n"
                "- _ready(), _process(), _physics_process() as needed\n"
                "- Input handling using Input.is_action_pressed() / Input.is_action_just_pressed()\n"
                "- Proper collision handling\n"
                "- Comments explaining logic"
            )

            result = await generate_gdscript(prompt=prompt)
            code = result.get("code", "")

            if code:
                code_files[script_path] = code
            else:
                # 生成最小骨架
                code_files[script_path] = (
                    f"extends {extends}\n"
                    f"## {description}\n\n"
                    f"func _ready() -> void:\n"
                    f"\tpass\n"
                )

        return code_files

    async def _generate_all_assets(
        self,
        design_doc: dict[str, Any],
        project_plan: dict[str, Any],
    ) -> dict[str, bytes]:
        """生成所有游戏资产（精灵图、音频等）

        Args:
            design_doc: 游戏设计文档
            project_plan: 项目结构规划

        Returns:
            {file_path: file_bytes} 映射
        """
        asset_files: dict[str, bytes] = {}
        assets = project_plan.get("assets", [])

        # 确定风格
        genre = design_doc.get("genre", "platformer")
        style = "pixel_art"
        if genre in ("rpg", "visual_novel"):
            style = "anime"
        elif genre in ("fps", "tps", "racing"):
            style = "realistic"

        for asset_info in assets:
            asset_path = asset_info.get("path", "")
            asset_type = asset_info.get("type", "sprite")
            description = asset_info.get("description", "")

            if not asset_path or asset_type != "sprite":
                continue

            try:
                result = await generate_image(
                    prompt=f"{description}, game asset, clean edges, centered",
                    style=style,
                    width=64,
                    height=64,
                    transparent_bg=True,
                )

                import base64
                image_bytes = base64.b64decode(result["image_base64"])
                asset_files[asset_path] = image_bytes

            except Exception as exc:
                logger.warning("Failed to generate asset %s: %s", asset_path, exc)
                # 生成 1x1 透明像素占位图
                asset_files[asset_path] = self._create_placeholder_png()

        return asset_files

    def _create_placeholder_png(self) -> bytes:
        """创建一个 64x64 的占位 PNG 图像"""
        import io

        try:
            from PIL import Image

            img = Image.new("RGBA", (64, 64), (128, 128, 128, 128))
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            return buffer.getvalue()
        except ImportError:
            # 手动创建最小 PNG — 1x1 灰色像素
            import struct
            import zlib

            def make_png_chunk(chunk_type: bytes, data: bytes) -> bytes:
                raw = chunk_type + data
                return struct.pack(">I", len(data)) + raw + struct.pack(">I", zlib.crc32(raw) & 0xFFFFFFFF)

            signature = b"\x89PNG\r\n\x1a\n"
            ihdr_data = struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0)
            ihdr = make_png_chunk(b"IHDR", ihdr_data)
            # 1 pixel RGBA: filter=0, R=128, G=128, B=128, A=128
            raw_data = b"\x00\x80\x80\x80\x80"
            idat = make_png_chunk(b"IDAT", zlib.compress(raw_data))
            iend = make_png_chunk(b"IEND", b"")

            return signature + ihdr + idat + iend

    async def _assemble_project(
        self,
        project_dir: Path,
        project_name: str,
        design_doc: dict[str, Any],
        project_plan: dict[str, Any],
        code_files: dict[str, str],
        asset_files: dict[str, bytes],
    ) -> list[str]:
        """组装 Godot 项目目录

        Args:
            project_dir: 项目目录路径
            project_name: 项目名称
            design_doc: 游戏设计文档
            project_plan: 项目结构规划
            code_files: 代码文件映射
            asset_files: 资产文件映射

        Returns:
            创建的文件路径列表
        """
        files_created: list[str] = []
        project_dir.mkdir(parents=True, exist_ok=True)

        # 1. 创建 project.godot
        viewport = design_doc.get("viewport", {"width": 1280, "height": 720})
        renderer = design_doc.get("renderer", "gl_compatibility")

        project_godot = PROJECT_GODOT_TEMPLATE.format(
            project_name=design_doc.get("title", project_name),
            viewport_width=viewport.get("width", 1280),
            viewport_height=viewport.get("height", 720),
            renderer=renderer,
        )

        # 添加 autoload 配置
        autoloads = project_plan.get("autoloads", [])
        if autoloads:
            project_godot += "\n[autoload]\n\n"
            for autoload in autoloads:
                name = autoload.get("name", "")
                path = autoload.get("path", "")
                if name and path:
                    project_godot += f'{name}="*{path}"\n'

        # 添加输入映射
        input_actions = project_plan.get("input_actions", [])
        if input_actions:
            project_godot += "\n[input]\n\n"
            for action in input_actions:
                action_name = action.get("name", "")
                keys = action.get("keys", [])
                if action_name and keys:
                    events = []
                    for key in keys:
                        key_code = self._key_name_to_godot(key)
                        events.append(
                            f'Object(InputEventKey,"resource_local_to_scene":false,'
                            f'"resource_name":"","device":-1,'
                            f'"window_id":0,"alt_pressed":false,'
                            f'"shift_pressed":false,"ctrl_pressed":false,'
                            f'"meta_pressed":false,"pressed":false,'
                            f'"keycode":0,"physical_keycode":{key_code},'
                            f'"key_label":0,"unicode":0,"location":0,'
                            f'"echo":false,"script":null)'
                        )
                    events_str = ", ".join(events)
                    project_godot += (
                        f'{action_name}={{\n'
                        f'"deadzone": 0.5,\n'
                        f'"events": [{events_str}]\n'
                        f"}}\n"
                    )

        project_godot_path = project_dir / "project.godot"
        project_godot_path.write_text(project_godot, encoding="utf-8")
        files_created.append(str(project_godot_path))

        # 2. 写入代码文件
        for res_path, content in code_files.items():
            # res://scripts/player.gd -> scripts/player.gd
            rel_path = res_path.replace("res://", "")
            file_path = project_dir / rel_path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")
            files_created.append(str(file_path))

        # 3. 写入资产文件
        for res_path, content_bytes in asset_files.items():
            rel_path = res_path.replace("res://", "")
            file_path = project_dir / rel_path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_bytes(content_bytes)
            files_created.append(str(file_path))

        # 4. 生成场景文件
        for scene_info in project_plan.get("scenes", []):
            scene_path = scene_info.get("path", "")
            root_type = scene_info.get("root_type", "Node2D")

            if not scene_path:
                continue

            rel_path = scene_path.replace("res://", "")
            file_path = project_dir / rel_path
            file_path.parent.mkdir(parents=True, exist_ok=True)

            tscn_content = self._generate_scene_tscn(
                root_type=root_type,
                scene_name=Path(scene_path).stem.capitalize(),
                scripts=code_files,
                scene_path=scene_path,
            )

            file_path.write_text(tscn_content, encoding="utf-8")
            files_created.append(str(file_path))

        # 5. 保存设计文档
        design_doc_path = project_dir / "design_doc.json"
        design_doc_path.write_text(
            json.dumps(design_doc, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        files_created.append(str(design_doc_path))

        logger.info("Project assembled: %s (%d files)", project_dir, len(files_created))
        return files_created

    def _generate_scene_tscn(
        self,
        root_type: str,
        scene_name: str,
        scripts: dict[str, str],
        scene_path: str,
    ) -> str:
        """生成基础 .tscn 场景文件"""
        load_steps = 1
        ext_resources: list[str] = []

        # 查找附加到此场景的脚本
        scene_stem = Path(scene_path).stem
        matching_scripts: list[str] = []
        for script_path in scripts:
            script_stem = Path(script_path).stem
            if script_stem == scene_stem or script_stem in scene_path:
                matching_scripts.append(script_path)

        if matching_scripts:
            for idx, sp in enumerate(matching_scripts):
                ext_resources.append(
                    f'[ext_resource type="Script" path="{sp}" id="{idx + 1}_script"]'
                )
                load_steps += 1

        lines: list[str] = [
            f'[gd_scene load_steps={load_steps} format=3]',
        ]

        for ext_res in ext_resources:
            lines.append("")
            lines.append(ext_res)

        lines.append("")
        lines.append(f'[node name="{scene_name}" type="{root_type}"]')

        if matching_scripts:
            lines.append(f'script = ExtResource("1_script")')

        return "\n".join(lines)

    def _key_name_to_godot(self, key_name: str) -> int:
        """将按键名称转换为 Godot keycode 常量"""
        key_map: dict[str, int] = {
            "A": 65, "B": 66, "C": 67, "D": 68, "E": 69,
            "F": 70, "G": 71, "H": 72, "I": 73, "J": 74,
            "K": 75, "L": 76, "M": 77, "N": 78, "O": 79,
            "P": 80, "Q": 81, "R": 82, "S": 83, "T": 84,
            "U": 85, "V": 86, "W": 87, "X": 88, "Y": 89,
            "Z": 90,
            "Space": 32,
            "Enter": 4194309, "Return": 4194309,
            "Escape": 4194305, "Esc": 4194305,
            "Tab": 4194306,
            "Up": 4194320, "Down": 4194322,
            "Left": 4194319, "Right": 4194321,
            "Shift": 4194325, "Ctrl": 4194326, "Alt": 4194328,
        }
        return key_map.get(key_name, key_map.get(key_name.capitalize(), 0))

    async def _run_qa(
        self,
        project_path: str,
        design_doc: dict[str, Any],
    ) -> dict[str, Any]:
        """运行视觉 QA 检查

        Args:
            project_path: 项目路径
            design_doc: 设计文档（用于构建 QA 标准）

        Returns:
            QA 结果
        """
        # 从设计文档构建 QA 标准
        qa_criteria: list[str] = [
            "The scene renders without errors",
            "Game elements are visible on screen",
        ]

        player = design_doc.get("player", {})
        if player:
            qa_criteria.append(f"Player character ({player.get('name', 'player')}) is visible")

        if design_doc.get("assets_needed", {}).get("ui"):
            qa_criteria.append("UI elements are present and readable")

        try:
            result = await visual_qa_pipeline.run_qa(
                project_path=project_path,
                scene_path="res://scenes/main.tscn",
                qa_criteria=qa_criteria,
                max_iterations=2,
            )
            return result
        except Exception as exc:
            logger.warning("QA pipeline failed: %s", exc)
            return {
                "passed": False,
                "iterations": 0,
                "issues_found": [{"type": "qa_error", "description": str(exc)}],
                "fixes_applied": [],
                "screenshots": [],
                "final_analysis": {},
            }


# ---------------------------------------------------------------------------
# 单例
# ---------------------------------------------------------------------------

game_from_text_pipeline = GameFromTextPipeline()
