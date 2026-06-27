# Phase 2 — 全链路 AI 资产管线 (预计 4 个月)

## 概述
将 AI 资产生成能力从基础扩展到生产级：3D 模型、精灵图集、Tilemap、BGM、视觉 QA 闭环。

---

## Task 2.1 — 3D 模型生成集成

### 2.1.1 Hunyuan3D 2.1 本地部署

```bash
# 在 GPU 服务器上部署 Hunyuan3D
cd /opt/models
git clone https://github.com/Tencent-Hunyuan/Hunyuan3D-2.1.git
cd Hunyuan3D-2.1
pip install torch==2.5.1 torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
pip install -r requirements.txt
cd hy3dpaint/custom_rasterizer && pip install -e . && cd ../..
cd hy3dpaint/DifferentiableRenderer && bash compile_mesh_painter.sh && cd ../..

# 下载模型权重 (~10GB)
huggingface-cli download tencent/Hunyuan3D-2.1 --local-dir ./weights

# 验证：启动 Gradio demo
python3 gradio_app.py --model_path tencent/Hunyuan3D-2.1 --low_vram_mode
```

### 2.1.2 3D 生成服务封装

创建 `ai-services/src/providers/hunyuan3d.py`：

```python
"""Hunyuan3D 2.1 — 文字/图片→3D模型（带PBR贴图）"""
import sys
sys.path.insert(0, '/opt/models/Hunyuan3D-2.1/hy3dshape')
sys.path.insert(0, '/opt/models/Hunyuan3D-2.1/hy3dpaint')

from hy3dshape.pipelines import Hunyuan3DDiTFlowMatchingPipeline
from hy3dpaint.textureGenPipeline import Hunyuan3DPaintPipeline, Hunyuan3DPaintConfig
import trimesh
import uuid
from pathlib import Path

class Hunyuan3DService:
    def __init__(self):
        self.shape_pipeline = None
        self.paint_pipeline = None
        self._loaded = False
    
    def _ensure_loaded(self):
        if not self._loaded:
            self.shape_pipeline = Hunyuan3DDiTFlowMatchingPipeline.from_pretrained(
                'tencent/Hunyuan3D-2.1'
            )
            self.paint_pipeline = Hunyuan3DPaintPipeline(
                Hunyuan3DPaintConfig(max_num_view=6, resolution=512)
            )
            self._loaded = True
    
    async def generate_from_image(self, image_path: str, with_texture: bool = True) -> dict:
        """从参考图生成 3D 模型"""
        self._ensure_loaded()
        
        # Stage 1: 生成几何体
        mesh = self.shape_pipeline(image=image_path)[0]
        
        # Stage 2: 生成纹理 (可选)
        if with_texture:
            mesh = self.paint_pipeline(mesh, image_path=image_path)
        
        # 导出为 GLB (Godot 原生支持)
        output_id = uuid.uuid4().hex[:8]
        output_dir = Path(f"/tmp/godotforge/models/{output_id}")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        glb_path = str(output_dir / "model.glb")
        mesh.export(glb_path)
        
        return {
            "model_path": glb_path,
            "format": "glb",
            "vertices": len(mesh.vertices),
            "faces": len(mesh.faces),
            "has_texture": with_texture,
        }
    
    async def generate_from_text(self, prompt: str, with_texture: bool = True) -> dict:
        """从文字描述生成 3D 模型 (需要先文生图，再图生3D)"""
        from .image_service import generate_image
        
        # Step 1: 文字→参考图
        img_result = await generate_image(
            prompt=f"3D model reference, {prompt}, white background, studio lighting, multiple angles",
            style="realistic",
            width=512,
            height=512,
        )
        
        # Step 2: 参考图→3D
        import base64
        img_path = f"/tmp/godotforge/ref_{uuid.uuid4().hex[:8]}.png"
        with open(img_path, "wb") as f:
            f.write(base64.b64decode(img_result["image_base64"]))
        
        return await self.generate_from_image(img_path, with_texture)

hunyuan3d_service = Hunyuan3DService()
```

