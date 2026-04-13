# Phase 0 — 项目初始化与验证 (预计 2 周)

## 前置条件

```bash
# 确认环境
node --version    # >= 20.x
python3 --version # >= 3.10
godot --version   # >= 4.4 (需要在 PATH 中可用)
```

---

## Task 0.1 — Monorepo 初始化

```bash
# 创建项目根目录
mkdir godot-forge && cd godot-forge
git init

# 初始化 monorepo
npm init -y
npm install -D turbo typescript @types/node

# 创建 workspace 配置
cat > package.json << 'EOF'
{
  "name": "godot-forge",
  "version": "0.1.0",
  "private": true,
  "workspaces": [
    "packages/*"
  ],
  "scripts": {
    "dev": "turbo run dev",
    "build": "turbo run build",
    "test": "turbo run test",
    "lint": "turbo run lint"
  },
  "devDependencies": {
    "turbo": "^2.0.0",
    "typescript": "^5.5.0"
  }
}
EOF

cat > turbo.json << 'EOF'
{
  "$schema": "https://turbo.build/schema.json",
  "pipeline": {
    "build": { "dependsOn": ["^build"], "outputs": ["dist/**", "build/**"] },
    "dev": { "cache": false, "persistent": true },
    "test": { "dependsOn": ["build"] },
    "lint": {}
  }
}
EOF

# 创建目录结构
mkdir -p packages/{mcp-server,ai-services,godot-plugin,web-ui,cli}
mkdir -p docker templates docs/{phases,modules,api} tests/{mcp-server,ai-services,integration,e2e}
```

**验收**：`npm install` 无报错，`npx turbo --version` 正常输出

---

## Task 0.2 — MCP Server 骨架

```bash
cd packages/mcp-server
npm init -y

# 安装核心依赖
npm install @modelcontextprotocol/sdk zod ws
npm install -D typescript @types/node @types/ws tsx vitest

# TypeScript 配置
cat > tsconfig.json << 'EOF'
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "NodeNext",
    "moduleResolution": "NodeNext",
    "outDir": "./build",
    "rootDir": "./src",
    "strict": true,
    "esModuleInterop": true,
    "declaration": true,
    "sourceMap": true,
    "skipLibCheck": true
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "build"]
}
EOF
```

**创建 `src/index.ts`**：

```typescript
#!/usr/bin/env node
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { CallToolRequestSchema, ListToolsRequestSchema } from "@modelcontextprotocol/sdk/types.js";
import { GodotConnection } from "./transport/websocket.js";
import { registerAllTools } from "./tools/index.js";

const SERVER_NAME = "godot-forge-mcp";
const SERVER_VERSION = "0.1.0";

async function main() {
  const server = new Server(
    { name: SERVER_NAME, version: SERVER_VERSION },
    { capabilities: { tools: {} } }
  );

  // Godot WebSocket 连接
  const godot = new GodotConnection({
    port: parseInt(process.env.GODOT_MCP_PORT || "6505"),
    reconnect: true,
  });

  // 注册所有工具
  const tools = registerAllTools(godot);

  server.setRequestHandler(ListToolsRequestSchema, async () => ({
    tools: tools.map(t => t.definition),
  }));

  server.setRequestHandler(CallToolRequestSchema, async (request) => {
    const tool = tools.find(t => t.definition.name === request.params.name);
    if (!tool) {
      return { content: [{ type: "text", text: `Unknown tool: ${request.params.name}` }], isError: true };
    }
    try {
      const result = await tool.handler(request.params.arguments ?? {});
      return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
    } catch (error: any) {
      return { content: [{ type: "text", text: `Error: ${error.message}` }], isError: true };
    }
  });

  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error(`${SERVER_NAME} v${SERVER_VERSION} running on stdio`);
}

main().catch(console.error);
```

**创建 `src/transport/websocket.ts`**：

