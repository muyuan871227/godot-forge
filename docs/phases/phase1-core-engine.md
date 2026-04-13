# Phase 1 — 核心引擎构建 (预计 3 个月)

## 概述
将 Phase 0 的骨架扩展为功能完整的核心引擎：150+ MCP 工具、完整编辑器插件、基础 AI 代码生成。

---

## Task 1.1 — MCP Server 工具扩展至 150+

在 `packages/mcp-server/src/tools/` 下按类别创建工具文件。

### 1.1.1 项目管理工具 (`project.ts` — 8 个)

```typescript
// get_project_info, list_scenes, list_scripts, list_resources,
// get_project_settings, set_project_setting, rescan_filesystem,
// get_godot_version
export function registerProjectTools(godot: GodotConnection): RegisteredTool[] {
  return [
    {
      definition: {
        name: "list_scenes",
        description: "列出项目中所有场景文件 (.tscn/.scn)",
        inputSchema: {
          type: "object",
          properties: {
            directory: { type: "string", description: "搜索目录 (默认 res://)" }
          }
        }
      },
      handler: async (args) => godot.send("list_scenes", args),
    },
    {
      definition: {
        name: "list_scripts",
        description: "列出项目中所有脚本文件 (.gd/.cs)",
        inputSchema: {
          type: "object",
          properties: {
            directory: { type: "string" },
            filter: { type: "string", description: "文件名过滤 (支持通配符)" }
          }
        }
      },
      handler: async (args) => godot.send("list_scripts", args),
    },
    {
      definition: {
        name: "get_project_settings",
        description: "获取项目设置",
        inputSchema: {
          type: "object",
          properties: {
            category: { type: "string", description: "设置类别 (如 application, rendering)" }
          }
        }
      },
      handler: async (args) => godot.send("get_project_settings", args),
    },
    // ... 其余工具按同样模式注册
  ];
}
```

### 1.1.2 场景操作工具 (`scene.ts` — 15 个)

```
create_scene, open_scene, save_scene, save_scene_as, close_scene,
get_scene_tree, get_scene_tree_flat, get_open_scenes, switch_scene,
duplicate_scene, instantiate_scene, pack_scene, unpack_scene,
get_scene_resources, reload_scene
```

### 1.1.3 节点 CRUD 工具 (`node.ts` — 20 个)

```
add_node, remove_node, duplicate_node, rename_node, reparent_node,
get_node_info, get_node_properties, set_node_property,
get_node_children, get_node_signals, connect_signal, disconnect_signal,
add_to_group, remove_from_group, get_groups,
get_class_list, get_class_properties, get_class_methods,
find_nodes_by_type, find_nodes_by_group
```

### 1.1.4 脚本工具 (`script.ts` — 12 个)

```
create_script, read_script, update_script, delete_script,
attach_script, detach_script, get_script_errors,
get_open_script, set_open_script,
search_in_scripts, replace_in_scripts, format_script
```

### 1.1.5 资源管理工具 (`resource.ts` — 10 个)

```
list_resources, load_resource, save_resource,
import_asset, get_import_settings, set_import_settings,
create_resource, duplicate_resource,
get_resource_dependencies, find_unused_resources
```

### 1.1.6 编辑器控制工具 (`editor.ts` — 8 个)

```
get_editor_state, take_screenshot, get_output_log,
get_debugger_output, clear_output,
select_node, get_selected_nodes,
undo, redo
```

### 1.1.7 调试工具 (`debug.ts` — 10 个)

```
run_project, stop_project, run_scene,
get_debug_output, get_errors, clear_errors,
set_breakpoint, remove_breakpoint,
game_eval (运行时执行 GDScript),
get_runtime_node_tree
```

### 1.1.8 物理系统 (`physics.ts` — 8 个)

```
set_collision_layer, set_collision_mask,
add_collision_shape, create_physics_body,
set_gravity, get_physics_settings,
add_raycast, configure_area
```

### 1.1.9 动画系统 (`animation.ts` — 10 个)

