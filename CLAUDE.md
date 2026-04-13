# CLAUDE.md — AI + Godot 游戏创作平台 (GodotForge)

## 项目概述

GodotForge 是一个以 Godot 4.x 引擎为核心、深度集成 AI 的开源游戏创作平台。
用户通过自然语言描述即可完成从概念到可运行游戏的完整开发流程。

**技术栈**：Godot 4.4+ / TypeScript (MCP Server) / Python (AI Services) / React+Next.js (Web UI) / GDScript (Editor Plugin)

## 项目结构

```
godot-forge/
├── CLAUDE.md                          # 你正在读的文件
├── README.md                          # 项目介绍
├── LICENSE                            # MIT License
├── package.json                       # Monorepo root
├── turbo.json                         # Turborepo 配置
│
├── packages/
│   ├── mcp-server/                    # MCP Server (TypeScript)
│   │   ├── src/
│   │   │   ├── index.ts               # 入口：stdio transport
│   │   │   ├── server.ts              # MCP server 核心
│   │   │   ├── tools/                 # 工具注册目录
│   │   │   │   ├── project.ts         # 项目管理工具 (8)
│   │   │   │   ├── scene.ts           # 场景操作工具 (15)
│   │   │   │   ├── node.ts            # 节点 CRUD 工具 (20)
│   │   │   │   ├── script.ts          # 脚本操作工具 (12)
│   │   │   │   ├── resource.ts        # 资源管理工具 (10)
│   │   │   │   ├── editor.ts          # 编辑器控制工具 (8)
│   │   │   │   ├── debug.ts           # 调试工具 (10)
│   │   │   │   ├── physics.ts         # 物理系统工具 (8)
│   │   │   │   ├── animation.ts       # 动画系统工具 (10)
│   │   │   │   ├── audio.ts           # 音频系统工具 (6)
│   │   │   │   ├── ui.ts              # UI 控件工具 (10)
│   │   │   │   ├── rendering.ts       # 渲染工具 (8)
│   │   │   │   ├── input.ts           # 输入模拟工具 (6)
│   │   │   │   ├── navigation.ts      # 导航系统工具 (5)
│   │   │   │   ├── networking.ts      # 网络工具 (6)
│   │   │   │   └── index.ts           # 工具注册汇总
│   │   │   ├── transport/
│   │   │   │   ├── websocket.ts       # WebSocket 连接 Godot
│   │   │   │   └── tcp.ts             # TCP 连接运行时
│   │   │   ├── godot/
│   │   │   │   ├── headless.ts        # Godot 无头模式操作
│   │   │   │   ├── process.ts         # 进程管理
│   │   │   │   └── screenshot.ts      # 截图捕获
│   │   │   └── utils/
│   │   │       ├── uid.ts             # UID 管理
│   │   │       ├── path.ts            # 路径工具
│   │   │       └── logger.ts          # 日志
│   │   ├── scripts/                   # GDScript 操作脚本
│   │   │   ├── godot_operations.gd    # 无头操作
│   │   │   └── mcp_interaction.gd     # 运行时交互
│   │   ├── package.json
│   │   └── tsconfig.json
│   │
│   ├── ai-services/                   # AI 服务层 (Python)
│   │   ├── src/
│   │   │   ├── __init__.py
│   │   │   ├── main.py                # FastAPI 入口
│   │   │   ├── routers/
│   │   │   │   ├── codegen.py         # 代码生成路由
│   │   │   │   ├── imagegen.py        # 图像生成路由
│   │   │   │   ├── modelgen.py        # 3D 模型生成路由
│   │   │   │   ├── audiogen.py        # 音频生成路由
│   │   │   │   └── npcai.py           # NPC AI 路由
│   │   │   ├── services/
│   │   │   │   ├── llm_service.py     # LLM 统一接口
│   │   │   │   ├── image_service.py   # 图像生成服务
│   │   │   │   ├── model3d_service.py # 3D 模型生成服务
│   │   │   │   ├── audio_service.py   # 音频生成服务
│   │   │   │   └── asset_pipeline.py  # 资产后处理管线
│   │   │   ├── providers/
│   │   │   │   ├── anthropic.py       # Claude API
│   │   │   │   ├── openai.py          # OpenAI API
│   │   │   │   ├── ollama.py          # Ollama 本地
│   │   │   │   ├── comfyui.py         # ComfyUI 后端
│   │   │   │   ├── hunyuan3d.py       # Hunyuan3D 本地
│   │   │   │   ├── triposr.py         # TripoSR
│   │   │   │   ├── bark.py            # Bark TTS/SFX
│   │   │   │   └── musicgen.py        # MusicGen BGM
│   │   │   ├── pipelines/
│   │   │   │   ├── sprite_sheet.py    # 精灵图生成管线
│   │   │   │   ├── tilemap.py         # Tilemap 生成管线
│   │   │   │   ├── character.py       # 角色资产管线
│   │   │   │   ├── environment.py     # 环境资产管线
│   │   │   │   └── game_from_text.py  # 文字→游戏主管线
│   │   │   └── config.py              # 配置管理
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   │
│   ├── godot-plugin/                  # Godot 编辑器插件 (GDScript)
│   │   ├── addons/
│   │   │   └── godot_forge/
│   │   │       ├── plugin.cfg
│   │   │       ├── plugin.gd          # EditorPlugin 主入口
│   │   │       ├── ui/
│   │   │       │   ├── ai_panel.gd    # AI 对话面板
│   │   │       │   ├── ai_panel.tscn
│   │   │       │   ├── asset_browser.gd  # AI 资产浏览器
│   │   │       │   ├── asset_browser.tscn
│   │   │       │   ├── generation_preview.gd # 生成预览
│   │   │       │   └── settings_dialog.gd    # 设置对话框
│   │   │       ├── mcp/
│   │   │       │   ├── mcp_client.gd  # WebSocket MCP 客户端
│   │   │       │   ├── tool_handler.gd # 工具调用处理
│   │   │       │   └── message_protocol.gd  # 消息协议
│   │   │       ├── ai/
│   │   │       │   ├── code_assistant.gd    # 代码辅助
│   │   │       │   ├── scene_generator.gd   # 场景生成
│   │   │       │   └── asset_generator.gd   # 资产生成
│   │   │       └── utils/
│   │   │           ├── http_client.gd       # HTTP 工具
│   │   │           └── config_manager.gd    # 配置管理
│   │   └── project.godot              # 测试项目
│   │
│   ├── web-ui/                        # Web 管理端 (Next.js)
│   │   ├── src/
│   │   │   ├── app/
│   │   │   │   ├── layout.tsx
│   │   │   │   ├── page.tsx           # 首页/项目列表
│   │   │   │   ├── project/[id]/
│   │   │   │   │   ├── page.tsx       # 项目工作区
│   │   │   │   │   ├── chat/page.tsx  # AI 对话
│   │   │   │   │   ├── assets/page.tsx # 资产管理
│   │   │   │   │   └── build/page.tsx # 构建导出
│   │   │   │   ├── templates/page.tsx # 模板市场
│   │   │   │   └── settings/page.tsx  # 平台设置
│   │   │   ├── components/
│   │   │   │   ├── chat/              # AI 对话组件
│   │   │   │   ├── editor/            # 在线编辑器
│   │   │   │   ├── preview/           # 游戏预览
│   │   │   │   └── assets/            # 资产管理
│   │   │   ├── lib/
│   │   │   │   ├── api.ts             # API 客户端
│   │   │   │   ├── websocket.ts       # WS 连接
│   │   │   │   └── stores/            # 状态管理
│   │   │   └── styles/
│   │   ├── package.json
│   │   └── next.config.js
│   │
│   └── cli/                           # CLI 工具
│       ├── src/
│       │   ├── index.ts               # 入口
│       │   ├── commands/
│       │   │   ├── init.ts            # 初始化项目
│       │   │   ├── generate.ts        # AI 生成
│       │   │   ├── build.ts           # 构建导出
│       │   │   ├── serve.ts           # 启动服务
│       │   │   └── asset.ts           # 资产管理
│       │   └── utils/
│       ├── package.json
│       └── tsconfig.json
│
├── docker/
│   ├── docker-compose.yml             # 开发环境编排
│   ├── docker-compose.prod.yml        # 生产环境编排
│   ├── Dockerfile.mcp                 # MCP Server
│   ├── Dockerfile.ai                  # AI Services
│   └── Dockerfile.web                 # Web UI
│
├── templates/                         # 游戏模板
│   ├── 2d-platformer/
│   ├── 2d-topdown-rpg/
│   ├── 3d-fps/
│   ├── 3d-third-person/
│   ├── visual-novel/
│   └── puzzle/
│
├── docs/
│   ├── phases/                        # 阶段执行文档
│   │   ├── phase0-bootstrap.md
│   │   ├── phase1-core-engine.md
│   │   ├── phase2-ai-pipeline.md
│   │   ├── phase3-platform.md
│   │   └── phase4-ecosystem.md
│   ├── modules/                       # 模块规格书
│   │   ├── mcp-server-spec.md
│   │   ├── ai-services-spec.md
│   │   ├── godot-plugin-spec.md
│   │   ├── web-ui-spec.md
│   │   └── cli-spec.md
│   └── api/                           # API 文档
│       ├── mcp-tools.md
│       └── rest-api.md
│
└── tests/
    ├── mcp-server/
    ├── ai-services/
    ├── integration/
    └── e2e/
```

## 执行原则

1. **渐进式构建**：每个 Phase 产出可运行的交付物，不做空中楼阁
2. **测试先行**：每个模块先写测试骨架，再填充实现
3. **模块独立**：各 package 可独立运行和测试
4. **配置驱动**：所有 AI 供应商通过配置切换，不硬编码
5. **文档同步**：代码和文档在同一 PR 中更新

## Claude Code 执行入口

按以下顺序执行各阶段：

```
Phase 0 → docs/phases/phase0-bootstrap.md     # 项目初始化
Phase 1 → docs/phases/phase1-core-engine.md    # MCP + 插件 + 基础 AI
Phase 2 → docs/phases/phase2-ai-pipeline.md    # 全链路 AI 资产
Phase 3 → docs/phases/phase3-platform.md       # Web 平台化
Phase 4 → docs/phases/phase4-ecosystem.md      # 生态与商业化
```

每个阶段文档包含：
- 具体任务清单（可勾选）
- 每个任务的 Claude Code 命令序列
- 验收标准
- 依赖关系

**开始执行**：阅读 `docs/phases/phase0-bootstrap.md` 并逐步执行。
