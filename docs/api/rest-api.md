# REST API Reference

GodotForge AI Services exposes a RESTful API via FastAPI. The default base URL is `http://localhost:8100`.

## Authentication

Most endpoints require a JWT bearer token obtained from the `/api/v1/users/login` endpoint.

```bash
# Register
curl -X POST http://localhost:8100/api/v1/users/register \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","email":"alice@example.com","password":"secret123"}'

# Login (OAuth2 form)
curl -X POST http://localhost:8100/api/v1/users/login \
  -d "username=alice&password=secret123"

# Authenticated request
curl http://localhost:8100/api/v1/users/me \
  -H "Authorization: Bearer <token>"
```

---

## Health Check

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/health` | No | Returns `{"status":"ok","version":"0.1.0"}` |

---

## Users (`/api/v1/users`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/register` | No | Create a new account. Returns JWT. |
| POST | `/login` | No | Authenticate with username + password. Returns JWT. |
| GET | `/me` | Yes | Return the current user's profile. |

### POST `/register`

**Request body:**
```json
{
  "username": "alice",
  "email": "alice@example.com",
  "password": "secret123",
  "display_name": "Alice"
}
```

**Response (201):**
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 86400,
  "user": {
    "id": "a1b2c3...",
    "username": "alice",
    "email": "alice@example.com",
    "display_name": "Alice",
    "created_at": "2026-04-13T00:00:00+00:00"
  }
}
```

---

## Code Generation (`/api/v1/codegen`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/generate` | No | Generate GDScript code from a natural-language prompt. |
| POST | `/fix` | No | Fix GDScript errors given error messages and source code. |
| POST | `/explain` | No | Explain what a GDScript snippet does. |

### POST `/generate`

**Request body:**
```json
{
  "prompt": "Create a CharacterBody2D movement script with 300 px/s speed",
  "context": "",
  "scene_tree": "Player (CharacterBody2D) > Sprite2D, CollisionShape2D",
  "existing_scripts": [],
  "godot_version": "4.4"
}
```

**Response (200):**
```json
{
  "code": "extends CharacterBody2D\n\n@export var speed := 300.0\n...",
  "explanation": "This script handles 8-direction movement...",
  "files": [
    {"path": "res://scripts/player.gd", "content": "..."}
  ]
}
```

---

## Image Generation (`/api/v1/imagegen`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/generate` | No | Generate an image from a text prompt. |
| POST | `/sprite-sheet` | No | Generate a sprite sheet with specified columns and frame count. |
| POST | `/tileset` | No | Generate a tileset image for use with TileMap. |

---

## 3D Model Generation (`/api/v1/modelgen`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/generate` | No | Generate a 3D model from a text prompt or reference image. |
| POST | `/optimize` | No | Reduce polygon count and optimize a mesh for real-time use. |
| GET | `/status/{job_id}` | No | Poll the status of an async generation job. |

---

## Audio Generation (`/api/v1/audiogen`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/sfx` | No | Generate a sound effect from a text description. |
| POST | `/bgm` | No | Generate background music with specified mood and duration. |
| POST | `/tts` | No | Generate text-to-speech audio for NPC dialogue. |

---

## NPC AI (`/api/v1/npcai`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/dialogue` | No | Generate an in-character NPC dialogue reply. |
| POST | `/behavior` | No | Generate a behavior tree GDScript for an NPC type. |

### POST `/dialogue`

**Request body:**
```json
{
  "npc_name": "Elder Sage",
  "npc_personality": "mysterious, wise",
  "npc_background": "Ancient guardian of the forest",
  "player_message": "Where can I find the lost sword?",
  "conversation_history": [],
  "game_context": "Player has completed the forest quest",
  "max_tokens": 256
}
```

**Response (200):**
```json
{
  "npc_reply": "The blade you seek rests where shadows dare not reach...",
  "emotion": "mysterious",
  "suggested_actions": ["give_quest", "hint"]
}
```

---

## Projects (`/api/v1/projects`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/` | Yes | Create a new project record. |
| GET | `/` | Yes | List the current user's projects. |
| GET | `/{id}` | Yes | Get project details. |
| PUT | `/{id}` | Yes | Update project metadata. |
| DELETE | `/{id}` | Yes | Delete a project. |

---

## Build & Export (`/api/v1/build`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/export` | Yes | Trigger a project export for a target platform. |
| GET | `/export/{job_id}` | Yes | Check export job status and download link. |
| GET | `/presets` | No | List available export preset templates. |