```
create_animation_player, add_animation,
add_animation_track, set_keyframe,
create_animation_tree, set_blend_parameter,
play_animation, stop_animation,
create_tween, configure_tween
```

### 1.1.10 音频系统 (`audio.ts` — 6 个)

```
add_audio_player, set_audio_stream,
add_audio_bus, configure_audio_effect,
play_audio, stop_audio
```

### 1.1.11 UI 工具 (`ui.ts` — 10 个)

```
create_ui_element, set_theme, set_style_override,
create_button, create_label, create_container,
set_anchor_preset, set_margin, set_size_flags,
create_ui_layout
```

### 1.1.12 渲染工具 (`rendering.ts` — 8 个)

```
set_environment, configure_camera,
add_light, set_material, create_shader,
set_canvas_layer, configure_viewport,
take_viewport_screenshot
```

### 1.1.13 输入模拟 (`input.ts` — 6 个)

```
add_input_action, remove_input_action,
get_input_map, set_input_map,
simulate_input, simulate_key_press
```

### 1.1.14 导航系统 (`navigation.ts` — 5 个)

```
create_navigation_region, bake_navigation,
create_navigation_agent, set_navigation_target,
get_navigation_path
```

### 1.1.15 网络工具 (`networking.ts` — 6 个)

```
create_multiplayer_spawner, create_multiplayer_synchronizer,
set_multiplayer_authority, configure_enet,
create_rpc_function, set_network_mode
```

**对应 Godot 端实现**：

每个 MCP 工具都需要在 `plugin.gd` 的 `_handle_method()` 中添加对应实现。
建议将实现拆分为多个 GDScript 文件：

```
addons/godot_forge/
  handlers/
    project_handler.gd
    scene_handler.gd
    node_handler.gd
    script_handler.gd
    resource_handler.gd
    editor_handler.gd
    debug_handler.gd
    physics_handler.gd
    animation_handler.gd
    audio_handler.gd
    ui_handler.gd
    rendering_handler.gd
    input_handler.gd
    navigation_handler.gd
    networking_handler.gd
```

每个 handler 是一个 `RefCounted` 类，由 `plugin.gd` 持有实例并路由调用。

**验收**：MCP Server `ListTools` 返回 150+ 工具定义

---

## Task 1.2 — Godot 编辑器插件完善

### 1.2.1 AI 对话面板 (`ui/ai_panel.gd`)

功能要求：
- 聊天式 UI（用户输入 + AI 回复）
- 代码块高亮渲染
- "应用到场景" 按钮（将 AI 生成的代码/节点直接应用）
- 生成历史记录
- 连接状态指示器

```gdscript
# 核心流程
func _on_send():
    var prompt = chat_input.text
    _add_user_message(prompt)
    chat_input.text = ""
    
    # 1. 收集项目上下文
    var context = _gather_context()
    
    # 2. 调用 AI 服务
    var request = {
        "prompt": prompt,
        "context": context.project_info,
        "scene_tree": context.scene_tree,
        "existing_scripts": context.scripts,
    }
    
    var http = HTTPRequest.new()
    add_child(http)
    http.request_completed.connect(_on_ai_response.bind(http))
    http.request(
        "http://localhost:8100/api/v1/codegen/generate",
        ["Content-Type: application/json"],
        HTTPClient.METHOD_POST,
        JSON.stringify(request)
    )

func _gather_context() -> Dictionary:
    var root = EditorInterface.get_edited_scene_root()
    return {
        "project_info": _get_project_info_string(),
        "scene_tree": JSON.stringify(_serialize_tree(root)) if root else "",
        "scripts": _get_open_scripts(),
    }

func _on_ai_response(result, code, headers, body, http):
    http.queue_free()
    if code != 200:
        _add_system_message("Error: HTTP %d" % code)
        return
    
    var data = JSON.parse_string(body.get_string_from_utf8())
    _add_ai_message(data.get("explanation", ""), data.get("files", []))

func _add_ai_message(explanation: String, files: Array):
    # 渲染说明
    chat_log.append_text("\n[color=cyan][b]AI:[/b][/color] %s\n" % explanation)
    
    # 渲染代码块 + 应用按钮
    for file_data in files:
        var path = file_data.get("path", "")
        var code = file_data.get("content", "")
        chat_log.append_text("\n[code]# %s[/code]\n" % path)
        chat_log.append_text("[code]%s[/code]\n" % code)
        
        # 创建"应用"按钮
        var btn = Button.new()
        btn.text = "Apply: %s" % path
        btn.pressed.connect(_apply_code.bind(path, code))
        chat_log.add_child(btn)

func _apply_code(path: String, code: String):
    # 写入文件
    DirAccess.make_dir_recursive_absolute(path.get_base_dir())
    var file = FileAccess.open(path, FileAccess.WRITE)
    file.store_string(code)
    file.close()
    EditorInterface.get_resource_filesystem().scan()
    _add_system_message("Applied: %s" % path)
```