```typescript
import WebSocket from "ws";

export interface GodotConnectionOptions {
  host?: string;
  port: number;
  reconnect?: boolean;
  maxRetries?: number;
}

export class GodotConnection {
  private ws: WebSocket | null = null;
  private options: Required<GodotConnectionOptions>;
  private retryCount = 0;
  private pendingRequests = new Map<number, {
    resolve: (value: any) => void;
    reject: (reason: any) => void;
    timeout: NodeJS.Timeout;
  }>();
  private requestId = 0;
  private connected = false;

  constructor(options: GodotConnectionOptions) {
    this.options = {
      host: options.host || "127.0.0.1",
      port: options.port,
      reconnect: options.reconnect ?? true,
      maxRetries: options.maxRetries ?? 10,
    };
  }

  async connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      const url = `ws://${this.options.host}:${this.options.port}`;
      this.ws = new WebSocket(url);

      this.ws.on("open", () => {
        this.connected = true;
        this.retryCount = 0;
        console.error(`Connected to Godot at ${url}`);
        resolve();
      });

      this.ws.on("message", (data) => {
        try {
          const msg = JSON.parse(data.toString());
          if (msg.id && this.pendingRequests.has(msg.id)) {
            const pending = this.pendingRequests.get(msg.id)!;
            clearTimeout(pending.timeout);
            this.pendingRequests.delete(msg.id);
            if (msg.error) {
              pending.reject(new Error(msg.error.message || "Godot error"));
            } else {
              pending.resolve(msg.result);
            }
          }
        } catch (e) {
          console.error("Failed to parse Godot message:", e);
        }
      });

      this.ws.on("close", () => {
        this.connected = false;
        if (this.options.reconnect && this.retryCount < this.options.maxRetries) {
          const delay = Math.min(1000 * Math.pow(2, this.retryCount), 60000);
          this.retryCount++;
          console.error(`Reconnecting in ${delay}ms (attempt ${this.retryCount})...`);
          setTimeout(() => this.connect().catch(() => {}), delay);
        }
      });

      this.ws.on("error", (err) => {
        if (!this.connected) reject(err);
      });
    });
  }

  async send(method: string, params: Record<string, any> = {}): Promise<any> {
    if (!this.ws || !this.connected) {
      await this.connect();
    }

    return new Promise((resolve, reject) => {
      const id = ++this.requestId;
      const timeout = setTimeout(() => {
        this.pendingRequests.delete(id);
        reject(new Error(`Request ${method} timed out`));
      }, 30000);

      this.pendingRequests.set(id, { resolve, reject, timeout });

      const message = JSON.stringify({
        jsonrpc: "2.0",
        id,
        method,
        params,
      });

      this.ws!.send(message);
    });
  }

  get isConnected(): boolean {
    return this.connected;
  }

  disconnect(): void {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
      this.connected = false;
    }
  }
}
```

**创建 `src/tools/index.ts`** — 工具注册框架：

```typescript
import { z } from "zod";
import { GodotConnection } from "../transport/websocket.js";

export interface ToolDefinition {
  name: string;
  description: string;
  inputSchema: Record<string, any>;
}

export interface RegisteredTool {
  definition: ToolDefinition;
  handler: (args: Record<string, any>) => Promise<any>;
}

// ============================================
// Phase 0: 基础工具 (10 个核心工具)
// ============================================

