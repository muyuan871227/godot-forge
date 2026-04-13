"""端到端集成测试"""
import httpx
import pytest

API_URL = "http://localhost:8100"


@pytest.mark.asyncio
async def test_code_generation():
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{API_URL}/api/v1/codegen/generate",
            json={
                "prompt": "Create a simple player movement script for a 2D platformer",
                "godot_version": "4.4",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "code" in data
        assert "extends" in data["code"]
        assert len(data["files"]) > 0


@pytest.mark.asyncio
async def test_image_generation():
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(
            f"{API_URL}/api/v1/imagegen/generate",
            json={
                "prompt": "a cute slime monster",
                "style": "pixel_art",
                "width": 64,
                "height": 64,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "image_base64" in data


@pytest.mark.asyncio
async def test_health():
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{API_URL}/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_codegen_fix():
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{API_URL}/api/v1/codegen/fix",
            params={
                "script_content": 'extends Node2D\n\nfunc _ready():\n\tvar x = "hello"\n\tx.invalid_method()',
            },
            json=["Method 'invalid_method' not found in String"],
        )
        assert resp.status_code == 200


@pytest.mark.asyncio
async def test_sfx_generation():
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(
            f"{API_URL}/api/v1/audiogen/sfx",
            json={"description": "coin pickup sound", "duration": 0.5, "format": "wav"},
        )
        assert resp.status_code == 200


@pytest.mark.asyncio
async def test_bgm_generation():
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(
            f"{API_URL}/api/v1/audiogen/bgm",
            json={
                "description": "chiptune adventure theme",
                "duration": 10.0,
                "loop": True,
            },
        )
        assert resp.status_code == 200