### 1.2.2 AI 资产浏览器 (`ui/asset_browser.gd`)

功能要求：
- 显示 AI 生成的资产列表（图片/3D/音频）
- 预览面板（图片缩略图、3D 旋转预览、音频播放）
- 拖拽到场景功能
- 生成状态指示（排队/生成中/完成/失败）

### 1.2.3 设置对话框 (`ui/settings_dialog.gd`)

功能要求：
- AI 服务 URL 配置
- API Key 输入（密码模式）
- LLM 供应商选择
- 本地模型路径配置
- 连接测试按钮

**验收**：插件面板可发送提示、显示 AI 回复、应用代码到项目

---

## Task 1.3 — AI 代码生成增强

### 1.3.1 上下文感知代码生成

在 `ai-services/src/services/llm_service.py` 中增强上下文收集：

```python
async def generate_gdscript_with_context(
    prompt: str,
    project_context: dict,
) -> dict:
    """上下文感知的 GDScript 生成"""
    
    # 构建增强 system prompt
    enhanced_system = GDSCRIPT_SYSTEM_PROMPT + f"""

Current Project Context:
- Project Name: {project_context.get('name', 'Unknown')}
- Godot Version: {project_context.get('godot_version', '4.4')}
- Main Scene: {project_context.get('main_scene', 'N/A')}

Scene Tree:
{project_context.get('scene_tree', 'No scene open')}

Existing Scripts in Project:
{_format_script_list(project_context.get('scripts', []))}

Available Autoloads:
{_format_autoloads(project_context.get('autoloads', []))}

Input Map Actions:
{_format_input_map(project_context.get('input_map', {}))}

IMPORTANT: Reference existing nodes and scripts by their actual paths.
Use existing autoloads rather than creating new ones when possible.
Follow the project's existing naming conventions and code style.
"""
    
    return await _generate_with_system(enhanced_system, prompt)
```

### 1.3.2 多文件生成支持

```python
async def generate_game_feature(
    feature_description: str,
    project_context: dict,
) -> dict:
    """生成完整游戏特性（多场景+多脚本+资源）"""
    
    prompt = f"""Generate a complete implementation for this game feature:
{feature_description}

Return ALL necessary files. For each file, use this format:
### FILE: res://path/to/file.gd
```gdscript
<code>
```

### FILE: res://scenes/my_scene.tscn
```
<tscn content or description>
```

Include:
1. All GDScript files needed
2. Scene descriptions (what nodes to create)
3. Any resource configurations
4. Integration instructions for existing scenes
"""
    
    result = await generate_gdscript_with_context(prompt, project_context)
    
    # 解析多文件输出
    files = _parse_multi_file_response(result["code"])
    return {
        "files": files,
        "explanation": result["explanation"],
        "integration_steps": _extract_integration_steps(result["explanation"]),
    }
```

### 1.3.3 错误修复循环

