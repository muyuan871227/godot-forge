import { GodotConnection } from "../transport/websocket.js";
import { RegisteredTool } from "./index.js";

export function registerNavigationTools(godot: GodotConnection): RegisteredTool[] {
  return [
    { definition: { name: "create_navigation_region", description: "创建导航区域", inputSchema: { type: "object", properties: { parent_path: { type: "string" }, node_name: { type: "string" }, type: { type: "string", description: "2d | 3d" } }, required: ["parent_path"] } }, handler: async (args) => godot.send("create_navigation_region", args) },
    { definition: { name: "bake_navigation", description: "烘焙导航网格", inputSchema: { type: "object", properties: { region_path: { type: "string" } }, required: ["region_path"] } }, handler: async (args) => godot.send("bake_navigation", args) },
    { definition: { name: "create_navigation_agent", description: "创建导航代理", inputSchema: { type: "object", properties: { parent_path: { type: "string" }, node_name: { type: "string" }, type: { type: "string", description: "2d | 3d" }, radius: { type: "number" }, max_speed: { type: "number" } }, required: ["parent_path"] } }, handler: async (args) => godot.send("create_navigation_agent", args) },
    { definition: { name: "set_navigation_target", description: "设置导航目标位置", inputSchema: { type: "object", properties: { agent_path: { type: "string" }, target: { type: "object", description: "目标坐标 {x, y} 或 {x, y, z}" } }, required: ["agent_path", "target"] } }, handler: async (args) => godot.send("set_navigation_target", args) },
    { definition: { name: "get_navigation_path", description: "获取导航路径", inputSchema: { type: "object", properties: { agent_path: { type: "string" }, from: { type: "object" }, to: { type: "object" } }, required: ["agent_path", "from", "to"] } }, handler: async (args) => godot.send("get_navigation_path", args) },
  ];
}
