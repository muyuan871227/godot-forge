# GodotForge

AI + Godot 游戏创作平台 — 通过自然语言描述完成从概念到可运行游戏的完整开发流程。

## 技术栈

- **Godot 4.4+** — 游戏引擎核心
- **TypeScript** — MCP Server (Model Context Protocol)
- **Python / FastAPI** — AI 服务层
- **GDScript** — Godot 编辑器插件
- **React + Next.js** — Web 管理端

## 项目结构

```
packages/
  mcp-server/      # MCP Server — 连接 AI 与 Godot 引擎
  ai-services/     # AI 服务 — 代码/图像/3D/音频生成
  godot-plugin/    # Godot 编辑器插件
  web-ui/          # Web 管理端
  cli/             # CLI 工具
```

## 快速开始

### 前置条件

- Node.js >= 20.x
- Python >= 3.10
- Godot >= 4.4

### 安装

```bash
# 克隆项目
git clone https://github.com/your-org/godot-forge.git
cd godot-forge

# 安装 Node 依赖
npm install

# 设置 AI 服务
cd packages/ai-services
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 配置环境变量
cd ../..
cp .env.example .env
# 编辑 .env 填入你的 API Key
```

### 启动服务

```bash
# MCP Server (编译 + 运行)
cd packages/mcp-server
npm run build

# AI Services
cd packages/ai-services
source .venv/bin/activate
uvicorn src.main:app --port 8100

# 或使用 Docker
cd docker
docker compose up
```

### Godot 插件

1. 将 `packages/godot-plugin/addons/godot_forge/` 复制到你的 Godot 项目的 `addons/` 目录
2. 在 Godot 编辑器中启用插件：Project > Project Settings > Plugins > GodotForge

## 开发路线

- **Phase 0** — 项目初始化与验证 (当前)
- **Phase 1** — 核心引擎 (MCP + 插件 + 基础 AI)
- **Phase 2** — 全链路 AI 资产管线
- **Phase 3** — Web 平台化
- **Phase 4** — 生态与商业化

## License

MIT
