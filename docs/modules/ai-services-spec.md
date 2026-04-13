# AI Services Architecture Specification

## Overview

AI Services is the Python-based backend that provides all AI-powered capabilities for GodotForge: code generation, image synthesis, 3D model creation, audio production, and NPC AI. It exposes a RESTful API via FastAPI and supports swappable provider backends for each AI modality.

**Package:** `packages/ai-services`
**Language:** Python 3.11+
**Framework:** FastAPI + Uvicorn
**Default port:** 8100

---

## Architecture Diagram

```
                    HTTP / WebSocket
                         |
              +----------v-----------+
              |   FastAPI Application |
              |      (main.py)       |
              +--+--+--+--+--+--+---+
                 |  |  |  |  |  |
    +------------+  |  |  |  |  +------------+
    v               v  v  v  v               v
 Routers:       codegen imagegen           Enterprise
 users          modelgen audiogen          Education
 projects       npcai    build             Community
                 |  |  |  |
              +--v--v--v--v--+
              |   Services    |
              | (llm_service, |
              | image_service, |
              | audio_service) |
              +--+--+--+--+--+
                 |  |  |  |
              +--v--v--v--v--+
              |   Providers   |
              | anthropic     |
              | openai        |
              | ollama        |
              | comfyui       |
              | hunyuan3d     |
              | bark/musicgen |
              +---------------+
```

---

## Module Breakdown

### `src/main.py` -- FastAPI Entry Point

Creates the FastAPI application, configures CORS, and registers all routers. Uses the lifespan context manager for startup/shutdown logging.

### `src/config.py` -- Configuration

Centralised configuration via `pydantic-settings`. All values are loaded from environment variables with the `GODOTFORGE_` prefix or a `.env` file.

Key configuration groups:

- **LLM**: provider selection (anthropic / openai / ollama), API keys, model names
- **Image**: provider (comfyui / replicate / local), connection URLs
- **3D Model**: provider (hunyuan3d / triposr / meshy_api), model paths
- **Audio**: provider (bark / musicgen / elevenlabs), model paths
- **Godot**: path to the Godot binary

---

## Routers

### Code Generation (`routers/codegen.py`)

Generates, fixes, and explains GDScript code.

- `POST /generate` -- Takes a prompt, optional scene tree context, and existing scripts; returns GDScript code with explanation.
- `POST /fix` -- Accepts error messages and script content; returns corrected code.
- `POST /explain` -- Returns a plain-English explanation of a GDScript snippet.

### Image Generation (`routers/imagegen.py`)

Generates 2D art assets: sprites, tilesets, UI elements, and backgrounds.

- `POST /generate` -- General image generation from a text prompt.
- `POST /sprite-sheet` -- Generates a sprite sheet with configurable grid dimensions.
- `POST /tileset` -- Generates a tileset image for use with TileMap.

### 3D Model Generation (`routers/modelgen.py`)

Creates 3D models from text prompts or reference images.

- `POST /generate` -- Text-to-3D model generation.
- `POST /optimize` -- Polygon reduction and mesh optimisation.
- `GET /status/{job_id}` -- Async job status polling.

### Audio Generation (`routers/audiogen.py`)

Generates sound effects, background music, and voice lines.

- `POST /sfx` -- Text-to-SFX generation (via Bark).
- `POST /bgm` -- Background music generation (via MusicGen).
- `POST /tts` -- Text-to-speech for NPC dialogue.

### NPC AI (`routers/npcai.py`)

Powers dynamic NPC interactions.

- `POST /dialogue` -- Generates in-character NPC replies with emotion and action suggestions.
- `POST /behavior` -- Generates GDScript behavior tree implementations for NPC archetypes.

### Users (`routers/users.py`)

User registration, JWT authentication, and profile management.

### Projects (`routers/projects.py`)

CRUD operations for project records associated with users.

### Build & Export (`routers/build.py`)

Triggers Godot export builds for target platforms.

### Enterprise (`routers/enterprise.py`)

Enterprise-only features: model training, batch generation, usage analytics, and audit logging.

### Education (`routers/education.py`)

Tutorial system, classroom management, assignments, and student progress tracking.

### Community (`routers/community.py`)

Game publishing, browsing, rating, and game jam management.

---

## Services Layer

### `services/llm_service.py`

Unified interface for LLM calls. Selects the active provider from configuration and routes requests accordingly.

```python
async def generate_gdscript(
    prompt: str,
    context: str = "",
    scene_tree: str = "",
    existing_scripts: list[str] | None = None,
    godot_version: str = "4.4",
) -> dict:
    """Generate GDScript code via the configured LLM provider."""
```

### `services/image_service.py`

Handles image generation requests. Manages prompt engineering for game art, post-processing (background removal, palette normalisation), and format conversion.

### `services/model3d_service.py`

Coordinates 3D model generation. Supports text-to-3D via Hunyuan3D or TripoSR, with automatic mesh optimisation for real-time rendering.

### `services/audio_service.py`

Manages audio generation. Routes to Bark (SFX/TTS) or MusicGen (BGM) based on request type. Handles audio format conversion and normalisation.

### `services/asset_pipeline.py`

Post-processing pipeline that transforms raw AI outputs into Godot-ready resources:

- PNG sprite sheets -> split frames + `.import` metadata
- GLTF/GLB models -> Godot `.tres` materials
- WAV/OGG audio -> proper sample rate + bit depth

---

## Providers

Each provider implements a consistent interface and is selected via configuration.

| Provider | Modality | Type |
|----------|----------|------|
| `providers/anthropic.py` | LLM | Cloud API |
| `providers/openai.py` | LLM | Cloud API |
| `providers/ollama.py` | LLM | Local server |
| `providers/comfyui.py` | Image | Local server |
| `providers/hunyuan3d.py` | 3D Model | Local GPU |
| `providers/triposr.py` | 3D Model | Local GPU |
| `providers/bark.py` | Audio (SFX/TTS) | Local GPU |
| `providers/musicgen.py` | Audio (BGM) | Local GPU |

---

## Pipelines

High-level orchestration flows that combine multiple services.

### `pipelines/game_from_text.py`

The flagship pipeline: converts a natural-language game description into a complete Godot project.

1. Parse the game description with the LLM to extract game design elements.
2. Generate the project structure and scene hierarchy.
3. Generate GDScript code for game mechanics.
4. Generate art assets (sprites, tilesets, UI).
5. Generate audio assets (SFX, BGM).
6. Assemble everything into a runnable Godot project.

### `pipelines/sprite_sheet.py`

Generates animated sprite sheets: single image generation, grid slicing, frame validation, and `.import` file creation.

### `pipelines/tilemap.py`

Generates tilesets with auto-tile rules: base tile generation, edge/corner variant creation, TileSet resource assembly.

### `pipelines/character.py`

Full character asset pipeline: sprite sheet + portrait + animation frames.

### `pipelines/environment.py`

Environment asset pipeline: background layers, tileset, parallax configuration.

---

## Data Storage

In the development/default configuration, data is stored in JSON files under `/tmp/godotforge/`. In enterprise deployments, storage is backed by PostgreSQL (structured data) and MinIO/S3 (binary assets).

---

## Running

```bash
cd packages/ai-services
pip install -r requirements.txt
uvicorn src.main:app --host 0.0.0.0 --port 8100 --reload
```

---

## Testing

```bash
cd packages/ai-services
pytest tests/ -v
```
