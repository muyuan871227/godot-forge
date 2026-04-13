# MCP Server Architecture Specification

## Overview

The MCP Server is the backbone of GodotForge. It implements the [Model Context Protocol](https://modelcontextprotocol.io/) and acts as the bridge between AI models (Claude, GPT, local LLMs) and the Godot 4.x engine. Every AI-driven operation -- scene manipulation, script generation, asset import, game debugging -- flows through this server.

**Package:** `packages/mcp-server`
**Language:** TypeScript
**Runtime:** Node.js 20+
**Protocol version:** MCP 2024-11-05

---

## Architecture Diagram

```
 AI Client (Claude / GPT / CLI)
           |
     stdio / SSE
           |
   +-------v--------+
   |   MCP Server    |
   |  (TypeScript)   |
   +---+----+----+---+
       |    |    |
       v    v    v
    Tools  Resources  Prompts
       |    |    |
       v    v    v
   +---+----+----+---+
   |  Transport Layer |
   +---+--------+----+
       |        |
       v        v
   WebSocket   TCP
   (Editor)   (Runtime)
       |        |
       v        v
   Godot      Godot
   Editor    Headless
```

---

## Module Breakdown

### `src/index.ts` -- Entry Point

Initialises the MCP server with stdio transport. Registers all tool categories and starts listening for JSON-RPC messages.

```typescript
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { registerAllTools } from "./tools/index.js";

const server = new McpServer({
  name: "godotforge",
  version: "0.1.0",
});

registerAllTools(server);

const transport = new StdioServerTransport();
await server.connect(transport);
```

### `src/server.ts` -- Server Core

Manages the server lifecycle, tool registration, and connection state. Handles:

- Tool registration from all 15 category modules
- Connection lifecycle events (connect, disconnect, error)
- Request routing and response marshalling
- Concurrent request handling with a request queue

### `src/tools/` -- Tool Registration

Each file exports a `register(server)` function that registers related tools using the MCP SDK's `server.tool()` API. Tools follow a consistent pattern:

```typescript
// Example: tools/project.ts
import { z } from "zod";

export function register(server: McpServer) {
  server.tool(
    "project_create",
    "Create a new Godot 4.x project",
    {
      name: z.string().describe("Project name"),
      path: z.string().describe("Directory path"),
      template: z.string().optional().describe("Template name"),
      godot_version: z.string().default("4.4"),
    },
    async (args) => {
      // Implementation calls into godot/headless.ts
      const result = await createProject(args);
      return { content: [{ type: "text", text: JSON.stringify(result) }] };
    }
  );
}
```

### `src/tools/index.ts` -- Registration Hub

Imports and invokes all tool registration functions:

```typescript
import * as project from "./project.js";
import * as scene from "./scene.js";
import * as node from "./node.js";
// ... all 15 categories

export function registerAllTools(server: McpServer) {
  project.register(server);
  scene.register(server);
  node.register(server);
  // ...
}
```

### `src/transport/websocket.ts` -- Editor Connection

Manages a WebSocket connection to the Godot editor plugin. The editor plugin runs a WebSocket server; this module connects as a client and proxies tool calls into editor RPC commands.

**Protocol:** JSON messages over WebSocket on port 6505.

```typescript
interface EditorMessage {
  id: string;
  method: string;
  params: Record<string, unknown>;
}

interface EditorResponse {
  id: string;
  result?: unknown;
  error?: { code: number; message: string };
}
```

### `src/transport/tcp.ts` -- Runtime Connection

Connects to a running Godot game instance for debugging, input simulation, and live inspection. Uses a TCP socket on a configurable port (default 6506).

### `src/godot/headless.ts` -- Headless Operations

Runs Godot in headless mode (`--headless`) for operations that do not require the editor UI:

- Scene file parsing and manipulation (`.tscn` text format)
- Script validation (compile check)
- Resource import
- Export builds
- Screenshot capture via off-screen rendering

### `src/godot/process.ts` -- Process Manager

Manages Godot child processes:

- Spawning and terminating the editor or headless instance
- Health-check heartbeat
- stdout/stderr capture for log tools
- Graceful shutdown with timeout

### `src/godot/screenshot.ts` -- Screenshot Capture

Captures screenshots from the running game viewport. Supports:

- Full viewport capture
- Region capture
- Automatic format conversion (PNG, JPEG)
- Returns base64-encoded image data for MCP image content blocks

### `src/utils/uid.ts` -- UID Manager

Godot 4.x uses integer UIDs for resources. This module generates and tracks UIDs to prevent collisions when creating new resources.

### `src/utils/path.ts` -- Path Utilities

Handles `res://` path resolution, platform-specific path normalization, and safe path joining.

### `src/utils/logger.ts` -- Logging

Structured JSON logging with configurable levels (debug, info, warn, error). Logs go to stderr so they do not interfere with MCP stdio transport.

---

## GDScript Support Scripts

### `scripts/godot_operations.gd`

Runs inside the headless Godot instance. Receives commands via `--script` argument and performs engine-level operations:

- Creating and modifying scene trees
- Running the GDScript compiler for validation
- Baking navigation meshes
- Exporting projects

### `scripts/mcp_interaction.gd`

Runs inside the game at runtime. Listens on a TCP port for commands from the MCP server:

- Input simulation (key press, mouse click)
- Variable inspection
- Scene tree queries
- Screenshot capture

---

## Configuration

Environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `GODOT_MCP_PORT` | `6505` | WebSocket server port |
| `GODOT_MCP_TCP_PORT` | `6506` | TCP runtime port |
| `GODOT_MCP_LOG_LEVEL` | `info` | Log level |
| `GODOT_PATH` | `godot` | Path to the Godot binary |
| `GODOT_MCP_HEADLESS` | `true` | Run in headless mode by default |

---

## Build and Test

```bash
cd packages/mcp-server
npm install
npm run build        # TypeScript -> JavaScript
npm run test         # Vitest test suite
npm run dev          # Watch mode with ts-node
```

---

## Deployment

The MCP server is distributed as an npm package (`@godotforge/mcp-server`) and a Docker image (`godotforge/mcp-server`). In production, it runs alongside the AI services and connects to Godot headless instances.