### 2.1.3 TripoSR 快速原型 (备选)

```python
"""TripoSR — 单图→3D，<5秒极速"""
import torch
from tsr.system import TSR

class TripoSRService:
    def __init__(self):
        self.model = TSR.from_pretrained(
            "stabilityai/TripoSR",
            config_name="config.yaml",
            weight_name="model.ckpt",
        )
        self.model.to("cuda" if torch.cuda.is_available() else "cpu")
    
    async def generate(self, image_path: str) -> dict:
        from PIL import Image
        image = Image.open(image_path)
        
        with torch.no_grad():
            scene_codes = self.model([image], device="cuda")
        
        meshes = self.model.extract_mesh(scene_codes, resolution=256)
        mesh = meshes[0]
        
        output_path = f"/tmp/godotforge/triposr_{uuid.uuid4().hex[:8]}.glb"
        mesh.export(output_path)
        
        return {"model_path": output_path, "format": "glb"}
```

### 2.1.4 3D 模型路由

创建 `ai-services/src/routers/modelgen.py`：

```python
router = APIRouter()

class Model3DRequest(BaseModel):
    prompt: str = ""
    image_base64: str = ""  # 或提供参考图
    provider: str = "hunyuan3d"  # hunyuan3d | triposr
    with_texture: bool = True
    output_format: str = "glb"  # glb | obj | fbx

@router.post("/generate")
async def generate_3d_model(req: Model3DRequest):
    if req.provider == "hunyuan3d":
        if req.image_base64:
            return await hunyuan3d_service.generate_from_image(...)
        else:
            return await hunyuan3d_service.generate_from_text(req.prompt)
    elif req.provider == "triposr":
        return await triposr_service.generate(...)

@router.post("/texture")
async def retexture_model(model_path: str, style_prompt: str):
    """为已有模型重新生成纹理"""
    ...

@router.post("/optimize")
async def optimize_model(model_path: str, target_faces: int = 5000):
    """优化模型面数 (适配移动端)"""
    import trimesh
    mesh = trimesh.load(model_path)
    # 使用 simplify_quadric_decimation 减面
    simplified = mesh.simplify_quadric_decimation(target_faces)
    ...
```

**验收**：文字/图片→GLB 模型，可在 Godot 中直接导入

---

## Task 2.2 — 精灵图集自动生成管线

创建 `ai-services/src/pipelines/sprite_sheet.py`：