export function registerAllTools(godot: GodotConnection): RegisteredTool[] {
  const tools: RegisteredTool[] = [];

  // --- 项目工具 ---
  tools.push({
    definition: {
      name: "get_project_info",
      description: "获取当前 Godot 项目的基本信息",
      inputSchema: { type: "object", properties: {}, required: [] },
    },
    handler: async () => godot.send("get_project_info"),
  });

  tools.push({
    definition: {
      name: "get_scene_tree",
      description: "获取当前场景的节点树结构",
      inputSchema: { type: "object", properties: {}, required: [] },
    },
    handler: async () => godot.send("get_scene_tree"),
  });

  // --- 场景工具 ---
  tools.push({
    definition: {
      name: "create_scene",
      description: "创建一个新场景",
      inputSchema: {
        type: "object",
        properties: {
          name: { type: "string", description: "场景名称" },
          root_type: { type: "string", description: "根节点类型 (Node2D/Node3D/Control)" },
        },
        required: ["name", "root_type"],
      },
    },
    handler: async (args) => godot.send("create_scene", args),
  });

  tools.push({
    definition: {
      name: "save_scene",
      description: "保存当前场景",
      inputSchema: {
        type: "object",
        properties: {
          path: { type: "string", description: "保存路径 (res://...)" },
        },
        required: [],
      },
    },
    handler: async (args) => godot.send("save_scene", args),
  });

  // --- 节点工具 ---
  tools.push({
    definition: {
      name: "add_node",
      description: "向场景树添加节点",
      inputSchema: {
        type: "object",
        properties: {
          parent_path: { type: "string", description: "父节点路径" },
          node_type: { type: "string", description: "节点类型 (如 Sprite2D, CharacterBody2D)" },
          node_name: { type: "string", description: "节点名称" },
          properties: { type: "object", description: "节点属性键值对" },
        },
        required: ["parent_path", "node_type", "node_name"],
      },
    },
    handler: async (args) => godot.send("add_node", args),
  });

  tools.push({
    definition: {
      name: "set_node_property",
      description: "设置节点属性",
      inputSchema: {
        type: "object",
        properties: {
          node_path: { type: "string" },
          property: { type: "string" },
          value: { description: "属性值" },
        },
        required: ["node_path", "property", "value"],
      },
    },
    handler: async (args) => godot.send("set_node_property", args),
  });

  // --- 脚本工具 ---
  tools.push({
    definition: {
      name: "create_script",
      description: "创建并附加 GDScript 到节点",
      inputSchema: {
        type: "object",
        properties: {
          node_path: { type: "string", description: "目标节点路径" },
          script_path: { type: "string", description: "脚本保存路径" },
          content: { type: "string", description: "GDScript 代码内容" },
        },
        required: ["node_path", "script_path", "content"],
      },
    },
    handler: async (args) => godot.send("create_script", args),
  });

  tools.push({
    definition: {
      name: "get_script_errors",
      description: "获取当前项目的脚本错误",
      inputSchema: { type: "object", properties: {}, required: [] },
    },
    handler: async () => godot.send("get_script_errors"),
  });

  // --- 运行工具 ---
  tools.push({
    definition: {
      name: "run_project",
      description: "运行当前项目",
      inputSchema: {
        type: "object",
        properties: {
          scene: { type: "string", description: "指定运行的场景路径 (可选)" },
        },
        required: [],
      },
    },
    handler: async (args) => godot.send("run_project", args),
  });

  tools.push({
    definition: {
      name: "stop_project",
      description: "停止正在运行的项目",
      inputSchema: { type: "object", properties: {}, required: [] },
    },
    handler: async () => godot.send("stop_project"),
  });

  return tools;
}
```

更新 `package.json`：
```json
{
  "name": "@godot-forge/mcp-server",
  "version": "0.1.0",
  "type": "module",
  "bin": { "godot-forge-mcp": "./build/index.js" },
  "scripts": {
    "build": "tsc",
    "dev": "tsx watch src/index.ts",
    "test": "vitest run",
    "lint": "tsc --noEmit"
  }
}
```

**验收**：`npm run build` 编译成功，`node build/index.js` 启动无报错（等待连接）

---

## Task 0.3 — Godot 编辑器插件骨架

创建 `packages/godot-plugin/addons/godot_forge/plugin.cfg`：

```ini
[plugin]
name="GodotForge"
description="AI-powered game creation platform"
author="GodotForge"
version="0.1.0"
script="plugin.gd"
```

创建 `packages/godot-plugin/addons/godot_forge/plugin.gd`：

```gdscript
@tool
extends EditorPlugin

const AI_PANEL = preload("res://addons/godot_forge/ui/ai_panel.tscn")

