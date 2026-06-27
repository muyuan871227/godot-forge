import { GodotConnection } from "../transport/websocket.js";
import { RegisteredTool } from "./index.js";

export function registerAudioTools(godot: GodotConnection): RegisteredTool[] {
  return [
    { definition: { name: "add_audio_player", description: "添加音频播放器节点", inputSchema: { type: "object", properties: { parent_path: { type: "string" }, node_name: { type: "string" }, type: { type: "string", description: "2d | 3d | stream" } }, required: ["parent_path"] } }, handler: async (args) => godot.send("add_audio_player", args) },
    { definition: { name: "set_audio_stream", description: "设置音频播放器的音频流", inputSchema: { type: "object", properties: { player_path: { type: "string" }, audio_path: { type: "string" } }, required: ["player_path", "audio_path"] } }, handler: async (args) => godot.send("set_audio_stream", args) },
    { definition: { name: "add_audio_bus", description: "添加音频总线", inputSchema: { type: "object", properties: { bus_name: { type: "string" }, send_to: { type: "string" } }, required: ["bus_name"] } }, handler: async (args) => godot.send("add_audio_bus", args) },
    { definition: { name: "configure_audio_effect", description: "配置音频总线效果", inputSchema: { type: "object", properties: { bus_name: { type: "string" }, effect_type: { type: "string", description: "reverb | delay | chorus | distortion | eq | compressor" }, properties: { type: "object" } }, required: ["bus_name", "effect_type"] } }, handler: async (args) => godot.send("configure_audio_effect", args) },
    { definition: { name: "play_audio", description: "播放音频", inputSchema: { type: "object", properties: { player_path: { type: "string" } }, required: ["player_path"] } }, handler: async (args) => godot.send("play_audio", args) },
    { definition: { name: "stop_audio", description: "停止音频播放", inputSchema: { type: "object", properties: { player_path: { type: "string" } }, required: ["player_path"] } }, handler: async (args) => godot.send("stop_audio", args) },
  ];
}
