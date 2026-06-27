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
echo ""
echo "--- Testing Code Generation ---"
curl -s -X POST http://localhost:8100/api/v1/codegen/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Create a simple 2D player controller with WASD movement, 200 pixels/sec speed, and a jump with gravity",
    "godot_version": "4.4"
  }' | python3 -m json.tool

# 3. 测试健康检查
echo ""
echo "--- Health Check ---"
curl -s http://localhost:8100/health | python3 -m json.tool

# 4. 清理
kill $AI_PID 2>/dev/null
echo ""
echo "=== POC Test Complete ==="