```python
"""完整精灵图集生成管线
输入: 角色描述 + 动画列表
输出: Godot 可用的 SpriteFrames 资源
"""

class SpriteSheetPipeline:
    """
    Pipeline 步骤:
    1. 生成角色参考图 (单帧正面)
    2. 使用 img2img 生成各动画帧 (保持角色一致性)
    3. 自动去背景
    4. 切片并对齐
    5. 生成 Godot SpriteFrames .tres 文件
    """
    
    async def generate(
        self,
        character_desc: str,
        animations: dict[str, int],  # {"idle": 4, "run": 6, "jump": 3}
        style: str = "pixel_art",
        frame_size: tuple = (64, 64),
    ) -> dict:
        from ..services.image_service import generate_image
        from PIL import Image
        import io, base64
        
        # Step 1: 生成参考角色
        ref_result = await generate_image(
            prompt=f"{character_desc}, character design, front view, T-pose, game sprite",
            style=style,
            width=frame_size[0] * 2,
            height=frame_size[1] * 2,
            transparent_bg=True,
        )
        
        all_frames = {}
        
        for anim_name, frame_count in animations.items():
            # Step 2: 为每个动画生成帧
            frames = []
            for i in range(frame_count):
                phase = i / frame_count
                anim_prompt = self._get_animation_prompt(
                    character_desc, anim_name, phase, style
                )
                
                frame_result = await generate_image(
                    prompt=anim_prompt,
                    style=style,
                    width=frame_size[0],
                    height=frame_size[1],
                    transparent_bg=True,
                )
                frames.append(frame_result["image_base64"])
            
            all_frames[anim_name] = frames
        
        # Step 3: 组合为精灵图集
        sheet = self._combine_to_sheet(all_frames, frame_size)
        
        # Step 4: 生成 Godot SpriteFrames 资源
        tres_content = self._generate_sprite_frames_tres(
            all_frames, frame_size
        )
        
        return {
            "sprite_sheet_base64": sheet,
            "sprite_frames_tres": tres_content,
            "animations": {k: len(v) for k, v in all_frames.items()},
            "frame_size": frame_size,
        }
    
    def _get_animation_prompt(self, desc, anim, phase, style):
        prompts = {
            "idle": f"{desc}, standing idle, slight breathing motion, phase {phase:.1f}",
            "run": f"{desc}, running cycle, leg position {phase:.1f}, dynamic pose",
            "jump": f"{desc}, jumping, {'ascending' if phase < 0.5 else 'descending'}, airborne",
            "attack": f"{desc}, attack swing, {'windup' if phase < 0.3 else 'strike' if phase < 0.7 else 'recovery'}",
            "death": f"{desc}, falling down, collapse phase {phase:.1f}",
        }
        base = prompts.get(anim, f"{desc}, {anim} animation, phase {phase:.1f}")
        return f"{base}, sprite, game asset, {style}"
    
    def _generate_sprite_frames_tres(self, all_frames, frame_size):
        """生成 Godot 的 .tres SpriteFrames 资源文件"""
        # Godot SpriteFrames 格式
        tres = '[gd_resource type="SpriteFrames" format=3]\n\n'
        tres += '[resource]\n'
        
        animations_data = []
        for anim_name, frames in all_frames.items():
            anim = {
                "name": anim_name,
                "speed": 8.0,
                "loop": anim_name != "death",
                "frames": []
            }
            for i, _ in enumerate(frames):
                anim["frames"].append({
                    "texture": f"res://assets/sprites/{anim_name}_{i}.png",
                    "duration": 1.0,
                })
            animations_data.append(anim)
        
        # 序列化为 Godot 资源格式
        # (实际实现需要精确的 .tres 语法)
        return tres

sprite_sheet_pipeline = SpriteSheetPipeline()
```

**验收**：输入角色描述 → 输出完整精灵图集 + `.tres` 资源文件

---

## Task 2.3 — Tilemap 生成管线

创建 `ai-services/src/pipelines/tilemap.py`：

```python
"""Tilemap 自动生成管线
输入: 主题描述 + 地图尺寸
输出: Godot TileSet + TileMap 场景
"""

class TilemapPipeline:
    async def generate(
        self,
        theme: str,          # "forest", "dungeon", "snow"
        map_width: int = 30,
        map_height: int = 20,
        tile_size: int = 16,
        style: str = "pixel_art",
    ) -> dict:
        # Step 1: 生成 Tileset 贴图
        tileset_img = await self._generate_tileset(theme, tile_size, style)
        
        # Step 2: 使用 AI 生成地图布局
        layout = await self._generate_map_layout(theme, map_width, map_height)
        
        # Step 3: 生成 Godot TileSet 资源
        tileset_tres = self._generate_tileset_resource(tile_size)
        
        # Step 4: 生成 TileMap 场景
        tilemap_tscn = self._generate_tilemap_scene(layout, map_width, map_height)
        
        return {
            "tileset_image": tileset_img,
            "tileset_tres": tileset_tres,
            "tilemap_tscn": tilemap_tscn,
            "layout": layout,
        }
    
    async def _generate_map_layout(self, theme, width, height):
        """使用 LLM 生成地图布局 (JSON 二维数组)"""
        from ..services.llm_service import generate_gdscript
        
        prompt = f"""Generate a 2D tile map layout for a {theme} themed level.
Map size: {width}x{height}
Use these tile IDs:
- 0: empty/sky
- 1: ground
- 2: platform
- 3: wall
- 4: decoration (tree/rock/etc)
- 5: hazard (spikes/lava)
- 6: collectible position

Return ONLY a JSON 2D array, no other text.
Make it fun and playable as a platformer level.
Include platforms at varying heights, some hazards, and collectibles."""
        
        result = await generate_gdscript(prompt)
        import json
        return json.loads(result["code"])
```

