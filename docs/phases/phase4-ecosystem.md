# Phase 4 — 生态与商业化 (预计 4 个月)

## 概述
构建可持续的开源生态：插件系统、资产市场、教育版、企业版、开发者文档。

---

## Task 4.1 — 插件系统

### 4.1.1 插件 SDK

允许社区扩展 AI 能力（新的图像模型、音频模型、游戏模板等）。

创建 `packages/plugin-sdk/`：

```typescript
// plugin-sdk/src/index.ts

export interface GodotForgePlugin {
  /** 插件唯一标识 */
  id: string;
  /** 显示名称 */
  name: string;
  /** 版本 */
  version: string;
  /** 插件类型 */
  type: "ai-provider" | "asset-generator" | "template" | "tool" | "theme";
  /** 初始化 */
  activate(context: PluginContext): Promise<void>;
  /** 卸载 */
  deactivate(): Promise<void>;
}

export interface PluginContext {
  /** 注册新的 MCP 工具 */
  registerTool(tool: ToolDefinition): void;
  /** 注册新的 AI 供应商 */
  registerAIProvider(provider: AIProvider): void;
  /** 注册新的资产生成器 */
  registerAssetGenerator(generator: AssetGenerator): void;
  /** 访问项目 API */
  projectApi: ProjectAPI;
  /** 访问 Godot 连接 */
  godotConnection: GodotConnection;
  /** 日志 */
  log: Logger;
}

export interface AIProvider {
  id: string;
  name: string;
  type: "llm" | "image" | "3d" | "audio";
  generate(input: any): Promise<any>;
  isAvailable(): Promise<boolean>;
}

export interface AssetGenerator {
  id: string;
  name: string;
  category: "sprite" | "3d-model" | "audio" | "tilemap" | "particle" | "shader";
  inputSchema: Record<string, any>;
  generate(params: any): Promise<AssetResult>;
}
```

### 4.1.2 插件示例 — Midjourney 集成

```typescript
// 社区插件示例: @godotforge/plugin-midjourney
import { GodotForgePlugin, PluginContext } from "@godot-forge/plugin-sdk";

export default class MidjourneyPlugin implements GodotForgePlugin {
  id = "midjourney";
  name = "Midjourney Image Provider";
  version = "1.0.0";
  type = "ai-provider" as const;
  
  async activate(context: PluginContext) {
    context.registerAIProvider({
      id: "midjourney",
      name: "Midjourney",
      type: "image",
      async generate(input) {
        // 通过 Midjourney API 生成图像
        // ...
      },
      async isAvailable() {
        return !!process.env.MIDJOURNEY_API_KEY;
      },
    });
    
    context.log.info("Midjourney plugin activated");
  }
  
  async deactivate() {}
}
```

### 4.1.3 插件注册表与安装

```bash
# CLI 插件管理
godot-forge plugin install @godotforge/plugin-midjourney
godot-forge plugin list
godot-forge plugin remove @godotforge/plugin-midjourney

# 插件注册表 (类似 npm registry)
godot-forge plugin publish   # 发布到社区
godot-forge plugin search "image generation"
```

**验收**：一个社区插件可安装、激活、在平台中使用

---

## Task 4.2 — 资产市场

### 4.2.1 市场后端

```python
# ai-services/src/routers/marketplace.py

router = APIRouter()

class AssetListing(BaseModel):
    title: str
    description: str
    category: str      # sprite | 3d_model | audio | template | plugin | shader
    tags: list[str]
    price: float = 0   # 0 = 免费
    preview_images: list[str]
    files: list[str]
    license: str = "MIT"

@router.post("/listings")
async def create_listing(listing: AssetListing, user=Depends(get_current_user)):
    """上架资产"""
    ...

@router.get("/listings")
async def browse_listings(
    category: str = "",
    search: str = "",
    sort: str = "popular",  # popular | newest | price_asc | price_desc
    page: int = 1,
    limit: int = 20,
):
    """浏览市场"""
    ...

@router.post("/listings/{id}/download")
async def download_asset(id: str, user=Depends(get_current_user)):
    """下载资产到用户项目"""
    ...

@router.post("/listings/{id}/import")
async def import_to_project(id: str, project_id: str, user=Depends(get_current_user)):
    """一键导入资产到 Godot 项目"""
    ...
```

### 4.2.2 AI 生成资产一键上架

