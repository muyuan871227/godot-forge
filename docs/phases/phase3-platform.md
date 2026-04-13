# Phase 3 — 平台化 (预计 4 个月)

## 概述
将工具链包装为完整的 Web 平台：用户系统、项目管理、模板市场、多平台导出。

---

## Task 3.1 — Web UI 构建 (Next.js)

### 3.1.1 项目初始化

```bash
cd packages/web-ui
npx create-next-app@latest . --typescript --tailwind --app --src-dir
npm install zustand @tanstack/react-query socket.io-client
npm install @radix-ui/react-dialog @radix-ui/react-tabs @radix-ui/react-dropdown-menu
npm install lucide-react monaco-editor @monaco-editor/react
npm install -D @types/node
```

### 3.1.2 核心页面实现

```
src/app/
├── layout.tsx              # 全局布局 (侧边栏 + 顶栏)
├── page.tsx                # 首页：项目列表 + 新建项目
├── project/[id]/
│   ├── layout.tsx          # 项目工作区布局 (标签页切换)
│   ├── page.tsx            # 项目概览 (文件树 + 预览)
│   ├── chat/page.tsx       # AI 对话页 (全功能聊天)
│   ├── editor/page.tsx     # 代码编辑器 (Monaco + GDScript)
│   ├── assets/page.tsx     # 资产管理 (生成/上传/浏览)
│   ├── scenes/page.tsx     # 场景管理 (可视化场景树)
│   ├── build/page.tsx      # 构建导出 (多平台)
│   └── settings/page.tsx   # 项目设置
├── templates/page.tsx      # 模板市场
├── community/page.tsx      # 社区 (展示/分享)
├── auth/
│   ├── login/page.tsx
│   └── register/page.tsx
└── settings/page.tsx       # 平台设置
```

### 3.1.3 AI 对话组件

创建 `src/components/chat/ChatInterface.tsx`：

```typescript
"use client";
import { useState, useRef, useEffect } from "react";
import { useMutation } from "@tanstack/react-query";
import { Send, Wand2, Image, Music, Box, Loader2 } from "lucide-react";

interface Message {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  files?: { path: string; content: string; type: string }[];
  timestamp: Date;
}

export function ChatInterface({ projectId }: { projectId: string }) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [activeMode, setActiveMode] = useState<"code" | "image" | "3d" | "audio">("code");
  const scrollRef = useRef<HTMLDivElement>(null);
  
  const generateMutation = useMutation({
    mutationFn: async (prompt: string) => {
      const endpoints = {
        code: "/api/v1/codegen/generate",
        image: "/api/v1/imagegen/generate",
        "3d": "/api/v1/modelgen/generate",
        audio: "/api/v1/audiogen/sfx",
      };
      
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}${endpoints[activeMode]}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt, project_id: projectId }),
      });
      return res.json();
    },
    onSuccess: (data) => {
      setMessages(prev => [...prev, {
        id: crypto.randomUUID(),
        role: "assistant",
        content: data.explanation || "Generated successfully",
        files: data.files || [],
        timestamp: new Date(),
      }]);
    },
  });
  
  const handleSend = () => {
    if (!input.trim()) return;
    setMessages(prev => [...prev, {
      id: crypto.randomUUID(),
      role: "user",
      content: input,
      timestamp: new Date(),
    }]);
    generateMutation.mutate(input);
    setInput("");
  };
  
  return (
    <div className="flex flex-col h-full bg-gray-950">
      {/* 模式切换 */}
      <div className="flex gap-2 p-3 border-b border-gray-800">
        {[
          { key: "code", icon: Wand2, label: "Code" },
          { key: "image", icon: Image, label: "2D Art" },
          { key: "3d", icon: Box, label: "3D Model" },
          { key: "audio", icon: Music, label: "Audio" },
        ].map(mode => (
          <button
            key={mode.key}
            onClick={() => setActiveMode(mode.key as any)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm transition
              ${activeMode === mode.key 
                ? "bg-indigo-600 text-white" 
                : "bg-gray-800 text-gray-400 hover:bg-gray-700"}`}
          >
            <mode.icon size={14} />
            {mode.label}
          </button>
        ))}
      </div>
      
      {/* 消息列表 */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map(msg => (
          <ChatMessage key={msg.id} message={msg} projectId={projectId} />
        ))}
        {generateMutation.isPending && (
          <div className="flex items-center gap-2 text-gray-400">
            <Loader2 className="animate-spin" size={16} />
            Generating...
          </div>
        )}
      </div>
      
      {/* 输入区 */}
      <div className="p-3 border-t border-gray-800">
        <div className="flex gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && (e.preventDefault(), handleSend())}
            placeholder={`Describe what you want to ${activeMode === "code" ? "build" : "generate"}...`}
            className="flex-1 bg-gray-900 rounded-lg p-3 text-gray-200 resize-none border border-gray-700 focus:border-indigo-500 outline-none"
            rows={2}
          />
          <button
            onClick={handleSend}
            disabled={generateMutation.isPending}
            className="px-4 bg-indigo-600 rounded-lg hover:bg-indigo-500 transition disabled:opacity-50"
          >
            <Send size={18} />
          </button>
        </div>
      </div>
    </div>
  );
}
```

### 3.1.4 Monaco GDScript 编辑器

```typescript
// src/components/editor/GDScriptEditor.tsx
import Editor from "@monaco-editor/react";

