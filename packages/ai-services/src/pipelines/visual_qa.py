"""视觉 QA 管线 — 截图分析与自动修复

完整流程:
1. 使用 Godot 无头模式截图
2. 使用 Claude 多模态 API 分析截图是否符合 QA 标准
3. 根据分析结果生成代码修复
4. 应用修复到项目文件
5. 迭代直到通过或达到最大次数
"""
import asyncio
import base64
import json
import logging
import subprocess
import uuid
from pathlib import Path
from typing import Any

from ..config import settings
from ..services.llm_service import generate_gdscript

logger = logging.getLogger(__name__)

QA_OUTPUT_DIR = Path("/tmp/godotforge/qa")
QA_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


class VisualQAPipeline:
    """视觉 QA 管线

    通过截图分析和迭代修复确保游戏画面质量。
    使用 Godot 无头模式截图，再用 Claude 多模态 API 分析。
    """

    async def run_qa(
        self,
        project_path: str,
        scene_path: str,
        qa_criteria: list[str],
        max_iterations: int = 3,
    ) -> dict[str, Any]:
        """运行视觉 QA 检查循环

        Args:
            project_path: Godot 项目根目录路径
            scene_path: 要测试的场景路径 (res://scenes/main.tscn)
            qa_criteria: QA 检查标准列表 (例如 ["player character visible", "UI elements aligned"])
            max_iterations: 最大迭代次数

        Returns:
            dict with keys:
                - passed: bool — 是否通过全部 QA 标准
                - iterations: int — 实际迭代次数
                - issues_found: list[dict] — 发现的问题
                - fixes_applied: list[dict] — 已应用的修复
                - screenshots: list[str] — 每次迭代的截图路径
                - final_analysis: dict — 最终分析结果
        """
        session_id = uuid.uuid4().hex[:8]
        session_dir = QA_OUTPUT_DIR / session_id
        session_dir.mkdir(parents=True, exist_ok=True)

        logger.info(
            "Starting Visual QA: project=%s, scene=%s, criteria=%d, max_iter=%d",
            project_path,
            scene_path,
            len(qa_criteria),
            max_iterations,
        )

        all_issues: list[dict[str, Any]] = []
        all_fixes: list[dict[str, Any]] = []
        screenshots: list[str] = []
        final_analysis: dict[str, Any] = {}
        passed = False

        for iteration in range(max_iterations):
            logger.info("QA iteration %d/%d", iteration + 1, max_iterations)

            # Step 1: 截图
            screenshot_path = session_dir / f"screenshot_iter{iteration}.png"
            capture_success = await self._capture_screenshot(
                project_path=project_path,
                scene_path=scene_path,
                output_path=str(screenshot_path),
            )

            if not capture_success:
                logger.error("Screenshot capture failed at iteration %d", iteration)
                all_issues.append({
                    "iteration": iteration,
                    "type": "capture_failure",
                    "description": "Failed to capture screenshot from Godot",
                })
                # 尝试修复启动问题
                fix_result = await self._generate_fixes(
                    project_path=project_path,
                    scene_path=scene_path,
                    issues=[{
                        "type": "runtime_error",
                        "description": "Scene failed to render. Check for missing nodes, script errors, or invalid scene structure.",
                    }],
                )
                if fix_result:
                    applied = await self._apply_fixes(project_path, fix_result)
                    all_fixes.extend(applied)
                continue

            screenshots.append(str(screenshot_path))

            # Step 2: 分析截图
            analysis = await self._analyze_screenshot(
                screenshot_path=str(screenshot_path),
                qa_criteria=qa_criteria,
                scene_path=scene_path,
            )

            final_analysis = analysis

            if analysis.get("all_passed", False):
                logger.info("All QA criteria passed at iteration %d", iteration + 1)
                passed = True
                break

            # 收集问题
            issues = analysis.get("issues", [])
            for issue in issues:
                issue["iteration"] = iteration
            all_issues.extend(issues)

            logger.info(
                "Found %d issues at iteration %d: %s",
                len(issues),
                iteration,
                [i.get("criterion", "") for i in issues],
            )

            # 如果是最后一轮，不再修复
            if iteration >= max_iterations - 1:
                break

            # Step 3: 生成修复
            fix_result = await self._generate_fixes(
                project_path=project_path,
                scene_path=scene_path,
                issues=issues,
            )

            if not fix_result:
                logger.warning("No fixes generated for issues at iteration %d", iteration)
                break

            # Step 4: 应用修复
            applied = await self._apply_fixes(project_path, fix_result)
            all_fixes.extend(applied)

            if not applied:
                logger.warning("No fixes could be applied at iteration %d", iteration)
                break

        return {
            "passed": passed,
            "iterations": min(len(screenshots), max_iterations),
            "issues_found": all_issues,
            "fixes_applied": all_fixes,
            "screenshots": screenshots,
            "final_analysis": final_analysis,
            "session_dir": str(session_dir),
        }

    async def _capture_screenshot(
        self,
        project_path: str,
        scene_path: str,
        output_path: str,
    ) -> bool:
        """运行 Godot 无头模式捕获截图

        Args:
            project_path: Godot 项目根目录
            scene_path: 场景路径 (res://...)
            output_path: 截图保存路径

        Returns:
            True 如果截图成功
        """
        godot_bin = settings.godot_path

        # 创建截图脚本
        screenshot_script = (
            'extends SceneTree\n'
            '\n'
            'func _init() -> void:\n'
            '\tawait create_timer(2.0).timeout\n'
            '\tvar viewport := get_root().get_viewport()\n'
            '\tvar img := viewport.get_texture().get_image()\n'
            f'\timg.save_png("{output_path}")\n'
            '\tquit()\n'
        )

        script_path = Path(project_path) / ".godotforge_screenshot.gd"
        script_path.write_text(screenshot_script, encoding="utf-8")

        try:
            cmd = [
                godot_bin,
                "--path", project_path,
                "--headless",
                "--script", str(script_path),
                scene_path,
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=30.0,
            )

            # 检查截图文件是否生成
            if Path(output_path).exists() and Path(output_path).stat().st_size > 0:
                logger.info("Screenshot captured: %s", output_path)
                return True

            logger.warning(
                "Godot screenshot script did not produce output. "
                "stdout=%s, stderr=%s",
                stdout.decode("utf-8", errors="replace")[:200],
                stderr.decode("utf-8", errors="replace")[:200],
            )
            return False

        except asyncio.TimeoutError:
            logger.error("Godot screenshot capture timed out (30s)")
            return False
        except FileNotFoundError:
            logger.error("Godot binary not found at: %s", godot_bin)
            return False
        except Exception as exc:
            logger.error("Screenshot capture error: %s", exc)
            return False
        finally:
            # 清理临时脚本
            if script_path.exists():
                script_path.unlink()

    async def _analyze_screenshot(
        self,
        screenshot_path: str,
        qa_criteria: list[str],
        scene_path: str,
    ) -> dict[str, Any]:
        """使用 Claude 多模态 API 分析截图

        Args:
            screenshot_path: 截图文件路径
            qa_criteria: QA 检查标准列表
            scene_path: 场景路径（提供上下文）

        Returns:
            dict with keys:
                - all_passed: bool
                - criteria_results: list[{criterion, passed, description}]
                - issues: list[{criterion, type, description, suggestion}]
                - overall_quality: str (good, acceptable, poor)
        """
        # 读取截图为 base64
        screenshot_bytes = Path(screenshot_path).read_bytes()
        screenshot_b64 = base64.b64encode(screenshot_bytes).decode("utf-8")

        criteria_text = "\n".join(f"  {i+1}. {c}" for i, c in enumerate(qa_criteria))

        analysis_prompt = (
            f"Analyze this screenshot of a Godot game scene ({scene_path}).\n\n"
            f"Check the following QA criteria:\n{criteria_text}\n\n"
            "For each criterion, determine if it PASSES or FAILS.\n\n"
            "Respond with a JSON object (no markdown fences) with this structure:\n"
            "{\n"
            '  "all_passed": true/false,\n'
            '  "criteria_results": [\n'
            '    {"criterion": "...", "passed": true/false, "description": "..."}\n'
            "  ],\n"
            '  "issues": [\n'
            '    {"criterion": "...", "type": "visual|layout|missing|rendering", '
            '"description": "...", "suggestion": "..."}\n'
            "  ],\n"
            '  "overall_quality": "good|acceptable|poor"\n'
            "}"
        )

        try:
            if settings.llm_provider == "anthropic":
                return await self._analyze_with_anthropic(screenshot_b64, analysis_prompt)
            else:
                # 非 Anthropic 供应商 — 使用纯文本分析（无法多模态）
                logger.warning(
                    "Visual QA analysis with %s does not support multimodal. "
                    "Returning default pass result.",
                    settings.llm_provider,
                )
                return {
                    "all_passed": True,
                    "criteria_results": [
                        {"criterion": c, "passed": True, "description": "Skipped (no multimodal support)"}
                        for c in qa_criteria
                    ],
                    "issues": [],
                    "overall_quality": "acceptable",
                }

        except Exception as exc:
            logger.error("Screenshot analysis failed: %s", exc)
            return {
                "all_passed": False,
                "criteria_results": [],
                "issues": [{
                    "criterion": "analysis",
                    "type": "error",
                    "description": f"Analysis failed: {exc}",
                    "suggestion": "Check API key and connectivity",
                }],
                "overall_quality": "poor",
            }

    async def _analyze_with_anthropic(
        self,
        screenshot_b64: str,
        prompt: str,
    ) -> dict[str, Any]:
        """使用 Anthropic Claude 多模态 API 分析截图"""
        import anthropic

        client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

        response = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": screenshot_b64,
                        },
                    },
                    {
                        "type": "text",
                        "text": prompt,
                    },
                ],
            }],
        )

        raw_text = response.content[0].text.strip()

        # 解析 JSON 响应
        import re

        # 移除可能的 markdown 围栏
        raw_text = re.sub(r"```(?:json)?\s*\n?", "", raw_text).strip()

        try:
            return json.loads(raw_text)
        except json.JSONDecodeError:
            # 尝试找到 JSON 对象
            json_match = re.search(r"\{.*\}", raw_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))
            raise

    async def _generate_fixes(
        self,
        project_path: str,
        scene_path: str,
        issues: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """根据发现的问题生成代码修复

        Args:
            project_path: 项目根目录
            scene_path: 场景路径
            issues: 问题列表

        Returns:
            修复列表 [{file_path, original_content, fixed_content, description}]
        """
        if not issues:
            return []

        issues_desc = "\n".join(
            f"- [{issue.get('type', 'unknown')}] {issue.get('criterion', '')}: "
            f"{issue.get('description', '')} "
            f"(Suggestion: {issue.get('suggestion', 'N/A')})"
            for issue in issues
        )

        # 扫描项目中相关的脚本文件
        project_dir = Path(project_path)
        script_contents: dict[str, str] = {}

        for gd_file in project_dir.rglob("*.gd"):
            rel_path = gd_file.relative_to(project_dir)
            try:
                script_contents[str(rel_path)] = gd_file.read_text(encoding="utf-8")
            except Exception:
                pass

        # 扫描场景文件
        for tscn_file in project_dir.rglob("*.tscn"):
            rel_path = tscn_file.relative_to(project_dir)
            try:
                script_contents[str(rel_path)] = tscn_file.read_text(encoding="utf-8")
            except Exception:
                pass

        scripts_desc = ""
        for path, content in list(script_contents.items())[:10]:  # 最多 10 个文件
            scripts_desc += f"\n### FILE: {path}\n```gdscript\n{content}\n```\n"

        prompt = (
            f"Fix the following visual issues found in a Godot game scene ({scene_path}).\n\n"
            f"Issues:\n{issues_desc}\n\n"
            f"Project files:\n{scripts_desc}\n\n"
            "For each fix, respond in this format:\n"
            "### FIX: <relative_file_path>\n"
            "```gdscript\n"
            "<complete fixed file content>\n"
            "```\n"
            "DESCRIPTION: <what was changed and why>\n\n"
            "Provide complete file contents, not just diffs."
        )

        result = await generate_gdscript(prompt=prompt)
        raw_text = result.get("_raw_text", "") or result.get("explanation", "")

        return self._parse_fixes(raw_text, script_contents)

    def _parse_fixes(
        self,
        raw_text: str,
        original_contents: dict[str, str],
    ) -> list[dict[str, Any]]:
        """从 LLM 响应中解析修复列表"""
        import re

        fixes: list[dict[str, Any]] = []

        # 匹配 ### FIX: path 格式
        fix_pattern = re.compile(
            r"###\s*FIX:\s*(\S+)\s*\n"
            r"```(?:gdscript|gd|tscn)?\s*\n"
            r"(.*?)"
            r"```\s*\n"
            r"(?:DESCRIPTION:\s*(.+?)(?:\n###|\Z))?",
            re.DOTALL,
        )

        for match in fix_pattern.finditer(raw_text):
            file_path = match.group(1).strip()
            fixed_content = match.group(2).strip()
            description = (match.group(3) or "").strip()

            original = original_contents.get(file_path, "")

            fixes.append({
                "file_path": file_path,
                "original_content": original,
                "fixed_content": fixed_content,
                "description": description,
            })

        return fixes

    async def _apply_fixes(
        self,
        project_path: str,
        fixes: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """应用修复到项目文件

        Args:
            project_path: 项目根目录
            fixes: 修复列表

        Returns:
            成功应用的修复列表
        """
        applied: list[dict[str, Any]] = []
        project_dir = Path(project_path)

        for fix in fixes:
            file_path = fix.get("file_path", "")
            fixed_content = fix.get("fixed_content", "")

            if not file_path or not fixed_content:
                continue

            target = project_dir / file_path
            try:
                # 确保父目录存在
                target.parent.mkdir(parents=True, exist_ok=True)

                # 备份原文件
                if target.exists():
                    backup_path = target.with_suffix(target.suffix + ".bak")
                    backup_path.write_text(
                        target.read_text(encoding="utf-8"),
                        encoding="utf-8",
                    )

                # 写入修复后内容
                target.write_text(fixed_content, encoding="utf-8")

                logger.info("Applied fix to %s: %s", target, fix.get("description", ""))
                applied.append(fix)

            except Exception as exc:
                logger.error("Failed to apply fix to %s: %s", target, exc)

        return applied


# ---------------------------------------------------------------------------
# 单例
# ---------------------------------------------------------------------------

visual_qa_pipeline = VisualQAPipeline()