var ai_panel_instance: Control
var mcp_server: WebSocketServer
var ws_peer: WebSocketPeer
var port: int = 6505

func _enter_tree():
    # 添加 AI 面板到底部
    ai_panel_instance = AI_PANEL.instantiate()
    add_control_to_bottom_panel(ai_panel_instance, "AI Assistant")
    
    # 启动 WebSocket 服务器
    _start_websocket_server()
    print("[GodotForge] Plugin activated on port %d" % port)

func _exit_tree():
    if ai_panel_instance:
        remove_control_from_bottom_panel(ai_panel_instance)
        ai_panel_instance.queue_free()
    _stop_websocket_server()
    print("[GodotForge] Plugin deactivated")

func _start_websocket_server():
    mcp_server = WebSocketServer.new()
    mcp_server.client_connected.connect(_on_client_connected)
    mcp_server.client_disconnected.connect(_on_client_disconnected)
    mcp_server.message_received.connect(_on_message_received)
    var err = mcp_server.listen(port)
    if err != OK:
        push_error("[GodotForge] Failed to start WebSocket server on port %d" % port)
    else:
        print("[GodotForge] WebSocket server listening on port %d" % port)

func _stop_websocket_server():
    if mcp_server:
        mcp_server.stop()

func _process(_delta):
    if mcp_server:
        mcp_server.poll()

func _on_client_connected(peer_id: int, _protocol: String):
    print("[GodotForge] MCP client connected: %d" % peer_id)
    if ai_panel_instance and ai_panel_instance.has_method("set_connection_status"):
        ai_panel_instance.set_connection_status(true)

func _on_client_disconnected(peer_id: int, _was_clean: bool):
    print("[GodotForge] MCP client disconnected: %d" % peer_id)
    if ai_panel_instance and ai_panel_instance.has_method("set_connection_status"):
        ai_panel_instance.set_connection_status(false)

func _on_message_received(peer_id: int, message: String):
    var json = JSON.new()
    var err = json.parse(message)
    if err != OK:
        _send_error(peer_id, -1, "Invalid JSON")
        return
    
    var request = json.data
    if not request is Dictionary:
        _send_error(peer_id, -1, "Invalid request format")
        return
    
    var id = request.get("id", -1)
    var method = request.get("method", "")
    var params = request.get("params", {})
    
    var result = _handle_method(method, params)
    _send_response(peer_id, id, result)

func _handle_method(method: String, params: Dictionary) -> Dictionary:
    match method:
        "get_project_info":
            return _get_project_info()
        "get_scene_tree":
            return _get_scene_tree()
        "create_scene":
            return _create_scene(params)
        "add_node":
            return _add_node(params)
        "set_node_property":
            return _set_node_property(params)
        "create_script":
            return _create_script(params)
        "save_scene":
            return _save_scene(params)
        "get_script_errors":
            return _get_script_errors()
        "run_project":
            return _run_project(params)
        "stop_project":
            return _stop_project()
        _:
            return {"error": "Unknown method: %s" % method}

# ============================================
# 方法实现
# ============================================

func _get_project_info() -> Dictionary:
    return {
        "name": ProjectSettings.get_setting("application/config/name", "Untitled"),
        "godot_version": Engine.get_version_info(),
        "project_path": ProjectSettings.globalize_path("res://"),
        "main_scene": ProjectSettings.get_setting("application/run/main_scene", ""),
    }

func _get_scene_tree() -> Dictionary:
    var root = get_editor_interface().get_edited_scene_root()
    if not root:
        return {"error": "No scene open"}
    return {"tree": _serialize_node(root)}

func _serialize_node(node: Node) -> Dictionary:
    var data := {
        "name": node.name,
        "type": node.get_class(),
        "path": str(node.get_path()),
        "children": []
    }
    for child in node.get_children():
        data["children"].append(_serialize_node(child))
    return data