```python
async def auto_fix_loop(
    script_path: str,
    script_content: str,
    errors: list[str],
    max_iterations: int = 3,
) -> dict:
    """自动修复循环：检测错误 → 修复 → 再检测"""
    
    history = []
    current_content = script_content
    
    for i in range(max_iterations):
        if not errors:
            break
        
        fix_prompt = f"""Fix these errors in {script_path}:

Errors:
{chr(10).join(f'- {e}' for e in errors)}

Current code:
```gdscript
{current_content}
```

Return the COMPLETE fixed script."""
        
        result = await generate_gdscript(fix_prompt)
        current_content = result["code"]
        history.append({
            "iteration": i + 1,
            "errors_fixed": errors,
            "new_code": current_content,
        })
        
        # TODO: 通过 MCP 写入并获取新错误
        errors = []  # Placeholder
    
    return {
        "final_code": current_content,
        "iterations": len(history),
        "history": history,
        "all_fixed": len(errors) == 0,
    }
```

**验收**：
- 代码生成包含项目上下文（引用真实节点路径）
- 可生成多文件特性（如完整的 Player Controller + UI）
- 错误修复循环可检测并修复基础 GDScript 错误

---

## Task 1.4 — CLI 工具

创建 `packages/cli/src/index.ts`：

```typescript
#!/usr/bin/env node
import { Command } from "commander";
import { initCommand } from "./commands/init.js";
import { generateCommand } from "./commands/generate.js";
import { serveCommand } from "./commands/serve.js";

const program = new Command();

program
  .name("godot-forge")
  .description("AI-powered Godot game creation platform")
  .version("0.1.0");

program
  .command("init")
  .description("Initialize a new GodotForge project")
  .option("-t, --template <template>", "Project template", "2d-platformer")
  .option("-n, --name <name>", "Project name")
  .action(initCommand);

program
  .command("generate")
  .description("Generate game content from natural language")
  .argument("<prompt>", "What to generate")
  .option("--type <type>", "Generation type: code|scene|asset|full", "code")
  .option("--apply", "Auto-apply to project", false)
  .action(generateCommand);

program
  .command("serve")
  .description("Start all GodotForge services")
  .option("-p, --port <port>", "AI services port", "8100")
  .option("--mcp-port <port>", "MCP server port", "6505")
  .action(serveCommand);

program.parse();
```

创建 `packages/cli/src/commands/generate.ts`：

```typescript
import fetch from "node-fetch";

export async function generateCommand(prompt: string, options: any) {
  const apiUrl = process.env.GODOTFORGE_API_URL || "http://localhost:8100";
  
  console.log(`\n🎮 GodotForge — Generating ${options.type}...\n`);
  console.log(`Prompt: "${prompt}"\n`);
  
  const endpoint = {
    code: "/api/v1/codegen/generate",
    scene: "/api/v1/codegen/generate",
    asset: "/api/v1/imagegen/generate",
    full: "/api/v1/codegen/generate",
  }[options.type] || "/api/v1/codegen/generate";
  
  try {
    const response = await fetch(`${apiUrl}${endpoint}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt, godot_version: "4.4" }),
    });
    
    const data = await response.json() as any;
    
    if (data.explanation) {
      console.log("📝 Explanation:");
      console.log(data.explanation);
    }
    
    if (data.files?.length) {
      console.log(`\n📁 Generated ${data.files.length} file(s):\n`);
      for (const file of data.files) {
        console.log(`--- ${file.path} ---`);
        console.log(file.content);
        console.log();
        
        if (options.apply) {
          // 写入到当前 Godot 项目
          const fs = await import("fs");
          const path = await import("path");
          const fullPath = path.join(process.cwd(), file.path.replace("res://", ""));
          fs.mkdirSync(path.dirname(fullPath), { recursive: true });
          fs.writeFileSync(fullPath, file.content);
          console.log(`✅ Applied: ${fullPath}`);
        }
      }
    }
  } catch (error: any) {
    console.error(`❌ Error: ${error.message}`);
    process.exit(1);
  }
}
```

**验收**：`npx godot-forge generate "create a coin pickup with animation and score"` 输出有效代码

---

## Task 1.5 — 基础 2D 图像生成

### 在 `ai-services` 中添加图像生成路由

创建 `src/routers/imagegen.py`：

```python
"""图像生成路由 — 2D 精灵/背景/UI"""
from fastapi import APIRouter
from pydantic import BaseModel
from ..services.image_service import generate_image

