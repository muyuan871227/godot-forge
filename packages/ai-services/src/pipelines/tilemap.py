"""瓦片地图生成管线 — 从主题描述生成 Tileset + TileMap

完整流程:
1. 生成 tileset 图像（包含所有瓦片类型）
2. 使用 LLM 根据主题生成 2D 地图布局 JSON
3. 生成 Godot TileSet .tres 资源
4. 生成 Godot TileMap .tscn 场景文件
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
from ..services.llm_service import _call_llm

logger = logging.getLogger(__name__)

TILEMAP_OUTPUT_DIR = Path("/tmp/godotforge/tilemaps")
TILEMAP_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 瓦片类型定义 — 用于 LLM 生成地图布局时的参照
TILE_TYPES = {
    "forest": {
        0: "grass",
        1: "dirt_path",
        2: "tree",
        3: "bush",
        4: "water",
        5: "flower",
        6: "rock",
        7: "bridge",
    },
    "dungeon": {
        0: "stone_floor",
        1: "wall",
        2: "door",
        3: "chest",
        4: "torch",
        5: "pit",
        6: "stairs_up",
        7: "stairs_down",
    },
    "city": {
        0: "road",
        1: "sidewalk",
        2: "building",
        3: "park",
        4: "water",
        5: "bridge",
        6: "market_stall",
        7: "fountain",
    },
    "desert": {
        0: "sand",
        1: "dune",
        2: "cactus",
        3: "oasis_water",
        4: "palm_tree",
        5: "rock",
        6: "ruins",
        7: "path",
    },
    "snow": {
        0: "snow_ground",
        1: "ice",
        2: "pine_tree",
        3: "frozen_lake",
        4: "snow_rock",
        5: "cabin",
        6: "path",
        7: "snowdrift",
    },
}


class TilemapPipeline:
    """瓦片地图生成管线

    从主题描述生成完整的 tileset 图像、地图布局和 Godot 资源文件。
    """

    async def generate(
        self,
        theme: str,
        map_width: int = 20,
        map_height: int = 15,
        tile_size: int = 16,
        style: str = "pixel_art",
    ) -> dict[str, Any]:
        """生成完整的瓦片地图包

        Args:
            theme: 地图主题 (forest, dungeon, city, desert, snow, 或自定义描述)
            map_width: 地图宽度（瓦片数）
            map_height: 地图高度（瓦片数）
            tile_size: 单个瓦片尺寸（像素）
            style: 图像风格预设

        Returns:
            dict with keys:
                - tileset_path: tileset 图像路径
                - tileset_base64: tileset 图像 base64
                - map_layout: 2D 瓦片索引数组
                - tileset_tres_path: TileSet .tres 路径
                - tileset_tres_content: TileSet .tres 内容
                - tilemap_tscn_path: TileMap .tscn 路径
                - tilemap_tscn_content: TileMap .tscn 内容
                - tile_types: 瓦片类型映射
        """
        session_id = uuid.uuid4().hex[:8]
        session_dir = TILEMAP_OUTPUT_DIR / session_id
        session_dir.mkdir(parents=True, exist_ok=True)

        logger.info(
            "Generating tilemap: theme=%s, size=%dx%d, tile=%dpx, style=%s",
            theme,
            map_width,
            map_height,
            tile_size,
            style,
        )

        # 解析主题对应的瓦片类型
        theme_key = theme.lower().strip()
        tile_types = TILE_TYPES.get(theme_key, TILE_TYPES["forest"])
        num_tile_types = len(tile_types)

        # Step 1: 生成 tileset 图像
        tileset_bytes, tileset_base64 = await self._generate_tileset(
            theme=theme,
            tile_types=tile_types,
            tile_size=tile_size,
            style=style,
        )
        tileset_path = session_dir / "tileset.png"
        tileset_path.write_bytes(tileset_bytes)

        # Step 2: 使用 LLM 生成地图布局
        map_layout = await self._generate_map_layout(
            theme=theme,
            tile_types=tile_types,
            map_width=map_width,
            map_height=map_height,
        )

        # 保存地图布局 JSON
        layout_path = session_dir / "map_layout.json"
        layout_path.write_text(
            json.dumps({"layout": map_layout, "tile_types": tile_types}, indent=2),
            encoding="utf-8",
        )

        # Step 3: 生成 TileSet .tres 资源
        tileset_tres_content = self._generate_tileset_resource(
            tileset_filename="tileset.png",
            tile_types=tile_types,
            tile_size=tile_size,
        )
        tileset_tres_path = session_dir / "tileset.tres"
        tileset_tres_path.write_text(tileset_tres_content, encoding="utf-8")

        # Step 4: 生成 TileMap .tscn 场景
        tilemap_tscn_content = self._generate_tilemap_scene(
            map_layout=map_layout,
            tileset_tres_filename="tileset.tres",
            tile_size=tile_size,
        )
        tilemap_tscn_path = session_dir / "tilemap.tscn"
        tilemap_tscn_path.write_text(tilemap_tscn_content, encoding="utf-8")

        logger.info("Tilemap generated: %s", session_dir)

        return {
            "tileset_path": str(tileset_path),
            "tileset_base64": tileset_base64,
            "map_layout": map_layout,
            "tileset_tres_path": str(tileset_tres_path),
            "tileset_tres_content": tileset_tres_content,
            "tilemap_tscn_path": str(tilemap_tscn_path),
            "tilemap_tscn_content": tilemap_tscn_content,
            "tile_types": tile_types,
            "session_dir": str(session_dir),
        }

    async def _generate_tileset(
        self,
        theme: str,
        tile_types: dict[int, str],
        tile_size: int,
        style: str,
    ) -> tuple[bytes, str]:
        """生成 tileset 图像

        将所有瓦片类型排列为水平条带。

        Args:
            theme: 地图主题
            tile_types: 瓦片类型映射 {index: name}
            tile_size: 单个瓦片尺寸
            style: 图像风格

        Returns:
            (tileset_bytes, tileset_base64)
        """
        num_tiles = len(tile_types)
        tile_names = [tile_types[i] for i in range(num_tiles)]

        # 构建精确的 tileset 生成提示词
        tile_desc = ", ".join(tile_names)
        prompt = (
            f"Top-down {theme} tileset for a 2D game, "
            f"{num_tiles} tiles in a single horizontal row: {tile_desc}. "
            f"Each tile is {tile_size}x{tile_size} pixels, seamless edges, "
            f"consistent lighting, game-ready tileset sprite sheet"
        )

        result = await generate_image(
            prompt=prompt,
            style=style,
            width=tile_size * num_tiles,
            height=tile_size,
            transparent_bg=False,
        )

        tileset_bytes = base64.b64decode(result["image_base64"])
        return tileset_bytes, result["image_base64"]

    async def _generate_map_layout(
        self,
        theme: str,
        tile_types: dict[int, str],
        map_width: int,
        map_height: int,
    ) -> list[list[int]]:
        """使用 LLM 生成 2D 地图布局

        LLM 返回一个 map_height x map_width 的 2D 数组，每个值是瓦片类型索引。

        Args:
            theme: 地图主题
            tile_types: 瓦片类型映射
            map_width: 地图宽度（瓦片数）
            map_height: 地图高度（瓦片数）

        Returns:
            2D 列表 — map_layout[row][col] = tile_type_index
        """
        tile_desc = "\n".join(f"  {idx}: {name}" for idx, name in tile_types.items())

        system_prompt = (
            "You are a game level designer. Generate a 2D tile map layout as a JSON array. "
            "Return ONLY a valid JSON object, no explanation, no markdown code fences."
        )

        prompt = (
            f"Generate a {theme}-themed top-down 2D game map.\n\n"
            f"Map dimensions: {map_width} columns x {map_height} rows\n\n"
            f"Available tile types:\n{tile_desc}\n\n"
            "Design guidelines:\n"
            "- Create an interesting, playable layout\n"
            "- Include paths connecting different areas\n"
            "- Place obstacles and features naturally\n"
            "- Ensure the edges use appropriate boundary tiles\n"
            "- Make the map visually varied but cohesive\n\n"
            "Return a JSON object with a single key \"layout\" containing "
            f"a 2D array of {map_height} rows, each with {map_width} integer values. "
            "Each value is a tile type index from the list above.\n\n"
            "Example for a 3x3 map: {\"layout\": [[0,0,1],[0,2,0],[1,0,0]]}"
        )

        try:
            result = await _call_llm(prompt, system_prompt=system_prompt)
            raw_text = result.get("_raw_text", "") or result.get("explanation", "")

            # 尝试从响应中提取 JSON
            layout = self._parse_layout_json(raw_text, map_width, map_height, len(tile_types))

            if layout is not None:
                return layout

        except Exception as exc:
            logger.warning("LLM map layout generation failed: %s, using fallback", exc)

        # 如果 LLM 失败，使用算法生成
        return self._fallback_layout(theme, map_width, map_height, len(tile_types))

    def _parse_layout_json(
        self,
        raw_text: str,
        map_width: int,
        map_height: int,
        num_tile_types: int,
    ) -> list[list[int]] | None:
        """从 LLM 响应中解析地图布局 JSON

        Returns:
            解析后的 2D 数组，或 None（如果解析失败）
        """
        import re

        # 尝试直接解析
        text = raw_text.strip()

        # 移除 markdown 代码围栏
        text = re.sub(r"```(?:json)?\s*\n?", "", text)
        text = text.strip()

        # 尝试找到 JSON 对象
        json_match = re.search(r"\{.*\}", text, re.DOTALL)
        if json_match:
            text = json_match.group(0)

        try:
            data = json.loads(text)
            layout = data.get("layout", data) if isinstance(data, dict) else data

            # 验证布局
            if not isinstance(layout, list) or len(layout) == 0:
                return None

            # 确保尺寸和值范围正确
            validated: list[list[int]] = []
            for row_idx, row in enumerate(layout[:map_height]):
                if not isinstance(row, list):
                    return None
                validated_row: list[int] = []
                for col_idx, val in enumerate(row[:map_width]):
                    tile_idx = int(val) % num_tile_types
                    validated_row.append(tile_idx)
                # 如果行太短，用 0 填充
                while len(validated_row) < map_width:
                    validated_row.append(0)
                validated.append(validated_row)

            # 如果行太少，用默认行填充
            while len(validated) < map_height:
                validated.append([0] * map_width)

            return validated

        except (json.JSONDecodeError, ValueError, TypeError):
            return None

    def _fallback_layout(
        self,
        theme: str,
        map_width: int,
        map_height: int,
        num_tile_types: int,
    ) -> list[list[int]]:
        """算法生成的后备地图布局

        生成一个包含简单路径和边界的基础地图。
        """
        import random

        random.seed(hash(theme) % 2**32)

        # 基础 — 全部填充地面瓦片 (index 0)
        layout: list[list[int]] = [[0] * map_width for _ in range(map_height)]

        # 添加边界（使用 index 1 或 wall 类型）
        boundary_tile = min(1, num_tile_types - 1)
        for x in range(map_width):
            layout[0][x] = boundary_tile
            layout[map_height - 1][x] = boundary_tile
        for y in range(map_height):
            layout[y][0] = boundary_tile
            layout[y][map_width - 1] = boundary_tile

        # 创建一条蜿蜒的路径 (index 1 if path exists)
        path_tile = min(1, num_tile_types - 1)
        cx, cy = map_width // 2, 1
        for _ in range(map_height - 2):
            layout[cy][cx] = path_tile
            cy += 1
            # 随机左右偏移
            cx = max(1, min(map_width - 2, cx + random.choice([-1, 0, 0, 1])))

        # 随机散布装饰物
        for _ in range(map_width * map_height // 8):
            rx = random.randint(1, map_width - 2)
            ry = random.randint(1, map_height - 2)
            if layout[ry][rx] == 0:
                layout[ry][rx] = random.randint(2, min(5, num_tile_types - 1))

        return layout

    def _generate_tileset_resource(
        self,
        tileset_filename: str,
        tile_types: dict[int, str],
        tile_size: int,
    ) -> str:
        """生成 Godot TileSet .tres 资源文件

        Args:
            tileset_filename: tileset 图像文件名
            tile_types: 瓦片类型映射
            tile_size: 单个瓦片尺寸

        Returns:
            .tres 文件内容
        """
        num_tiles = len(tile_types)

        # Godot 4 TileSet 资源格式
        lines: list[str] = [
            f'[gd_resource type="TileSet" load_steps=2 format=3]',
            "",
            f'[ext_resource type="Texture2D" '
            f'path="res://assets/tilemaps/{tileset_filename}" '
            f'id="1_tileset"]',
            "",
            "[resource]",
            f"tile_size = Vector2i({tile_size}, {tile_size})",
        ]

        # 添加 TileSetAtlasSource
        lines.append("")
        lines.append("[sub_resource type=\"TileSetAtlasSource\" id=\"TileSetAtlasSource_1\"]")
        lines.append(f'texture = ExtResource("1_tileset")')
        lines.append(f"texture_region_size = Vector2i({tile_size}, {tile_size})")

        # 为每个瓦片类型定义 tile data
        for idx in range(num_tiles):
            atlas_x = idx
            atlas_y = 0
            tile_name = tile_types.get(idx, f"tile_{idx}")

            lines.append(f"{atlas_x}:0/0 = 0")  # 基本 tile data

            # 定义碰撞 — wall/obstacle 类型添加碰撞层
            if tile_name in ("wall", "tree", "rock", "building", "cactus", "pine_tree"):
                lines.append(
                    f"{atlas_x}:0/0/physics_layer_0/polygon_0/points = "
                    f"PackedVector2Array(0, 0, {tile_size}, 0, {tile_size}, {tile_size}, 0, {tile_size})"
                )

        # 添加源到 TileSet
        lines.append("")
        lines.append("0/source = SubResource(\"TileSetAtlasSource_1\")")

        # 添加物理层
        lines.append("physics_layer_0/collision_layer = 1")
        lines.append("physics_layer_0/collision_mask = 1")

        return "\n".join(lines)

    def _generate_tilemap_scene(
        self,
        map_layout: list[list[int]],
        tileset_tres_filename: str,
        tile_size: int,
    ) -> str:
        """生成 Godot TileMap .tscn 场景文件

        Args:
            map_layout: 2D 瓦片索引数组
            tileset_tres_filename: TileSet .tres 文件名
            tile_size: 单个瓦片尺寸

        Returns:
            .tscn 文件内容
        """
        lines: list[str] = [
            '[gd_scene load_steps=2 format=3]',
            "",
            f'[ext_resource type="TileSet" '
            f'path="res://assets/tilemaps/{tileset_tres_filename}" '
            f'id="1_tileset"]',
            "",
            '[node name="TileMap" type="TileMapLayer"]',
            'tile_set = ExtResource("1_tileset")',
        ]

        # 生成 tile_map_data — Godot 4 使用稀疏格式
        # 格式: source_id, atlas_coords, alternative_tile
        tile_data_entries: list[str] = []

        for row_idx, row in enumerate(map_layout):
            for col_idx, tile_type in enumerate(row):
                if tile_type >= 0:
                    # Godot 4 TileMapLayer tile_map_data 格式:
                    # Vector2i(col, row) => source_id=0, atlas_coords=Vector2i(tile_type, 0)
                    tile_data_entries.append(
                        f"Vector2i({col_idx}, {row_idx}), 0, Vector2i({tile_type}, 0), 0"
                    )

        if tile_data_entries:
            # Godot 4 TileMapLayer 使用 tile_map_data 属性
            lines.append(f"tile_map_data = PackedByteArray()")

        # 为 Godot 4.x 生成 layer_0/tile_data
        # 实际中 Godot 使用压缩的二进制格式
        # 这里使用场景脚本来在运行时设置瓦片
        lines.append("")
        lines.append('[node name="MapLoader" type="Node" parent="."]')
        lines.append('script = ExtResource("map_loader_script")')
        lines.append("")

        # 生成 map_loader.gd 内联脚本内容作为注释
        lines.append(f"# Map layout data ({len(map_layout)}x{len(map_layout[0]) if map_layout else 0}):")
        lines.append(f"# Use the JSON layout file to populate tiles at runtime")

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# 单例
# ---------------------------------------------------------------------------

tilemap_pipeline = TilemapPipeline()