func _create_scene(params: Dictionary) -> Dictionary:
    var root_type = params.get("root_type", "Node2D")
    var scene_name = params.get("name", "new_scene")
    
    var root = ClassDB.instantiate(root_type)
    if not root:
        return {"error": "Invalid node type: %s" % root_type}
    root.name = scene_name
    
    var packed = PackedScene.new()
    packed.pack(root)
    var path = "res://scenes/%s.tscn" % scene_name
    DirAccess.make_dir_recursive_absolute("res://scenes")
    ResourceSaver.save(packed, path)
    root.queue_free()
    
    get_editor_interface().open_scene_from_path(path)
    return {"success": true, "path": path}

func _add_node(params: Dictionary) -> Dictionary:
    var root = get_editor_interface().get_edited_scene_root()
    if not root:
        return {"error": "No scene open"}
    
    var parent_path = params.get("parent_path", ".")
    var parent = root.get_node_or_null(parent_path) if parent_path != "." else root
    if not parent:
        return {"error": "Parent not found: %s" % parent_path}
    
    var node_type = params.get("node_type", "Node")
    var node = ClassDB.instantiate(node_type)
    if not node:
        return {"error": "Invalid type: %s" % node_type}
    
    node.name = params.get("node_name", node_type)
    parent.add_child(node)
    node.owner = root
    
    # 设置属性
    var props = params.get("properties", {})
    for key in props:
        if node.has_method("set"):
            node.set(key, props[key])
    
    return {"success": true, "path": str(node.get_path())}

func _set_node_property(params: Dictionary) -> Dictionary:
    var root = get_editor_interface().get_edited_scene_root()
    if not root:
        return {"error": "No scene open"}
    var node = root.get_node_or_null(params.get("node_path", ""))
    if not node:
        return {"error": "Node not found"}
    node.set(params.get("property", ""), params.get("value"))
    return {"success": true}

func _create_script(params: Dictionary) -> Dictionary:
    var root = get_editor_interface().get_edited_scene_root()
    if not root:
        return {"error": "No scene open"}
    var node = root.get_node_or_null(params.get("node_path", ""))
    if not node:
        return {"error": "Node not found"}
    
    var script_path = params.get("script_path", "res://scripts/new_script.gd")
    var content = params.get("content", "extends Node\n")
    
    DirAccess.make_dir_recursive_absolute(script_path.get_base_dir())
    var file = FileAccess.open(script_path, FileAccess.WRITE)
    file.store_string(content)
    file.close()
    
    var script = load(script_path)
    node.set_script(script)
    return {"success": true, "path": script_path}

func _save_scene(params: Dictionary) -> Dictionary:
    var root = get_editor_interface().get_edited_scene_root()
    if not root:
        return {"error": "No scene open"}
    get_editor_interface().save_scene()
    return {"success": true}

func _get_script_errors() -> Dictionary:
    # 读取 Godot 编辑器的错误输出
    return {"errors": [], "warnings": []}

func _run_project(params: Dictionary) -> Dictionary:
    var scene = params.get("scene", "")
    if scene:
        get_editor_interface().play_custom_scene(scene)
    else:
        get_editor_interface().play_main_scene()
    return {"success": true}

func _stop_project() -> Dictionary:
    get_editor_interface().stop_playing_scene()
    return {"success": true}

# ============================================
# WebSocket 通信
# ============================================

func _send_response(peer_id: int, id: int, result: Dictionary):
    var response = {
        "jsonrpc": "2.0",
        "id": id,
        "result": result,
    }
    mcp_server.send(peer_id, JSON.stringify(response))

func _send_error(peer_id: int, id: int, message: String):
    var response = {
        "jsonrpc": "2.0",
        "id": id,
        "error": {"code": -1, "message": message},
    }
    mcp_server.send(peer_id, JSON.stringify(response))
```

创建最小 AI 面板 `packages/godot-plugin/addons/godot_forge/ui/ai_panel.tscn` 和 `ai_panel.gd`：

```gdscript
# ai_panel.gd
@tool
extends VBoxContainer