router = APIRouter()

class ImageGenRequest(BaseModel):
    prompt: str
    style: str = "pixel_art"  # pixel_art | hand_drawn | anime | realistic
    width: int = 512
    height: int = 512
    sprite_sheet: bool = False
    sprite_frames: int = 4
    transparent_bg: bool = True
    negative_prompt: str = ""

class ImageGenResponse(BaseModel):
    image_base64: str
    image_path: str
    metadata: dict

@router.post("/generate", response_model=ImageGenResponse)
async def generate(req: ImageGenRequest):
    return await generate_image(
        prompt=req.prompt,
        style=req.style,
        width=req.width,
        height=req.height,
        sprite_sheet=req.sprite_sheet,
        sprite_frames=req.sprite_frames,
        transparent_bg=req.transparent_bg,
        negative_prompt=req.negative_prompt,
    )

@router.post("/sprite-sheet")
async def generate_sprite_sheet(
    character_description: str,
    animations: list[str] = ["idle", "run", "jump"],
    frame_count: int = 4,
    style: str = "pixel_art",
):
    """生成角色精灵图集"""
    results = {}
    for anim in animations:
        prompt = f"{character_description}, {anim} animation, sprite sheet, {frame_count} frames, game asset"
        result = await generate_image(
            prompt=prompt,
            style=style,
            width=frame_count * 64,
            height=64,
            sprite_sheet=True,
            sprite_frames=frame_count,
        )
        results[anim] = result
    return results

@router.post("/tilemap")
async def generate_tilemap(
    theme: str,
    tile_size: int = 16,
    tile_count: int = 16,
    style: str = "pixel_art",
):
    """生成 Tilemap 贴图集"""
    prompt = f"tilemap tileset, {theme} theme, {tile_size}x{tile_size} tiles, seamless, top-down view, game asset, {tile_count} tiles grid"
    return await generate_image(
        prompt=prompt,
        style=style,
        width=tile_size * int(tile_count**0.5),
        height=tile_size * int(tile_count**0.5),
    )
```

创建 `src/services/image_service.py`：

```python
"""图像生成服务 — ComfyUI / Replicate / 本地 SD"""
import base64
import httpx
import uuid
from pathlib import Path
from ..config import settings

STYLE_PROMPTS = {
    "pixel_art": "pixel art style, 16-bit, retro game, clean pixels, ",
    "hand_drawn": "hand-drawn illustration, colorful, cartoon style, ",
    "anime": "anime style, cel shading, vibrant colors, ",
    "realistic": "photorealistic, detailed textures, PBR material, ",
}

NEGATIVE_DEFAULTS = "blurry, low quality, watermark, text, signature, deformed"

async def generate_image(
    prompt: str,
    style: str = "pixel_art",
    width: int = 512,
    height: int = 512,
    sprite_sheet: bool = False,
    sprite_frames: int = 4,
    transparent_bg: bool = True,
    negative_prompt: str = "",
) -> dict:
    """统一图像生成接口"""
    
    # 增强提示词
    style_prefix = STYLE_PROMPTS.get(style, "")
    full_prompt = style_prefix + prompt
    if transparent_bg:
        full_prompt += ", transparent background, isolated on alpha"
    if sprite_sheet:
        full_prompt += f", sprite sheet with {sprite_frames} frames, horizontal strip"
    
    neg = negative_prompt or NEGATIVE_DEFAULTS
    
    if settings.image_provider == "comfyui":
        return await _generate_comfyui(full_prompt, neg, width, height)
    elif settings.image_provider == "replicate":
        return await _generate_replicate(full_prompt, neg, width, height)
    else:
        return {"error": f"Unknown image provider: {settings.image_provider}"}

