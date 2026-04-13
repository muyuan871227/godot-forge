import { GodotConnection } from "../transport/websocket.js";
import { RegisteredTool } from "./index.js";

export function registerProjectTools(godot: GodotConnection): RegisteredTool[] {
  return [
    {
      definition: {
        name: "get_project_info",
        description: "获取当前 Godot 项目的基本信息",
        inputSchema: { type: "object", properties: {}, required: [] },
      },
      handler: async () => godot.send("get_project_info"),
    },
    {
      definition: {
        name: "list_scenes",
        description: "列出项目中所有场景文件 (.tscn/.scn)",
        inputSchema: {
          type: "object",
          properties: {
            directory: { type: "string", description: "搜索目录 (默认 res://)" },
          },
        },
      },
      handler: async (args) => godot.send("list_scenes", args),
    },
    {
      definition: {
        name: "list_scripts",
        description: "列出项目中所有脚本文件 (.gd/.cs)",
        inputSchema: {
          type: "object",
          properties: {
            directory: { type: "string" },
            filter: { type: "string", description: "文件名过滤 (支持通配符)" },
          },
        },
      },
      handler: async (args) => godot.send("list_scripts", args),
    },
    {
      definition: {
        name: "list_resources",
        description: "列出项目中所有资源文件",
        inputSchema: {
          type: "object",
          properties: {
            directory: { type: "string" },
            type: { type: "string", description: "资源类型过滤 (如 texture, audio)" },
          },
        },
      },
      handler: async (args) => godot.send("list_resources", args),
    },
    {
      definition: {
        name: "get_project_settings",
        description: "获取项目设置",
        inputSchema: {
          type: "object",
          properties: {
            category: { type: "string", description: "设置类别 (如 application, rendering)" },
          },
        },
      },
      handler: async (args) => godot.send("get_project_settings", args),
    },
    {
      definition: {
        name: "set_project_setting",
        description: "设置项目配置项",
        inputSchema: {
          type: "object",
          properties: {
            key: { type: "string", description: "设置键 (如 application/config/name)" },
            value: { description: "设置值" },
          },
          required: ["key", "value"],
        },
      },
      handler: async (args) => godot.send("set_project_setting", args),
    },
    {
      definition: {
        name: "rescan_filesystem",
        description: "重新扫描项目文件系统",
        inputSchema: { type: "object", properties: {}, required: [] },
      },
      handler: async () => godot.send("rescan_filesystem"),
    },
    {
      definition: {
        name: "get_godot_version",
        description: "获取当前 Godot 引擎版本信息",
        inputSchema: { type: "object", properties: {}, required: [] },
      },
      handler: async () => godot.send("get_godot_version"),
    },
  ];
}
