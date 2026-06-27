import { GodotConnection } from "../transport/websocket.js";
import { RegisteredTool } from "./index.js";

export function registerDebugTools(godot: GodotConnection): RegisteredTool[] {
  return [
    { definition: { name: "run_project", description: "运行当前项目", inputSchema: { type: "object", properties: { scene: { type: "string", description: "指定运行的场景路径 (可选)" } } } }, handler: async (args) => godot.send("run_project", args) },
    { definition: { name: "stop_project", description: "停止正在运行的项目", inputSchema: { type: "object", properties: {} } }, handler: async () => godot.send("stop_project") },
    { definition: { name: "run_scene", description: "运行指定场景", inputSchema: { type: "object", properties: { scene_path: { type: "string" } }, required: ["scene_path"] } }, handler: async (args) => godot.send("run_scene", args) },
    { definition: { name: "get_debug_output", description: "获取运行时调试输出", inputSchema: { type: "object", properties: { lines: { type: "number" } } } }, handler: async (args) => godot.send("get_debug_output", args) },
    { definition: { name: "get_errors", description: "获取运行时错误列表", inputSchema: { type: "object", properties: {} } }, handler: async () => godot.send("get_errors") },
    { definition: { name: "clear_errors", description: "清除错误列表", inputSchema: { type: "object", properties: {} } }, handler: async () => godot.send("clear_errors") },
    { definition: { name: "set_breakpoint", description: "设置断点", inputSchema: { type: "object", properties: { script_path: { type: "string" }, line: { type: "number" } }, required: ["script_path", "line"] } }, handler: async (args) => godot.send("set_breakpoint", args) },
    { definition: { name: "remove_breakpoint", description: "移除断点", inputSchema: { type: "object", properties: { script_path: { type: "string" }, line: { type: "number" } }, required: ["script_path", "line"] } }, handler: async (args) => godot.send("remove_breakpoint", args) },
    { definition: { name: "game_eval", description: "在运行时执行 GDScript 表达式", inputSchema: { type: "object", properties: { expression: { type: "string" } }, required: ["expression"] } }, handler: async (args) => godot.send("game_eval", args) },
    { definition: { name: "get_runtime_node_tree", description: "获取运行时的节点树", inputSchema: { type: "object", properties: {} } }, handler: async () => godot.send("get_runtime_node_tree") },
  ];
}