async def _generate_comfyui(prompt: str, negative: str, width: int, height: int) -> dict:
    """通过 ComfyUI API 生成图像"""
    workflow = {
        "3": {
            "class_type": "KSampler",
            "inputs": {
                "seed": -1, "steps": 20, "cfg": 7.5,
                "sampler_name": "euler", "scheduler": "normal",
                "denoise": 1.0,
                "model": ["4", 0], "positive": ["6", 0],
                "negative": ["7", 0], "latent_image": ["5", 0],
            }
        },
        "4": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "sd_xl_base_1.0.safetensors"}},
        "5": {"class_type": "EmptyLatentImage", "inputs": {"width": width, "height": height, "batch_size": 1}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["4", 1]}},
        "7": {"class_type": "CLIPTextEncode", "inputs": {"text": negative, "clip": ["4", 1]}},
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
        "9": {"class_type": "SaveImage", "inputs": {"filename_prefix": "godotforge", "images": ["8", 0]}},
    }
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        # 提交工作流
        resp = await client.post(f"{settings.comfyui_url}/prompt", json={"prompt": workflow})
        prompt_id = resp.json()["prompt_id"]
        
        # 轮询结果
        while True:
            import asyncio
            await asyncio.sleep(1)
            history = await client.get(f"{settings.comfyui_url}/history/{prompt_id}")
            data = history.json()
            if prompt_id in data:
                outputs = data[prompt_id]["outputs"]
                if "9" in outputs:
                    image_data = outputs["9"]["images"][0]
                    image_url = f"{settings.comfyui_url}/view?filename={image_data['filename']}"
                    img_resp = await client.get(image_url)
                    img_b64 = base64.b64encode(img_resp.content).decode()
                    
                    # 保存到项目
                    save_path = f"res://assets/generated/{uuid.uuid4().hex[:8]}.png"
                    
                    return {
                        "image_base64": img_b64,
                        "image_path": save_path,
                        "metadata": {"prompt": prompt, "width": width, "height": height},
                    }

async def _generate_replicate(prompt: str, negative: str, width: int, height: int) -> dict:
    """通过 Replicate API 生成图像 (备选)"""
    # Replicate API 实现
    pass
```

**验收**：`/api/v1/imagegen/generate` 可返回 base64 图像数据

---

## Task 1.6 — 基础音效生成

创建 `src/routers/audiogen.py`：

```python
"""音频生成路由 — TTS/音效/BGM"""
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

class SFXRequest(BaseModel):
    description: str  # "coin pickup sound", "explosion", "footstep on grass"
    duration: float = 1.0
    format: str = "wav"

class BGMRequest(BaseModel):
    description: str  # "upbeat chiptune adventure theme"
    duration: float = 30.0
    loop: bool = True

class TTSRequest(BaseModel):
    text: str
    voice: str = "default"
    language: str = "en"

@router.post("/sfx")
async def generate_sfx(req: SFXRequest):
    from ..services.audio_service import generate_sound_effect
    return await generate_sound_effect(req.description, req.duration, req.format)

@router.post("/bgm")
async def generate_bgm(req: BGMRequest):
    from ..services.audio_service import generate_background_music
    return await generate_background_music(req.description, req.duration, req.loop)

@router.post("/tts")
async def generate_tts(req: TTSRequest):
    from ..services.audio_service import generate_speech
    return await generate_speech(req.text, req.voice, req.language)
```

创建 `src/services/audio_service.py`：

```python
"""音频生成服务 — Bark + MusicGen"""
import base64
import uuid
from pathlib import Path
from ..config import settings

async def generate_sound_effect(description: str, duration: float, format: str) -> dict:
    """使用 Bark 生成音效"""
    if settings.audio_provider == "bark":
        from transformers import AutoProcessor, BarkModel
        import scipy
        import numpy as np
        
        processor = AutoProcessor.from_pretrained("suno/bark-small")
        model = BarkModel.from_pretrained("suno/bark-small")
        
        # Bark 音效提示格式
        prompt = f"[sound effect] {description}"
        inputs = processor(prompt, return_tensors="pt")
        audio = model.generate(**inputs, do_sample=True)
        audio_np = audio.cpu().numpy().squeeze()
        
        # 保存
        filename = f"sfx_{uuid.uuid4().hex[:8]}.{format}"
        save_path = f"/tmp/godotforge/{filename}"
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        scipy.io.wavfile.write(save_path, 24000, audio_np)
        
        with open(save_path, "rb") as f:
            audio_b64 = base64.b64encode(f.read()).decode()
        
        return {
            "audio_base64": audio_b64,
            "filename": filename,
            "duration": len(audio_np) / 24000,
            "sample_rate": 24000,
        }
    
    return {"error": f"Unknown audio provider: {settings.audio_provider}"}