---

## Enterprise (`/api/v1/enterprise`)

> Requires authentication. Available in enterprise deployments.

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/train-model` | Yes | Queue a custom model fine-tuning job. |
| GET | `/train-model/{job_id}` | Yes | Get training job status. |
| POST | `/batch-generate` | Yes | Submit a batch of up to 500 asset generation requests. |
| GET | `/batch-generate/{job_id}` | Yes | Get batch job status. |
| GET | `/usage-analytics` | Yes | Aggregated usage statistics for the deployment. |
| GET | `/audit-log` | Yes | Paginated audit trail with action and user filters. |

### POST `/train-model`

**Request body:**
```json
{
  "model_name": "my-gdscript-model",
  "base_model": "deepseek-coder-v2:16b",
  "dataset_path": "s3://godotforge-training/gdscript-dataset.jsonl",
  "epochs": 3,
  "learning_rate": 2e-5,
  "batch_size": 4,
  "max_seq_length": 2048,
  "description": "Fine-tuned on our studio's GDScript patterns"
}
```

**Response (202):**
```json
{
  "job_id": "abc123...",
  "status": "queued",
  "model_name": "my-gdscript-model",
  "created_at": "2026-04-13T00:00:00+00:00",
  "message": "Training job queued."
}
```

### POST `/batch-generate`

**Request body:**
```json
{
  "items": [
    {"asset_type": "sprite", "prompt": "Pixel art warrior, 32x32"},
    {"asset_type": "audio_sfx", "prompt": "Sword slash sound effect"},
    {"asset_type": "script", "prompt": "Health bar UI component"}
  ],
  "project_id": "proj-123",
  "priority": 5,
  "webhook_url": "https://myserver.com/webhook/batch-done"
}
```

---

## Education (`/api/v1/education`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/tutorials` | No | List tutorials (filter by difficulty or tag). |
| GET | `/tutorials/{id}` | No | Get a tutorial with all steps. |
| POST | `/classroom` | Yes | Create a classroom (generates invite code). |
| GET | `/classroom` | Yes | List classrooms the user belongs to. |
| GET | `/classroom/{id}` | Yes | Get classroom details. |
| POST | `/classroom/{id}/join` | Yes | Join a classroom with an invite code. |
| POST | `/classroom/{id}/assignments` | Yes | Create an assignment (teacher only). |
| GET | `/classroom/{id}/assignments` | Yes | List assignments for a classroom. |
| GET | `/classroom/{id}/progress` | Yes | View student progress. |
| POST | `/classroom/{id}/submit` | Yes | Submit work for an assignment. |

---

## Community (`/api/v1/community`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/games` | Yes | Publish a game to the showcase. |
| GET | `/games` | No | Browse games (search, filter by tag, sort, paginate). |
| GET | `/games/{id}` | No | Get game details. |
| POST | `/games/{id}/rate` | Yes | Rate a game (1-5 stars, optional review). |
| POST | `/gamejam` | Yes | Create a game jam event. |
| GET | `/gamejam` | No | List game jams (optional status filter). |
| GET | `/gamejam/{id}` | No | Get game jam details. |
| POST | `/gamejam/{id}/join` | Yes | Join a game jam. |
| POST | `/gamejam/{id}/submit` | Yes | Submit a game entry to a jam. |

### POST `/games`

**Request body:**
```json
{
  "title": "Stellar Escape",
  "description": "A fast-paced space shooter...",
  "web_url": "https://username.itch.io/stellar-escape",
  "screenshots": ["https://cdn.example.com/ss1.png"],
  "tags": ["2d", "shooter", "arcade"],
  "source_url": "https://github.com/user/stellar-escape",
  "godot_version": "4.4"
}
```

---

## Error Responses

All endpoints return errors in a consistent format:

```json
{
  "detail": "Invalid credentials"
}
```

Common HTTP status codes:

| Code | Meaning |
|------|---------|
| 400 | Bad request / validation error |
| 401 | Missing or expired authentication |
| 403 | Insufficient permissions |
| 404 | Resource not found |
| 409 | Conflict (duplicate username, etc.) |
| 422 | Request body validation failed |
| 500 | Internal server error |

---

## Interactive Documentation

FastAPI auto-generates interactive API docs:

- **Swagger UI**: `http://localhost:8100/docs`
- **ReDoc**: `http://localhost:8100/redoc`
