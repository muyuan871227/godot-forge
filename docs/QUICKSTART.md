# GodotForge — Claude Code 快速启动指南

## 在 Claude Code 中使用本项目

### 1. 克隆并进入项目

```bash
git clone https://github.com/your-org/godot-forge.git
cd godot-forge
```

### 2. 阅读 CLAUDE.md

Claude Code 启动时会自动读取 `CLAUDE.md`，了解项目结构和执行计划。

### 3. 按阶段执行

```
# 告诉 Claude Code:
"读取 docs/phases/phase0-bootstrap.md 并逐步执行所有任务"
```

### 4. MCP 配置

将以下配置添加到 Claude Code 的 MCP 设置中：

**~/.config/claude-code/mcp.json** (或对应平台的配置路径):

```json
{
  "mcpServers": {
    "godot-forge": {
      "command": "node",
      "args": ["./packages/mcp-server/build/index.js"],
      "env": {
        "GODOT_MCP_PORT": "6505",
        "DEBUG": "true"
      }
    }
  }
}
```

### 5. 环境变量

```bash
cp .env.example .env
# 编辑 .env 填入 API Key
```

### 6. 常用 Claude Code 命令

```
# 生成代码
"为 player.gd 添加冲刺能力，按 Shift 触发，有 2 秒冷却"

# 生成资产
"为角色生成一个像素风格的精灵图，包含 idle 和 run 动画"

# 修复错误
"检查当前场景的脚本错误并修复"

# 创建场景
"创建一个新场景，包含 TileMap 地面、Player 和 Camera2D"

# 运行测试
"运行项目并截图，检查是否有视觉问题"

# 构建导出
"导出为 Web 平台的 HTML5 版本"
```

---

## 项目进度追踪

| Phase | 状态 | 开始日期 | 完成日期 |
|-------|------|----------|----------|
| Phase 0 - Bootstrap | ⬜ 未开始 | | |
| Phase 1 - Core Engine | ⬜ 未开始 | | |
| Phase 2 - AI Pipeline | ⬜ 未开始 | | |
| Phase 3 - Platform | ⬜ 未开始 | | |
| Phase 4 - Ecosystem | ⬜ 未开始 | | |

---

## 核心依赖版本

| 组件 | 版本 | 用途 |
|------|------|------|
| Godot Engine | 4.4+ | 游戏引擎核心 |
| Node.js | 20+ | MCP Server + CLI |
| Python | 3.10+ | AI Services |
| TypeScript | 5.5+ | MCP + Web + CLI |
| Next.js | 14+ | Web UI |
| FastAPI | 0.110+ | AI API 服务 |
| MCP SDK | latest | 协议实现 |
| Hunyuan3D | 2.1 | 3D 模型生成 |
| Bark | latest | 音频生成 |
| MusicGen | small | BGM 生成 |
| ComfyUI | latest | 图像生成引擎 |
| FLUX.1 / SDXL | latest | 图像模型 |