**验收**：输入主题 → 输出完整 TileSet + TileMap 可直接在 Godot 中打开

---

## Task 2.4 — 视觉 QA 闭环

创建 `ai-services/src/pipelines/visual_qa.py`：

```python
"""视觉质量保证系统
1. 自动截图运行中的游戏
2. 使用多模态 LLM 分析截图
3. 发现问题 → 生成修复 → 重新截图
4. 循环直到通过验收标准
"""

class VisualQAPipeline:
    async def run_qa(
        self,
        project_path: str,
        scene_path: str,
        qa_criteria: list[str],
        max_iterations: int = 3,
    ) -> dict:
        results = []
        
        for i in range(max_iterations):
            # Step 1: 运行场景并截图
            screenshot = await self._capture_screenshot(project_path, scene_path)
            
            # Step 2: AI 分析截图
            analysis = await self._analyze_screenshot(screenshot, qa_criteria)
            
            results.append({
                "iteration": i + 1,
                "screenshot": screenshot,
                "analysis": analysis,
                "passed": analysis["all_passed"],
            })
            
            if analysis["all_passed"]:
                break
            
            # Step 3: 生成修复
            fixes = await self._generate_fixes(analysis["issues"])
            
            # Step 4: 应用修复
            await self._apply_fixes(project_path, fixes)
        
        return {
            "passed": results[-1]["passed"] if results else False,
            "iterations": len(results),
            "details": results,
        }
    
    async def _capture_screenshot(self, project_path, scene_path):
        """使用 Godot 无头模式截图"""
        import subprocess
        screenshot_script = f'''
extends SceneTree
func _init():
    var viewport = root.get_viewport()
    await RenderingServer.frame_post_draw
    var img = viewport.get_texture().get_image()
    img.save_png("user://screenshot.png")
    quit()
'''
        # 写入临时脚本并运行
        ...
    
    async def _analyze_screenshot(self, screenshot_path, criteria):
        """使用多模态 LLM 分析截图"""
        import anthropic, base64
        
        with open(screenshot_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode()
        
        client = anthropic.AsyncAnthropic()
        response = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2048,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": img_b64}},
                    {"type": "text", "text": f"""Analyze this game screenshot.
Check these quality criteria:
{chr(10).join(f'- {c}' for c in criteria)}

For each criterion, respond with:
- PASS or FAIL
- Brief explanation
- If FAIL, specific fix suggestion

Respond in JSON format."""},
                ],
            }],
        )
        
        import json
        return json.loads(response.content[0].text)
```

**验收**：自动截图→分析→修复循环可运行，发现并修复至少一个视觉问题

---

## Task 2.5 — GDScript 模型微调

### 2.5.1 数据集构建

```bash
# 使用 godot-dodo 方法构建微调数据集
git clone https://github.com/minosvasilias/godot-dodo.git /opt/godot-dodo

# 配置
export GITHUB_TOKEN=ghp_...
export OPENAI_API_KEY=sk-...

# 抓取 Godot 4.x 项目的 GDScript 代码
cd /opt/godot-dodo
python data/scrape.py --version 4 --max_repos 500 --output data/godot4_raw.json

# 生成指令-代码对
python data/generate_instructions.py --input data/godot4_raw.json --output data/godot4_instruct_80k.json

# 数据质量过滤
python data/filter.py --input data/godot4_instruct_80k.json --min_code_length 50 --max_code_length 2000
```

