"""图像生成路由 — 游戏图像资产生成"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..services.image_service import generate_image

router = APIRouter()


class ImageGenRequest(BaseModel):
    prompt: str = Field(..., description="图像描述")
    style: str = Field(
        default="pixel_art",
        description="风格预设: pixel_art, hand_drawn, anime, realistic",
    )
    width: int = Field(default=512, ge=64, le=2048, description="图像宽度")
    height: int = Field(default=512, ge=64, le=2048, description="图像高度")
    sprite_sheet: bool = Field(default=False, description="是否生成精灵图表")
    sprite_frames: int = Field(default=4, ge=1, le=32, description="精灵图帧数")
    transparent_bg: bool = Field(default=False, description="是否透明背景")
    negative_prompt: str = Field(default="", description="负面提示词")


class ImageGenResponse(BaseModel):
    image_base64: str
    width: int
    height: int
    format: str


class SpriteSheetResponse(BaseModel):
    image_base64: str
    width: int
    height: int
    format: str
    frames: int
    frame_width: int
    frame_height: int


class TilemapRequest(BaseModel):
    prompt: str = Field(..., description="瓦片地图描述")
    style: str = Field(default="pixel_art", description="风格预设")
    tile_size: int = Field(default=16, description="单个瓦片尺寸 (像素)")
    columns: int = Field(default=8, ge=1, le=32, description="列数")
    rows: int = Field(default=8, ge=1, le=32, description="行数")
    negative_prompt: str = Field(default="", description="负面提示词")


class TilemapResponse(BaseModel):
    image_base64: str
    width: int
    height: int
    format: str
    tile_size: int
    columns: int
    rows: int


@router.post("/generate", response_model=ImageGenResponse)
async def api_generate_image(req: ImageGenRequest):
    """生成单张游戏图像资产"""
    try:
        result = await generate_image(
            prompt=req.prompt,
            style=req.style,
            width=req.width,
            height=req.height,
            negative_prompt=req.negative_prompt,
            transparent_bg=req.transparent_bg,
        )
        return ImageGenResponse(
            image_base64=result["image_base64"],
            width=result["width"],
            height=result["height"],
            format=result["format"],
        )
    except TimeoutError as exc:
        raise HTTPException(status_code=504, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/sprite-sheet", response_model=SpriteSheetResponse)
async def api_generate_sprite_sheet(req: ImageGenRequest):
    """生成精灵图表 — 将多帧排列在单张图片中"""
    frames = req.sprite_frames if req.sprite_sheet else 4
    frame_w = req.width
    frame_h = req.height
    sheet_width = frame_w * frames
    sheet_height = frame_h

    enhanced_prompt = (
        f"{req.prompt}, sprite sheet with {frames} frames showing animation sequence, "
        f"evenly spaced, side by side, consistent character design across all frames"
    )

    try:
        result = await generate_image(
            prompt=enhanced_prompt,
            style=req.style,
            width=sheet_width,
            height=sheet_height,
            negative_prompt=req.negative_prompt,
            transparent_bg=req.transparent_bg,
        )
        return SpriteSheetResponse(
            image_base64=result["image_base64"],
            width=result["width"],
            height=result["height"],
            format=result["format"],
            frames=frames,
            frame_width=frame_w,
            frame_height=frame_h,
        )
    except TimeoutError as exc:
        raise HTTPException(status_code=504, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/tilemap", response_model=TilemapResponse)
async def api_generate_tilemap(req: TilemapRequest):
    """生成瓦片地图纹理集"""
    total_width = req.tile_size * req.columns
    total_height = req.tile_size * req.rows

    enhanced_prompt = (
        f"{req.prompt}, seamless tilemap tileset, {req.columns}x{req.rows} grid, "
        f"each tile {req.tile_size}x{req.tile_size} pixels, top-down view, "
        f"consistent style, game tiles"
    )

    try:
        result = await generate_image(
            prompt=enhanced_prompt,
            style=req.style,
            width=total_width,
            height=total_height,
            negative_prompt=req.negative_prompt,
            transparent_bg=False,
        )
        return TilemapResponse(
            image_base64=result["image_base64"],
            width=result["width"],
            height=result["height"],
            format=result["format"],
            tile_size=req.tile_size,
            columns=req.columns,
            rows=req.rows,
        )
    except TimeoutError as exc:
        raise HTTPException(status_code=504, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
