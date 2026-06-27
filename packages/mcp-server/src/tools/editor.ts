import { GodotConnection } from "../transport/websocket.js";
import { RegisteredTool } from "./index.js";

export function registerEditorTools(godot: GodotConnection): RegisteredTool[] {
  return [
    { definition: { name: "get_editor_state", description: "获取编辑器当前状态", inputSchema: { type: "object", properties: {} } }, handler: async () => godot.send("get_editor_state") },
    { definition: { name: "take_screenshot", description: "截取编辑器视口截图", inputSchema: { type: "object", properties: { viewport: { type: "string", description: "2d | 3d | full" } } } }, handler: async (args) => godot.send("take_screenshot", args) },
    { definition: { name: "get_output_log", description: "获取编辑器输出日志", inputSchema: { type: "object", properties: { lines: { type: "number", description: "返回行数" } } } }, handler: async (args) => godot.send("get_output_log", args) },
    { definition: { name: "get_debugger_output", description: "获取调试器输出", inputSchema: { type: "object", properties: {} } }, handler: async () => godot.send("get_debugger_output") },
    { definition: { name: "clear_output", description: "清空输出面板", inputSchema: { type: "object", properties: {} } }, handler: async () => godot.send("clear_output") },
    { definition: { name: "select_node", description: "在编辑器中选中节点", inputSchema: { type: "object", properties: { node_path: { type: "string" } }, required: ["node_path"] } }, handler: async (args) => godot.send("select_node", args) },
    { definition: { name: "get_selected_nodes", description: "获取当前选中的节点", inputSchema: { type: "object", properties: {} } }, handler: async () => godot.send("get_selected_nodes") },
    { definition: { name: "editor_undo", description: "编辑器撤销操作", inputSchema: { type: "object", properties: {} } }, handler: async () => godot.send("editor_undo") },
  ];
}