async def generate_background_music(description: str, duration: float, loop: bool) -> dict:
    """使用 MusicGen 生成背景音乐"""
    from audiocraft.models import MusicGen
    import scipy
    import numpy as np
    
    model = MusicGen.get_pretrained("facebook/musicgen-small")
    model.set_generation_params(duration=min(duration, 30))
    
    descriptions = [f"game music, {description}"]
    wav = model.generate(descriptions)
    audio_np = wav[0, 0].cpu().numpy()
    
    filename = f"bgm_{uuid.uuid4().hex[:8]}.wav"
    save_path = f"/tmp/godotforge/{filename}"
    Path(save_path).parent.mkdir(parents=True, exist_ok=True)
    scipy.io.wavfile.write(save_path, 32000, audio_np)
    
    with open(save_path, "rb") as f:
        audio_b64 = base64.b64encode(f.read()).decode()
    
    return {
        "audio_base64": audio_b64,
        "filename": filename,
        "duration": len(audio_np) / 32000,
        "loop": loop,
    }

async def generate_speech(text: str, voice: str, language: str) -> dict:
    """使用 Bark 生成语音 (NPC 对话)"""
    from transformers import AutoProcessor, BarkModel
    import scipy
    
    processor = AutoProcessor.from_pretrained("suno/bark-small")
    model = BarkModel.from_pretrained("suno/bark-small")
    
    voice_preset = f"v2/{language}_speaker_6"
    inputs = processor(text, voice_preset=voice_preset, return_tensors="pt")
    audio = model.generate(**inputs, do_sample=True)
    audio_np = audio.cpu().numpy().squeeze()
    
    filename = f"tts_{uuid.uuid4().hex[:8]}.wav"
    save_path = f"/tmp/godotforge/{filename}"
    Path(save_path).parent.mkdir(parents=True, exist_ok=True)
    scipy.io.wavfile.write(save_path, 24000, audio_np)
    
    with open(save_path, "rb") as f:
        audio_b64 = base64.b64encode(f.read()).decode()
    
    return {"audio_base64": audio_b64, "filename": filename, "text": text}
```

**验收**：`/api/v1/audiogen/sfx` 返回有效音频数据

---

## Task 1.7 — 集成测试

创建 `tests/integration/test_e2e_flow.py`：

```python
"""端到端集成测试"""
import httpx
import pytest

API_URL = "http://localhost:8100"

@pytest.mark.asyncio
async def test_code_generation():
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{API_URL}/api/v1/codegen/generate", json={
            "prompt": "Create a simple player movement script for a 2D platformer",
            "godot_version": "4.4",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "code" in data
        assert "extends" in data["code"]
        assert len(data["files"]) > 0

@pytest.mark.asyncio
async def test_image_generation():
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(f"{API_URL}/api/v1/imagegen/generate", json={
            "prompt": "a cute slime monster",
            "style": "pixel_art",
            "width": 64,
            "height": 64,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "image_base64" in data

@pytest.mark.asyncio
async def test_health():
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{API_URL}/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
```

**验收**：`pytest tests/integration/ -v` 全部通过

---

## Phase 1 完成标志

- [ ] MCP Server 注册 150+ 工具，全部有对应 Godot 端实现
- [ ] 编辑器插件：AI 对话面板可收发消息并应用代码
- [ ] AI 服务：代码生成支持上下文感知 + 多文件输出
- [ ] CLI：`godot-forge generate` 命令可用
- [ ] 图像生成 API 可返回有效图像
- [ ] 音频生成 API 可返回有效音频
- [ ] 集成测试全部通过
- [ ] 文档更新：所有 MCP 工具的 API 参考

**下一步**：执行 `docs/phases/phase2-ai-pipeline.md`
