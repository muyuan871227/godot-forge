import { GodotConnection } from "../transport/websocket.js";
import { RegisteredTool } from "./index.js";

export function registerResourceTools(godot: GodotConnection): RegisteredTool[] {
  return [
    { definition: { name: "load_resource", description: "加载资源并返回其信息", inputSchema: { type: "object", properties: { path: { type: "string" } }, required: ["path"] } }, handler: async (args) => godot.send("load_resource", args) },
    { definition: { name: "save_resource", description: "保存资源到指定路径", inputSchema: { type: "object", properties: { path: { type: "string" }, resource_type: { type: "string" } }, required: ["path"] } }, handler: async (args) => godot.send("save_resource", args) },
    { definition: { name: "import_asset", description: "导入外部资源文件", inputSchema: { type: "object", properties: { source_path: { type: "string" }, target_path: { type: "string" } }, required: ["source_path", "target_path"] } }, handler: async (args) => godot.send("import_asset", args) },
    { definition: { name: "get_import_settings", description: "获取资源的导入设置", inputSchema: { type: "object", properties: { path: { type: "string" } }, required: ["path"] } }, handler: async (args) => godot.send("get_import_settings", args) },
    { definition: { name: "set_import_settings", description: "修改资源的导入设置", inputSchema: { type: "object", properties: { path: { type: "string" }, settings: { type: "object" } }, required: ["path", "settings"] } }, handler: async (args) => godot.send("set_import_settings", args) },
    { definition: { name: "create_resource", description: "创建新资源", inputSchema: { type: "object", properties: { type: { type: "string" }, path: { type: "string" }, properties: { type: "object" } }, required: ["type", "path"] } }, handler: async (args) => godot.send("create_resource", args) },
    { definition: { name: "duplicate_resource", description: "复制资源", inputSchema: { type: "object", properties: { source_path: { type: "string" }, target_path: { type: "string" } }, required: ["source_path", "target_path"] } }, handler: async (args) => godot.send("duplicate_resource", args) },
    { definition: { name: "get_resource_dependencies", description: "获取资源的依赖关系", inputSchema: { type: "object", properties: { path: { type: "string" } }, required: ["path"] } }, handler: async (args) => godot.send("get_resource_dependencies", args) },
    { definition: { name: "find_unused_resources", description: "查找项目中未使用的资源", inputSchema: { type: "object", properties: { directory: { type: "string" } } } }, handler: async (args) => godot.send("find_unused_resources", args) },
    { definition: { name: "list_all_resources", description: "列出指定目录下的所有资源", inputSchema: { type: "object", properties: { directory: { type: "string" }, type_filter: { type: "string" } } } }, handler: async (args) => godot.send("list_all_resources", args) },
  ];
}
