import { GodotConnection } from "../transport/websocket.js";
import { registerProjectTools } from "./project.js";
import { registerSceneTools } from "./scene.js";
import { registerNodeTools } from "./node.js";
import { registerScriptTools } from "./script.js";
import { registerResourceTools } from "./resource.js";
import { registerEditorTools } from "./editor.js";
import { registerDebugTools } from "./debug.js";
import { registerPhysicsTools } from "./physics.js";
import { registerAnimationTools } from "./animation.js";
import { registerAudioTools } from "./audio.js";
import { registerUITools } from "./ui.js";
import { registerRenderingTools } from "./rendering.js";
import { registerInputTools } from "./input.js";
import { registerNavigationTools } from "./navigation.js";
import { registerNetworkingTools } from "./networking.js";

export interface ToolDefinition {
  name: string;
  description: string;
  inputSchema: Record<string, any>;
}

export interface RegisteredTool {
  definition: ToolDefinition;
  handler: (args: Record<string, any>) => Promise<any>;
}

export function registerAllTools(godot: GodotConnection): RegisteredTool[] {
  return [
    ...registerProjectTools(godot),
    ...registerSceneTools(godot),
    ...registerNodeTools(godot),
    ...registerScriptTools(godot),
    ...registerResourceTools(godot),
    ...registerEditorTools(godot),
    ...registerDebugTools(godot),
    ...registerPhysicsTools(godot),
    ...registerAnimationTools(godot),
    ...registerAudioTools(godot),
    ...registerUITools(godot),
    ...registerRenderingTools(godot),
    ...registerInputTools(godot),
    ...registerNavigationTools(godot),
    ...registerNetworkingTools(godot),
  ];
}
