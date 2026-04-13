import { GodotConnection } from "../transport/websocket.js";
import { RegisteredTool } from "./index.js";

export function registerInputTools(godot: GodotConnection): RegisteredTool[] {
  return [
    { definition: { name: "add_input_action", description: "添加输入动作", inputSchema: { type: "object", properties: { action_name: { type: "string" }, keys: { type: "array", items: { type: "string" }, description: "按键列表" }, deadzone: { type: "number" } }, required: ["action_name"] } }, handler: async (args) => godot.send("add_input_action", args) },
    { definition: { name: "remove_input_action", description: "移除输入动作", inputSchema: { type: "object", properties: { action_name: { type: "string" } }, required: ["action_name"] } }, handler: async (args) => godot.send("remove_input_action", args) },
    { definition: { name: "get_input_map", description: "获取完整输入映射", inputSchema: { type: "object", properties: {} } }, handler: async () => godot.send("get_input_map") },
    { definition: { name: "set_input_map", description: "批量设置输入映射", inputSchema: { type: "object", properties: { actions: { type: "object", description: "动作名到按键数组的映射" } }, required: ["actions"] } }, handler: async (args) => godot.send("set_input_map", args) },
    { definition: { name: "simulate_input", description: "模拟输入事件 (运行时)", inputSchema: { type: "object", properties: { action: { type: "string" }, pressed: { type: "boolean" }, strength: { type: "number" } }, required: ["action", "pressed"] } }, handler: async (args) => godot.send("simulate_input", args) },
    { definition: { name: "simulate_key_press", description: "模拟按键 (运行时)", inputSchema: { type: "object", properties: { keycode: { type: "string" }, pressed: { type: "boolean" }, shift: { type: "boolean" }, ctrl: { type: "boolean" }, alt: { type: "boolean" } }, required: ["keycode", "pressed"] } }, handler: async (args) => godot.send("simulate_key_press", args) },
  ];
}