```python
@router.post("/ai-to-marketplace")
async def publish_ai_asset(
    generation_id: str,      # AI 生成记录 ID
    title: str,
    description: str,
    price: float = 0,
    user=Depends(get_current_user),
):
    """将 AI 生成的资产一键上架到市场"""
    # 获取生成记录
    generation = await get_generation(generation_id)
    
    # 创建上架信息
    listing = AssetListing(
        title=title,
        description=description,
        category=generation["type"],
        tags=generation.get("tags", []),
        price=price,
        preview_images=[generation.get("preview_url", "")],
        files=generation.get("output_files", []),
        license="CC-BY-4.0",
    )
    
    return await create_listing(listing, user)
```

**验收**：用户可上架、搜索、下载资产

---

## Task 4.3 — 教育版

### 4.3.1 教学功能

```python
# 交互式教程系统
class TutorialSystem:
    """
    功能:
    1. 步骤式引导 (每步高亮 UI 区域 + 说明)
    2. AI 教学助手 (解释概念 + 回答问题)
    3. 挑战模式 (给任务描述，学生用 AI 辅助完成)
    4. 进度追踪
    """
    
    tutorials = [
        {
            "id": "first_game",
            "title": "你的第一个游戏",
            "steps": [
                {"instruction": "告诉 AI 你想做什么游戏", "hint": "试试'一个跳跃小游戏'"},
                {"instruction": "查看 AI 生成的代码，理解 _physics_process", "check": "script_exists"},
                {"instruction": "为角色生成一个精灵图", "check": "sprite_exists"},
                {"instruction": "运行游戏试玩！", "check": "game_ran"},
                {"instruction": "让 AI 添加一个敌人", "check": "enemy_exists"},
            ],
        },
        # ... 更多教程
    ]
```

### 4.3.2 课堂管理

```
教师端:
- 创建课堂 (邀请码加入)
- 布置作业 (游戏开发任务)
- 查看学生进度和作品
- 限制 AI 使用程度 (教学模式：AI 只给提示不给完整代码)

学生端:
- 加入课堂
- 跟随教程
- 提交作品
- 互相评价
```

**验收**：教师可创建课堂，学生可完成引导式教程

---

## Task 4.4 — 企业版

### 4.4.1 私有部署方案

```yaml
# docker/docker-compose.enterprise.yml
version: "3.9"

services:
  # 所有服务 + 企业特性
  mcp-server:
    ...
  
  ai-services:
    ...
    environment:
      # 企业: 使用私有模型
      - GODOTFORGE_LLM_PROVIDER=ollama
      - GODOTFORGE_OLLAMA_BASE_URL=http://ollama:11434
      - GODOTFORGE_OLLAMA_MODEL=godotforge-coder-enterprise
  
  ollama:
    image: ollama/ollama:latest
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
    volumes:
      - ollama_models:/root/.ollama
  
  web-ui:
    ...
    environment:
      # 企业: SSO 集成
      - AUTH_PROVIDER=saml
      - SAML_METADATA_URL=...
  
  postgres:
    image: postgres:16
    ...
  
  minio:
    image: minio/minio
    ...
    # 企业: 私有资产存储

  # 企业特有
  model-training:
    build: ./Dockerfile.training
    # 支持在企业数据上微调模型
    ...

volumes:
  ollama_models:
  postgres_data:
  minio_data:
```

### 4.4.2 企业 API

```python
# 企业版专属 API
@router.post("/enterprise/train-model")
async def train_custom_model(
    training_data_path: str,
    base_model: str = "deepseek-coder-6.7b",
    epochs: int = 3,
):
    """在企业数据上微调 GDScript 模型"""
    ...

@router.post("/enterprise/batch-generate")
async def batch_generate_assets(
    specifications: list[dict],
    parallel: int = 4,
):
    """批量生成资产 (适合大型项目)"""
    ...

@router.get("/enterprise/usage-analytics")
async def get_usage_analytics(timeframe: str = "30d"):
    """使用量分析"""
    ...
```

**验收**：企业 Docker Compose 可一键部署，含私有模型和存储

---

## Task 4.5 — 开发者文档与 SDK

### 4.5.1 文档站点 (VitePress)