// 注册 GDScript 语法高亮
const gdscriptLanguage = {
  id: "gdscript",
  extensions: [".gd"],
  aliases: ["GDScript"],
  mimetypes: ["text/x-gdscript"],
};

const gdscriptTokens = {
  keywords: [
    "extends", "class_name", "var", "const", "func", "signal",
    "if", "elif", "else", "for", "while", "match", "return",
    "yield", "await", "pass", "break", "continue",
    "export", "onready", "tool", "static",
    "true", "false", "null", "self", "super",
    "and", "or", "not", "in", "is", "as",
    "enum", "class", "preload", "load",
  ],
  typeKeywords: [
    "int", "float", "String", "bool", "Array", "Dictionary",
    "Vector2", "Vector3", "Color", "Transform2D", "Transform3D",
    "Node", "Node2D", "Node3D", "Control", "Resource",
  ],
  // ... 完整的 tokenizer 规则
};

export function GDScriptEditor({ 
  content, 
  onChange, 
  filePath 
}: {
  content: string;
  onChange: (value: string) => void;
  filePath: string;
}) {
  return (
    <Editor
      height="100%"
      defaultLanguage="gdscript"
      value={content}
      onChange={(v) => onChange(v || "")}
      theme="vs-dark"
      options={{
        fontSize: 14,
        minimap: { enabled: false },
        lineNumbers: "on",
        tabSize: 4,
        insertSpaces: false,
        formatOnPaste: true,
      }}
      beforeMount={(monaco) => {
        monaco.languages.register(gdscriptLanguage);
        monaco.languages.setMonarchTokensProvider("gdscript", gdscriptTokens as any);
      }}
    />
  );
}
```

**验收**：Web UI 可访问，AI 对话、代码编辑器、资产浏览器正常工作

---

## Task 3.2 — 用户系统与项目管理

### 3.2.1 后端 API

使用 FastAPI + SQLite (开发) / PostgreSQL (生产)：

```python
# ai-services/src/routers/users.py
from fastapi import APIRouter, Depends
from pydantic import BaseModel
import jwt, bcrypt

router = APIRouter()

class UserCreate(BaseModel):
    email: str
    username: str
    password: str

class ProjectCreate(BaseModel):
    name: str
    template: str = ""
    description: str = ""

@router.post("/register")
async def register(user: UserCreate):
    ...

@router.post("/login")
async def login(email: str, password: str):
    ...

@router.get("/projects")
async def list_projects(user=Depends(get_current_user)):
    ...

@router.post("/projects")
async def create_project(project: ProjectCreate, user=Depends(get_current_user)):
    # 创建 Godot 项目目录
    # 如果指定了模板，从 templates/ 复制
    ...

@router.get("/projects/{project_id}")
async def get_project(project_id: str, user=Depends(get_current_user)):
    ...
```

### 3.2.2 项目云存储

```python
# 项目文件存储策略:
# - 开发阶段: 本地文件系统
# - 生产阶段: S3 兼容存储 (MinIO 自托管 / AWS S3)

class ProjectStorage:
    async def save_project_files(self, project_id: str, files: dict):
        ...
    
    async def load_project_files(self, project_id: str) -> dict:
        ...
    
    async def sync_to_godot(self, project_id: str, local_path: str):
        """将云端项目同步到本地 Godot 项目目录"""
        ...
