import { describe, it, expect, vi } from "vitest";
import { registerAllTools } from "../../packages/mcp-server/src/tools/index.js";

// Mock GodotConnection
const mockGodot = {
  send: vi.fn().mockResolvedValue({ success: true }),
  isConnected: true,
  connect: vi.fn(),
  disconnect: vi.fn(),
} as any;

describe("MCP Tools Registration", () => {
  const tools = registerAllTools(mockGodot);

  it("should register 140+ tools", () => {
    expect(tools.length).toBeGreaterThanOrEqual(140);
  });

  it("should have unique tool names", () => {
    const names = tools.map((t) => t.definition.name);
    const uniqueNames = new Set(names);
    expect(uniqueNames.size).toBe(names.length);
  });

  it("should have valid definitions for all tools", () => {
    for (const tool of tools) {
      expect(tool.definition.name).toBeTruthy();
      expect(tool.definition.description).toBeTruthy();
      expect(tool.definition.inputSchema).toBeDefined();
      expect(typeof tool.handler).toBe("function");
    }
  });

  it("should include core project tools", () => {
    const names = tools.map((t) => t.definition.name);
    expect(names).toContain("get_project_info");
    expect(names).toContain("get_scene_tree");
    expect(names).toContain("create_scene");
    expect(names).toContain("add_node");
    expect(names).toContain("create_script");
    expect(names).toContain("run_project");
  });

  it("should include all tool categories", () => {
    const names = tools.map((t) => t.definition.name);
    // Physics
    expect(names).toContain("set_collision_layer");
    // Animation
    expect(names).toContain("create_animation_player");
    // Audio
    expect(names).toContain("add_audio_player");
    // UI
    expect(names).toContain("create_ui_element");
    // Rendering
    expect(names).toContain("set_environment");
    // Input
    expect(names).toContain("add_input_action");
    // Navigation
    expect(names).toContain("create_navigation_region");
    // Networking
    expect(names).toContain("create_multiplayer_spawner");
  });

  it("should call godot.send when handler is invoked", async () => {
    const projectInfoTool = tools.find(
      (t) => t.definition.name === "get_project_info"
    )!;
    await projectInfoTool.handler({});
    expect(mockGodot.send).toHaveBeenCalledWith("get_project_info");
  });
});
