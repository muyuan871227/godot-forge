import { GodotConnection } from "../transport/websocket.js";
import { RegisteredTool } from "./index.js";

export function registerScriptTools(godot: GodotConnection): RegisteredTool[] {
  return [
    { definition: { name: "create_script", description: "创建并附加 GDScript 到节点", inputSchema: { type: "object", properties: { node_path: { type: "string" }, script_path: { type: "string" }, content: { type: "string" } }, required: ["node_path", "script_path", "content"] } }, handler: async (args) => godot.send("create_script", args) },
    { definition: { name: "read_script", description: "读取脚本文件内容", inputSchema: { type: "object", properties: { path: { type: "string" } }, required: ["path"] } }, handler: async (args) => godot.send("read_script", args) },
    { definition: { name: "update_script", description: "更新脚本文件内容", inputSchema: { type: "object", properties: { path: { type: "string" }, content: { type: "string" } }, required: ["path", "content"] } }, handler: async (args) => godot.send("update_script", args) },
    { definition: { name: "delete_script", description: "删除脚本文件", inputSchema: { type: "object", properties: { path: { type: "string" } }, required: ["path"] } }, handler: async (args) => godot.send("delete_script", args) },
    { definition: { name: "attach_script", description: "将已有脚本附加到节点", inputSchema: { type: "object", properties: { node_path: { type: "string" }, script_path: { type: "string" } }, required: ["node_path", "script_path"] } }, handler: async (args) => godot.send("attach_script", args) },
    { definition: { name: "detach_script", description: "从节点移除脚本", inputSchema: { type: "object", properties: { node_path: { type: "string" } }, required: ["node_path"] } }, handler: async (args) => godot.send("detach_script", args) },
    { definition: { name: "get_script_errors", description: "获取当前项目的脚本错误", inputSchema: { type: "object", properties: {} } }, handler: async () => godot.send("get_script_errors") },
    { definition: { name: "get_open_script", description: "获取当前打开的脚本信息", inputSchema: { type: "object", properties: {} } }, handler: async () => godot.send("get_open_script") },
    { definition: { name: "set_open_script", description: "在编辑器中打开指定脚本", inputSchema: { type: "object", properties: { path: { type: "string" }, line: { type: "number" } }, required: ["path"] } }, handler: async (args) => godot.send("set_open_script", args) },
    { definition: { name: "search_in_scripts", description: "在所有脚本中搜索文本", inputSchema: { type: "object", properties: { query: { type: "string" }, regex: { type: "boolean" } }, required: ["query"] } }, handler: async (args) => godot.send("search_in_scripts", args) },
    { definition: { name: "replace_in_scripts", description: "在所有脚本中替换文本", inputSchema: { type: "object", properties: { search: { type: "string" }, replace: { type: "string" }, regex: { type: "boolean" } }, required: ["search", "replace"] } }, handler: async (args) => godot.send("replace_in_scripts", args) },
    { definition: { name: "format_script", description: "格式化 GDScript 代码", inputSchema: { type: "object", properties: { path: { type: "string" } }, required: ["path"] } }, handler: async (args) => godot.send("format_script", args) },
  ];
}