```

**验收**：用户注册/登录/创建项目/项目列表

---

## Task 3.3 — 模板系统

### 创建 6 个基础模板

每个模板包含：
```
templates/2d-platformer/
├── project.godot
├── scenes/
│   ├── main_menu.tscn
│   ├── game.tscn
│   ├── player.tscn
│   └── ui.tscn
├── scripts/
│   ├── player.gd
│   ├── game_manager.gd
│   └── ui_manager.gd
├── assets/
│   ├── sprites/       # 占位精灵
│   └── audio/         # 占位音效
├── template.json      # 模板元数据
└── README.md
```

`template.json` 格式：

```json
{
  "name": "2D Platformer",
  "description": "Classic side-scrolling platformer with player movement, enemies, and collectibles",
  "category": "2d",
  "tags": ["platformer", "action", "beginner"],
  "thumbnail": "thumbnail.png",
  "features": ["player_movement", "enemies", "collectibles", "ui", "sound"],
  "godot_version": "4.4",
  "ai_customizable": {
    "player_character": "Describe your player character",
    "world_theme": "Describe the world theme (forest, space, underwater...)",
    "enemy_types": "List enemy types",
    "music_style": "Describe the music style"
  }
}
```

模板列表：
1. **2d-platformer** — 横版过关
2. **2d-topdown-rpg** — 俯视角 RPG
3. **3d-fps** — 第一人称射击
4. **3d-third-person** — 第三人称动作
5. **visual-novel** — 视觉小说
6. **puzzle** — 益智解谜

**验收**：6 个模板可在 Web UI 中选择并一键创建新项目

---

## Task 3.4 — 多平台导出

创建 `ai-services/src/routers/build.py`：

```python
router = APIRouter()

class BuildRequest(BaseModel):
    project_id: str
    platform: str    # windows | macos | linux | android | ios | web
    config: dict = {}

@router.post("/export")
async def export_project(req: BuildRequest):
    """使用 Godot CLI 导出项目"""
    import subprocess
    
    project_path = get_project_path(req.project_id)
    
    # 平台预设映射
    preset_map = {
        "windows": "Windows Desktop",
        "macos": "macOS",
        "linux": "Linux/X11",
        "android": "Android",
        "web": "Web",
    }
    
    preset = preset_map.get(req.platform)
    if not preset:
        return {"error": f"Unsupported platform: {req.platform}"}
    
    output_dir = f"/tmp/godotforge/builds/{req.project_id}/{req.platform}"
    os.makedirs(output_dir, exist_ok=True)
    
    # 文件名
    extensions = {"windows": ".exe", "macos": ".dmg", "linux": ".x86_64", "android": ".apk", "web": ".html"}
    output_file = f"{output_dir}/game{extensions[req.platform]}"
    
    # 执行导出
    cmd = [
        settings.godot_path,
        "--headless",
        "--path", project_path,
        "--export-release", preset, output_file,
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    
    if result.returncode != 0:
        return {"error": result.stderr, "stdout": result.stdout}
    
    return {
        "success": True,
        "platform": req.platform,
        "output_path": output_file,
        "size_bytes": os.path.getsize(output_file),
        "download_url": f"/api/v1/build/download/{req.project_id}/{req.platform}",
    }
```

**验收**：Web UI 中选择平台 → 构建 → 下载可运行文件

---

## Task 3.5 — 游戏内 NPC AI 模块

创建 Godot 插件扩展：

```gdscript
# addons/godot_forge/ai/npc_ai.gd
class_name GodotForgeNPC
extends Node

## NPC AI 节点：为 NPC 添加 LLM 驱动的对话能力

@export var character_name: String = "NPC"
@export var character_description: String = ""
@export var character_knowledge: String = ""
@export var model_path: String = ""  # GGUF 模型路径
@export var max_response_length: int = 100

var _llm: GdLlama

func _ready():
    if model_path.is_empty():
        push_warning("[NPC AI] No model path set for %s" % character_name)
        return
    
    _llm = GdLlama.new()
    _llm.model_path = model_path
    _llm.n_predict = max_response_length
    add_child(_llm)

func chat(player_message: String) -> String:
    """与 NPC 对话"""
    if not _llm:
        return "[No AI model loaded]"
    
    var system_prompt = """You are %s. %s
Your knowledge: %s
Stay in character. Keep responses under %d words. Be conversational.""" % [
        character_name, character_description, character_knowledge, max_response_length
    ]
    
    var response = _llm.generate_text(player_message, system_prompt, "")
    return response

func chat_async(player_message: String):
    """异步对话（不阻塞游戏）"""
    if not _llm:
        return
    
    var system_prompt = "You are %s. %s" % [character_name, character_description]
    _llm.run_generate_text(player_message, system_prompt, "")

signal response_ready(text: String)

func _on_llm_generate_text_finished(text: String):
    response_ready.emit(text)
```

**验收**：NPC 节点可在 Godot 中添加到场景，实时对话生成

---

## Phase 3 完成标志

- [ ] Web UI 全部页面可访问
- [ ] 用户注册/登录/项目管理
- [ ] AI 对话界面支持代码/图像/3D/音频模式
- [ ] Monaco GDScript 编辑器集成
- [ ] 6 个游戏模板可用
- [ ] 多平台导出 (至少 Windows + Web)
- [ ] NPC AI 模块可用
- [ ] 多语言支持 (中/英)

**下一步**：执行 `docs/phases/phase4-ecosystem.md`