```bash
npm install -D vitepress
mkdir docs-site && cd docs-site

# 文档结构
docs/
├── index.md                 # 首页
├── getting-started/
│   ├── installation.md      # 安装指南
│   ├── quickstart.md        # 5 分钟快速开始
│   └── first-game.md        # 第一个游戏教程
├── guides/
│   ├── ai-code-generation.md
│   ├── asset-generation.md
│   ├── 3d-model-pipeline.md
│   ├── audio-generation.md
│   ├── npc-ai.md
│   ├── templates.md
│   └── deployment.md
├── api/
│   ├── mcp-tools.md         # 全部 150+ MCP 工具参考
│   ├── rest-api.md           # REST API 参考
│   └── plugin-sdk.md         # 插件 SDK 参考
├── architecture/
│   ├── overview.md
│   ├── mcp-protocol.md
│   └── ai-pipeline.md
└── contributing/
    ├── development-setup.md
    ├── plugin-development.md
    └── code-style.md
```

### 4.5.2 MCP 工具 API 自动文档

```python
# 从 MCP Server 工具定义自动生成文档
def generate_tool_docs():
    """遍历所有注册工具，生成 Markdown 文档"""
    docs = "# MCP Tools Reference\n\n"
    docs += f"Total tools: {len(tools)}\n\n"
    
    for category, tool_list in tools_by_category.items():
        docs += f"## {category}\n\n"
        for tool in tool_list:
            docs += f"### `{tool.name}`\n\n"
            docs += f"{tool.description}\n\n"
            docs += f"**Parameters:**\n\n"
            docs += f"```json\n{json.dumps(tool.inputSchema, indent=2)}\n```\n\n"
            docs += f"**Example:**\n\n"
            docs += f"```json\n{json.dumps(tool.example, indent=2)}\n```\n\n"
    
    return docs
```

**验收**：文档站点可访问，包含完整 API 参考和教程

---

## Task 4.6 — 社区与 Game Jam

### 4.6.1 社区功能

```
- 作品展示 (用户发布的游戏，Web 端在线试玩)
- 排行榜 (最多 star / 最多 fork / 最新)
- 评论与评分
- "Remix" 功能 (Fork 他人项目，用 AI 修改)
```

### 4.6.2 Game Jam 系统

```python
class GameJam:
    """
    线上 Game Jam 系统:
    1. 主办方创建 Jam (主题 + 时间 + 规则)
    2. 参赛者加入并创建项目
    3. AI 辅助限制 (可配置: 无限制 / 仅代码辅助 / 禁止 AI)
    4. 作品提交 + Web 在线试玩
    5. 社区投票 + 评委评审
    6. 排名公布
    """
    ...
```

**验收**：可创建 Game Jam，参赛者提交作品，社区投票

---

## Task 4.7 — 商业化配置

```python
# 定价方案
PRICING_PLANS = {
    "free": {
        "ai_generations_per_day": 20,
        "projects": 3,
        "storage_gb": 1,
        "export_platforms": ["web"],
        "templates": "basic",
    },
    "pro": {
        "price_monthly": 19.99,
        "ai_generations_per_day": 200,
        "projects": 50,
        "storage_gb": 20,
        "export_platforms": ["web", "windows", "macos", "linux", "android"],
        "templates": "all",
        "priority_gpu": True,
        "custom_models": True,
    },
    "team": {
        "price_monthly_per_seat": 29.99,
        "seats_min": 3,
        "ai_generations_per_day": 500,
        "projects": "unlimited",
        "storage_gb": 100,
        "export_platforms": "all",
        "collaboration": True,
        "admin_dashboard": True,
    },
    "enterprise": {
        "price": "custom",
        "private_deployment": True,
        "custom_model_training": True,
        "sso": True,
        "sla": True,
        "dedicated_support": True,
    },
}
```

**验收**：定价页面上线，Stripe/支付宝集成

---

## Phase 4 完成标志

- [ ] 插件 SDK 发布 (npm @godot-forge/plugin-sdk)
- [ ] 至少 3 个社区插件上架
- [ ] 资产市场可用（上架/搜索/下载）
- [ ] 教育版：教程 + 课堂管理
- [ ] 企业版：私有部署文档 + Docker Compose
- [ ] 文档站点上线 (docs.godotforge.dev)
- [ ] 首次 Game Jam 举办
- [ ] 商业化方案上线

---

## 🎉 V1.0 发布清单

- [ ] 所有 Phase 0-4 验收标准通过
- [ ] 安全审计完成 (API 认证、数据加密、输入验证)
- [ ] 性能压测通过 (100 并发用户)
- [ ] E2E 测试覆盖率 > 70%
- [ ] README / CONTRIBUTING / CODE_OF_CONDUCT 完善
- [ ] 产品宣传页 (godotforge.dev) 上线
- [ ] Product Hunt / Hacker News / Reddit r/godot 发布
- [ ] Discord 社区建立
- [ ] 开发者博客首篇文章发布
