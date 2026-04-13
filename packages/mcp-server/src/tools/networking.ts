import { GodotConnection } from "../transport/websocket.js";
import { RegisteredTool } from "./index.js";

export function registerNetworkingTools(godot: GodotConnection): RegisteredTool[] {
  return [
    { definition: { name: "create_multiplayer_spawner", description: "创建多人游戏生成器", inputSchema: { type: "object", properties: { parent_path: { type: "string" }, node_name: { type: "string" }, spawn_path: { type: "string" }, auto_spawn_scenes: { type: "array", items: { type: "string" } } }, required: ["parent_path"] } }, handler: async (args) => godot.send("create_multiplayer_spawner", args) },
    { definition: { name: "create_multiplayer_synchronizer", description: "创建多人同步器", inputSchema: { type: "object", properties: { parent_path: { type: "string" }, node_name: { type: "string" }, sync_properties: { type: "array", items: { type: "string" } } }, required: ["parent_path"] } }, handler: async (args) => godot.send("create_multiplayer_synchronizer", args) },
    { definition: { name: "set_multiplayer_authority", description: "设置多人游戏权限", inputSchema: { type: "object", properties: { node_path: { type: "string" }, authority_id: { type: "number" } }, required: ["node_path", "authority_id"] } }, handler: async (args) => godot.send("set_multiplayer_authority", args) },
    { definition: { name: "configure_enet", description: "配置 ENet 多人连接", inputSchema: { type: "object", properties: { mode: { type: "string", description: "server | client" }, port: { type: "number" }, address: { type: "string" }, max_clients: { type: "number" } }, required: ["mode"] } }, handler: async (args) => godot.send("configure_enet", args) },
    { definition: { name: "create_rpc_function", description: "为脚本添加 RPC 函数", inputSchema: { type: "object", properties: { script_path: { type: "string" }, function_name: { type: "string" }, rpc_mode: { type: "string", description: "any_peer | authority" }, transfer_mode: { type: "string", description: "reliable | unreliable | ordered" } }, required: ["script_path", "function_name"] } }, handler: async (args) => godot.send("create_rpc_function", args) },
    { definition: { name: "set_network_mode", description: "设置场景的网络模式", inputSchema: { type: "object", properties: { scene_path: { type: "string" }, mode: { type: "string", description: "offline | lan | online" } }, required: ["scene_path", "mode"] } }, handler: async (args) => godot.send("set_network_mode", args) },
  ];
}