@onready var status_label: Label = $StatusBar/StatusLabel
@onready var chat_input: TextEdit = $InputArea/ChatInput
@onready var send_button: Button = $InputArea/SendButton
@onready var chat_log: RichTextLabel = $ChatLog

var is_connected := false

func _ready():
    send_button.pressed.connect(_on_send)
    set_connection_status(false)

func set_connection_status(connected: bool):
    is_connected = connected
    if status_label:
        status_label.text = "● MCP Connected" if connected else "○ MCP Disconnected"
        status_label.modulate = Color.GREEN if connected else Color.RED

func _on_send():
    var text = chat_input.text.strip_edges()
    if text.is_empty():
        return
    chat_log.append_text("\n[b]You:[/b] %s\n" % text)
    chat_input.text = ""
    # TODO: 发送到 AI 服务
    chat_log.append_text("[i]Processing...[/i]\n")
```

**验收**：在 Godot 4.x 中启用插件，底部面板出现 "AI Assistant"

---

## Task 0.4 — AI Services 骨架

```bash
cd packages/ai-services

# Python 环境
python3 -m venv .venv
source .venv/bin/activate

# 创建依赖文件
cat > requirements.txt << 'EOF'
fastapi>=0.110.0
uvicorn[standard]>=0.29.0
pydantic>=2.7.0
httpx>=0.27.0
python-dotenv>=1.0.0
anthropic>=0.52.0
openai>=1.30.0
Pillow>=10.3.0
aiofiles>=24.1.0
websockets>=12.0
EOF

pip install -r requirements.txt
```

创建 `src/main.py`：

```python
"""GodotForge AI Services — FastAPI 入口"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from .config import settings
from .routers import codegen, imagegen, modelgen, audiogen

@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"[AI Services] Starting on port {settings.port}")
    print(f"[AI Services] LLM Provider: {settings.llm_provider}")
    yield
    print("[AI Services] Shutting down")

app = FastAPI(
    title="GodotForge AI Services",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(codegen.router, prefix="/api/v1/codegen", tags=["Code Generation"])
app.include_router(imagegen.router, prefix="/api/v1/imagegen", tags=["Image Generation"])
app.include_router(modelgen.router, prefix="/api/v1/modelgen", tags=["3D Model Generation"])
app.include_router(audiogen.router, prefix="/api/v1/audiogen", tags=["Audio Generation"])

@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}
```

创建 `src/config.py`：

```python
"""配置管理 — 所有 AI 供应商通过环境变量配置"""
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    port: int = 8100
    
    # LLM
    llm_provider: str = "anthropic"  # anthropic | openai | ollama
    anthropic_api_key: str = ""
    openai_api_key: str = ""
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
    
    class Config:
        env_file = ".env"
        env_prefix = "GODOTFORGE_"

settings = Settings()
```

创建 `src/routers/codegen.py`：

```python
"""代码生成路由"""
from fastapi import APIRouter
from pydantic import BaseModel
from ..services.llm_service import generate_gdscript

router = APIRouter()

class CodeGenRequest(BaseModel):
    prompt: str
    context: str = ""           # 当前项目上下文
    scene_tree: str = ""        # 场景树 JSON
    existing_scripts: list[str] = []  # 已有脚本内容
    godot_version: str = "4.4"

class CodeGenResponse(BaseModel):
    code: str
    explanation: str
    files: list[dict]  # [{path, content}]

@router.post("/generate", response_model=CodeGenResponse)
async def generate_code(req: CodeGenRequest):
    result = await generate_gdscript(
        prompt=req.prompt,
        context=req.context,
        scene_tree=req.scene_tree,
        existing_scripts=req.existing_scripts,
        godot_version=req.godot_version,
    )
    return result

@router.post("/fix")
async def fix_errors(errors: list[str], script_content: str):
    """根据错误信息修复 GDScript"""
    result = await generate_gdscript(
        prompt=f"Fix these GDScript errors:\n" + "\n".join(errors),
        context=script_content,
    )
    return result

@router.post("/explain")
async def explain_code(code: str):
    """解释 GDScript 代码"""
    result = await generate_gdscript(
        prompt=f"Explain this GDScript code in detail:\n{code}",
    )
    return {"explanation": result.get("explanation", "")}
```

创建 `src/services/llm_service.py`：

```python
"""LLM 统一服务 — 支持多供应商切换"""
from ..config import settings

GDSCRIPT_SYSTEM_PROMPT = """You are an expert Godot 4.x game developer.
You write clean, efficient GDScript that follows Godot 4 conventions.

