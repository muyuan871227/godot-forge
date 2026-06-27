import { GodotConnection } from "../transport/websocket.js";
import { RegisteredTool } from "./index.js";

export function registerPhysicsTools(godot: GodotConnection): RegisteredTool[] {
  return [
    { definition: { name: "set_collision_layer", description: "设置节点的碰撞层", inputSchema: { type: "object", properties: { node_path: { type: "string" }, layer: { type: "number" } }, required: ["node_path", "layer"] } }, handler: async (args) => godot.send("set_collision_layer", args) },
    { definition: { name: "set_collision_mask", description: "设置节点的碰撞掩码", inputSchema: { type: "object", properties: { node_path: { type: "string" }, mask: { type: "number" } }, required: ["node_path", "mask"] } }, handler: async (args) => godot.send("set_collision_mask", args) },
    { definition: { name: "add_collision_shape", description: "为物理体添加碰撞形状", inputSchema: { type: "object", properties: { node_path: { type: "string" }, shape_type: { type: "string", description: "rectangle | circle | capsule | polygon" }, size: { type: "object" } }, required: ["node_path", "shape_type"] } }, handler: async (args) => godot.send("add_collision_shape", args) },
    { definition: { name: "create_physics_body", description: "创建物理体节点", inputSchema: { type: "object", properties: { parent_path: { type: "string" }, body_type: { type: "string", description: "static | rigid | character | area" }, node_name: { type: "string" } }, required: ["parent_path", "body_type", "node_name"] } }, handler: async (args) => godot.send("create_physics_body", args) },
    { definition: { name: "set_gravity", description: "设置项目重力", inputSchema: { type: "object", properties: { gravity: { type: "number" }, direction: { type: "object" } }, required: ["gravity"] } }, handler: async (args) => godot.send("set_gravity", args) },
    { definition: { name: "get_physics_settings", description: "获取物理引擎设置", inputSchema: { type: "object", properties: {} } }, handler: async () => godot.send("get_physics_settings") },
    { definition: { name: "add_raycast", description: "添加射线检测节点", inputSchema: { type: "object", properties: { parent_path: { type: "string" }, target_position: { type: "object" }, node_name: { type: "string" } }, required: ["parent_path"] } }, handler: async (args) => godot.send("add_raycast", args) },
    { definition: { name: "configure_area", description: "配置 Area 节点属性", inputSchema: { type: "object", properties: { node_path: { type: "string" }, monitoring: { type: "boolean" }, monitorable: { type: "boolean" }, gravity_override: { type: "number" } }, required: ["node_path"] } }, handler: async (args) => godot.send("configure_area", args) },
  ];
}
