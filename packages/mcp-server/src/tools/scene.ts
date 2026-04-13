import { GodotConnection } from "../transport/websocket.js";
import { RegisteredTool } from "./index.js";

export function registerSceneTools(godot: GodotConnection): RegisteredTool[] {
  return [
    {
      definition: { name: "create_scene", description: "创建一个新场景", inputSchema: {
        type: "object", properties: {
          name: { type: "string", description: "场景名称" },
          root_type: { type: "string", description: "根节点类型 (Node2D/Node3D/Control)" },
        }, required: ["name", "root_type"],
      }},
      handler: async (args) => godot.send("create_scene", args),
    },
    {
      definition: { name: "open_scene", description: "打开指定场景文件", inputSchema: {
        type: "object", properties: { path: { type: "string", description: "场景路径 (res://...)" } }, required: ["path"],
      }},
      handler: async (args) => godot.send("open_scene", args),
    },
    {
      definition: { name: "save_scene", description: "保存当前场景", inputSchema: {
        type: "object", properties: { path: { type: "string", description: "保存路径 (可选)" } },
      }},
      handler: async (args) => godot.send("save_scene", args),
    },
    {
      definition: { name: "save_scene_as", description: "将当前场景另存为", inputSchema: {
        type: "object", properties: { path: { type: "string", description: "新保存路径" } }, required: ["path"],
      }},
      handler: async (args) => godot.send("save_scene_as", args),
    },
    {
      definition: { name: "close_scene", description: "关闭指定场景", inputSchema: {
        type: "object", properties: { index: { type: "number", description: "场景索引 (可选, 默认当前)" } },
      }},
      handler: async (args) => godot.send("close_scene", args),
    },
    {
      definition: { name: "get_scene_tree", description: "获取当前场景的节点树结构", inputSchema: { type: "object", properties: {} } },
      handler: async () => godot.send("get_scene_tree"),
    },
    {
      definition: { name: "get_scene_tree_flat", description: "获取场景树的扁平列表", inputSchema: { type: "object", properties: {} } },
      handler: async () => godot.send("get_scene_tree_flat"),
    },
    {
      definition: { name: "get_open_scenes", description: "获取所有已打开的场景列表", inputSchema: { type: "object", properties: {} } },
      handler: async () => godot.send("get_open_scenes"),
    },
    {
      definition: { name: "switch_scene", description: "切换到指定已打开的场景", inputSchema: {
        type: "object", properties: { index: { type: "number" } }, required: ["index"],
      }},
      handler: async (args) => godot.send("switch_scene", args),
    },
    {
      definition: { name: "duplicate_scene", description: "复制当前场景", inputSchema: {
        type: "object", properties: { new_name: { type: "string" } }, required: ["new_name"],
      }},
      handler: async (args) => godot.send("duplicate_scene", args),
    },
    {
      definition: { name: "instantiate_scene", description: "将打包场景实例化到当前场景", inputSchema: {
        type: "object", properties: {
          scene_path: { type: "string" }, parent_path: { type: "string" }, node_name: { type: "string" },
        }, required: ["scene_path"],
      }},
      handler: async (args) => godot.send("instantiate_scene", args),
    },
    {
      definition: { name: "pack_scene", description: "将节点子树打包为场景文件", inputSchema: {
        type: "object", properties: { node_path: { type: "string" }, save_path: { type: "string" } }, required: ["node_path", "save_path"],
      }},
      handler: async (args) => godot.send("pack_scene", args),
    },
    {
      definition: { name: "unpack_scene", description: "将实例化场景展开为独立节点", inputSchema: {
        type: "object", properties: { node_path: { type: "string" } }, required: ["node_path"],
      }},
      handler: async (args) => godot.send("unpack_scene", args),
    },
    {
      definition: { name: "get_scene_resources", description: "获取场景依赖的所有资源", inputSchema: {
        type: "object", properties: { scene_path: { type: "string" } },
      }},
      handler: async (args) => godot.send("get_scene_resources", args),
    },
    {
      definition: { name: "reload_scene", description: "重新加载当前场景", inputSchema: { type: "object", properties: {} } },
      handler: async () => godot.send("reload_scene"),
    },
  ];
}