Key rules:
- Use @export, @onready annotations
- Use typed variables (var speed: float = 100.0)
- Use signal declarations (signal health_changed(new_health: int))
- Use StringName for signal connections
- Use Node paths with $ shorthand where appropriate
- Follow Godot 4 API (not Godot 3)

Always respond with valid, complete GDScript code.
Include explanatory comments.
If creating multiple files, clearly separate them with file paths."""

async def generate_gdscript(
    prompt: str,
    context: str = "",
    scene_tree: str = "",
    existing_scripts: list[str] = None,
    godot_version: str = "4.4",
) -> dict:
    """统一 GDScript 生成接口"""
    
    # 构建上下文
    full_prompt = f"Godot {godot_version} project.\n"
    if scene_tree:
        full_prompt += f"\nCurrent scene tree:\n{scene_tree}\n"
    if context:
        full_prompt += f"\nAdditional context:\n{context}\n"
    if existing_scripts:
        for s in existing_scripts:
            full_prompt += f"\nExisting script:\n{s}\n"
    full_prompt += f"\nTask: {prompt}"
    
    if settings.llm_provider == "anthropic":
        return await _generate_anthropic(full_prompt)
    elif settings.llm_provider == "openai":
        return await _generate_openai(full_prompt)
    elif settings.llm_provider == "ollama":
        return await _generate_ollama(full_prompt)
    else:
        raise ValueError(f"Unknown LLM provider: {settings.llm_provider}")

async def _generate_anthropic(prompt: str) -> dict:
    import anthropic
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    response = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=8192,
        system=GDSCRIPT_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    text = response.content[0].text
    return _parse_code_response(text)

async def _generate_openai(prompt: str) -> dict:
    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": GDSCRIPT_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        max_tokens=8192,
    )
    text = response.choices[0].message.content
    return _parse_code_response(text)

async def _generate_ollama(prompt: str) -> dict:
    import httpx
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{settings.ollama_base_url}/api/chat",
            json={
                "model": settings.ollama_model,
                "messages": [
                    {"role": "system", "content": GDSCRIPT_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                "stream": False,
            },
        )
        data = response.json()
        text = data.get("message", {}).get("content", "")
        return _parse_code_response(text)

def _parse_code_response(text: str) -> dict:
    """解析 LLM 响应，提取代码块和说明"""
    import re
    files = []
    code_blocks = re.findall(r'```(?:gdscript|gd)?\s*\n(.*?)```', text, re.DOTALL)
    
    # 尝试提取文件路径
    path_pattern = re.compile(r'#\s*(?:File|Path|file|path):\s*(res://\S+)')
    for block in code_blocks:
        path_match = path_pattern.search(block)
        path = path_match.group(1) if path_match else f"res://scripts/generated_{len(files)}.gd"
        files.append({"path": path, "content": block.strip()})
    
    # 提取非代码部分作为说明
    explanation = re.sub(r'```.*?```', '', text, flags=re.DOTALL).strip()
    
    return {
        "code": code_blocks[0] if code_blocks else "",
        "explanation": explanation,
        "files": files,
    }
```

**验收**：`uvicorn src.main:app --port 8100` 启动，访问 `http://localhost:8100/docs` 看到 Swagger UI

---

## Task 0.5 — POC 端到端验证

创建 `scripts/poc_test.sh`：

```bash
#!/bin/bash
# POC 验证脚本：自然语言 → Godot 场景

echo "=== GodotForge POC Test ==="

# 1. 启动 AI Services
cd packages/ai-services
source .venv/bin/activate
uvicorn src.main:app --port 8100 &
AI_PID=$!
sleep 3

# 2. 测试代码生成 API
echo "\n--- Testing Code Generation ---"
curl -s -X POST http://localhost:8100/api/v1/codegen/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Create a simple 2D player controller with WASD movement, 200 pixels/sec speed, and a jump with gravity",
    "godot_version": "4.4"
  }' | python3 -m json.tool

# 3. 测试健康检查
echo "\n--- Health Check ---"
curl -s http://localhost:8100/health | python3 -m json.tool

# 4. 清理
kill $AI_PID 2>/dev/null
echo "\n=== POC Test Complete ==="
```

**验收标准**：
- [ ] MCP Server 编译成功，可通过 stdio 启动
- [ ] Godot 插件在编辑器中加载，显示 AI 面板
- [ ] AI Services 启动，Swagger 文档可访问
- [ ] 代码生成 API 返回有效 GDScript
- [ ] 所有服务之间的通信协议一致 (JSON-RPC 2.0)

---

## Task 0.6 — 开发环境 Docker 化

创建 `docker/docker-compose.yml`：

```yaml
version: "3.9"

services:
  mcp-server:
    build:
      context: ../packages/mcp-server
      dockerfile: ../../docker/Dockerfile.mcp
    ports:
      - "6505:6505"
    environment:
      - GODOT_MCP_PORT=6505
    volumes:
      - ../packages/mcp-server/src:/app/src
    restart: unless-stopped

  ai-services:
    build:
      context: ../packages/ai-services
      dockerfile: ../../docker/Dockerfile.ai
    ports:
      - "8100:8100"
    env_file:
      - ../.env
    volumes:
      - ../packages/ai-services/src:/app/src
      - ai-cache:/app/cache
    restart: unless-stopped
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]

  web-ui:
    build:
      context: ../packages/web-ui
      dockerfile: ../../docker/Dockerfile.web
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8100
      - NEXT_PUBLIC_WS_URL=ws://localhost:6505
    volumes:
      - ../packages/web-ui/src:/app/src
    restart: unless-stopped

volumes:
  ai-cache:
```

创建 `.env.example`：

```env
# LLM Provider (anthropic | openai | ollama)
GODOTFORGE_LLM_PROVIDER=anthropic
GODOTFORGE_ANTHROPIC_API_KEY=sk-ant-...
GODOTFORGE_OPENAI_API_KEY=sk-...
GODOTFORGE_OLLAMA_BASE_URL=http://localhost:11434
GODOTFORGE_OLLAMA_MODEL=deepseek-coder-v2:16b

# Image Generation
GODOTFORGE_IMAGE_PROVIDER=comfyui
GODOTFORGE_COMFYUI_URL=http://localhost:8188

# 3D Model Generation
GODOTFORGE_MODEL3D_PROVIDER=hunyuan3d
GODOTFORGE_HUNYUAN3D_PATH=/models/hunyuan3d
GODOTFORGE_MESHY_API_KEY=

# Audio
GODOTFORGE_AUDIO_PROVIDER=bark
GODOTFORGE_BARK_MODEL_PATH=/models/bark

# Godot
GODOTFORGE_GODOT_PATH=/usr/local/bin/godot
```

**验收**：`docker compose up` 启动全部服务无报错

---

## Phase 0 完成标志

- [ ] Monorepo 结构创建完成
- [ ] MCP Server 可编译运行
- [ ] Godot 插件可在编辑器中加载
- [ ] AI Services FastAPI 可启动
- [ ] POC 端到端测试通过
- [ ] Docker 开发环境可用
- [ ] README.md 完善（项目介绍、快速开始）
- [ ] 首次 git commit + push

**下一步**：执行 `docs/phases/phase1-core-engine.md`
