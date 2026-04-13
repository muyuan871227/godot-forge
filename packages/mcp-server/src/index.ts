#!/usr/bin/env node
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { CallToolRequestSchema, ListToolsRequestSchema } from "@modelcontextprotocol/sdk/types.js";
import { GodotConnection } from "./transport/websocket.js";
import { registerAllTools } from "./tools/index.js";

const SERVER_NAME = "godot-forge-mcp";
const SERVER_VERSION = "0.1.0";

async function main() {
  const server = new Server(
    { name: SERVER_NAME, version: SERVER_VERSION },
    { capabilities: { tools: {} } }
  );

  // Godot WebSocket 连接
  const godot = new GodotConnection({
    port: parseInt(process.env.GODOT_MCP_PORT || "6505"),
    reconnect: true,
  });

  // 注册所有工具
  const tools = registerAllTools(godot);

  server.setRequestHandler(ListToolsRequestSchema, async () => ({
    tools: tools.map(t => t.definition),
  }));

  server.setRequestHandler(CallToolRequestSchema, async (request) => {
    const tool = tools.find(t => t.definition.name === request.params.name);
    if (!tool) {
      return { content: [{ type: "text", text: `Unknown tool: ${request.params.name}` }], isError: true };
    }
    try {
      const result = await tool.handler(request.params.arguments ?? {});
      return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
    } catch (error: any) {
      return { content: [{ type: "text", text: `Error: ${error.message}` }], isError: true };
    }
  });

  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error(`${SERVER_NAME} v${SERVER_VERSION} running on stdio`);
}

main().catch(console.error);
