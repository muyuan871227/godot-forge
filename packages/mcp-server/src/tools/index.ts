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