### 2.5.2 微调 (使用 LoRA)

```python
# 使用 Unsloth 进行高效微调
from unsloth import FastLanguageModel

model, tokenizer = FastLanguageModel.from_pretrained(
    model_name="deepseek-ai/deepseek-coder-6.7b-instruct",
    max_seq_length=4096,
    load_in_4bit=True,
)

model = FastLanguageModel.get_peft_model(
    model,
    r=16,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
    lora_alpha=32,
    lora_dropout=0.05,
)

# 训练
from trl import SFTTrainer
trainer = SFTTrainer(
    model=model,
    train_dataset=dataset,
    max_seq_length=4096,
    args=TrainingArguments(
        output_dir="./godotforge-coder",
        num_train_epochs=3,
        per_device_train_batch_size=4,
        learning_rate=2e-5,
    ),
)
trainer.train()

# 导出为 GGUF (供 Ollama 使用)
model.save_pretrained_gguf("godotforge-coder-gguf", tokenizer, quantization_method="q5_k_m")
```

### 2.5.3 集成到 Ollama

```bash
# 创建 Modelfile
cat > Modelfile << 'EOF'
FROM ./godotforge-coder-gguf/unsloth.Q5_K_M.gguf
PARAMETER temperature 0.3
PARAMETER top_p 0.9
SYSTEM "You are GodotForge Coder, an expert in GDScript for Godot 4.x."
EOF

# 注册到 Ollama
ollama create godotforge-coder -f Modelfile

# 测试
ollama run godotforge-coder "Write a CharacterBody2D movement script with dash ability"
```

**验收**：微调模型在 GDScript 生成测试集上准确率高于 Claude Sonnet 基线

---

## Task 2.6 — 完整 "文字→游戏" 主管线

创建 `ai-services/src/pipelines/game_from_text.py`：

```python
"""主管线：一句话→完整可运行游戏"""

class GameFromTextPipeline:
    """
    流程:
    1. 解析游戏描述 → 设计文档 (LLM)
    2. 生成项目结构 → 场景/脚本列表 (LLM)
    3. 逐个生成场景和脚本 (LLM)
    4. 生成美术资产 (Image Gen)
    5. 生成音频资产 (Audio Gen)
    6. 组装项目 → 写入文件
    7. 运行测试 → 视觉 QA
    8. 迭代修复
    """
    
    async def generate(self, game_description: str) -> dict:
        # Step 1: 设计文档
        design = await self._generate_design_doc(game_description)
        
        # Step 2: 项目规划
        plan = await self._plan_project_structure(design)
        
        # Step 3: 生成代码
        code_files = await self._generate_all_code(plan)
        
        # Step 4: 生成资产
        assets = await self._generate_all_assets(plan)
        
        # Step 5: 组装
        project = await self._assemble_project(plan, code_files, assets)
        
        # Step 6: 测试与 QA
        qa_result = await self._run_qa(project)
        
        return {
            "project_path": project["path"],
            "design_doc": design,
            "files_created": len(code_files) + len(assets),
            "qa_passed": qa_result["passed"],
        }
```

**验收**：输入 "A 2D platformer with a knight character collecting coins" → 输出可运行的 Godot 项目

---

## Phase 2 完成标志

- [ ] 3D 模型生成：文字/图片→GLB，可导入 Godot
- [ ] 精灵图集管线：生成多动画帧的角色图集
- [ ] Tilemap 管线：自动生成关卡布局
- [ ] 视觉 QA：自动截图→分析→修复闭环
- [ ] GDScript 微调模型上线 Ollama
- [ ] "文字→游戏" 主管线端到端可运行
- [ ] 所有 API 有 Swagger 文档

**下一步**：执行 `docs/phases/phase3-platform.md`
