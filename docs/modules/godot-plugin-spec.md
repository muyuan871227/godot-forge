# Godot Plugin Architecture Specification

## Overview

The GodotForge editor plugin integrates AI capabilities directly into the Godot 4.x editor. It provides an AI chat panel, asset browser, generation preview, and a WebSocket-based MCP client that connects to the MCP server.

**Package:** `packages/godot-plugin`
**Language:** GDScript
**Engine:** Godot 4.4+
**Plugin path:** `addons/godot_forge/`

---

## Architecture Diagram

```
+--------------------------------------------------+
|                  Godot Editor                     |
|  +----------------------------------------------+|
|  |         EditorPlugin (plugin.gd)             ||
|  +---+----------+----------+----------+---------+|
|      |          |          |          |          |
|      v          v          v          v          |
|  AI Panel   Asset     Generation   Settings     |
|  (chat)    Browser    Preview     Dialog        |
|      |          |          |                     |
|      +----------+----------+                     |
|                 |                                 |
|      +----------v----------+                     |
|      |    MCP Client       |                     |
|      |  (WebSocket)        |                     |
|      +----------+----------+                     |
|                 |                                 |
+--------------------------------------------------+
                  |
            WebSocket :6505
                  |
         +--------v--------+
         |   MCP Server    |
         +-----------------+
```

---

## Module Breakdown

### `plugin.gd` -- EditorPlugin Main Entry

The `@tool` script that extends `EditorPlugin`. Handles:

- Plugin activation and deactivation
- Adding custom editor panels (bottom panel, dock)
- Registering the MCP client connection
- Menu items and keyboard shortcuts

```gdscript
@tool
extends EditorPlugin

var ai_panel: Control
var asset_browser: Control
var mcp_client: MCPClient

func _enter_tree() -> void:
    ai_panel = preload("res://addons/godot_forge/ui/ai_panel.tscn").instantiate()
    add_control_to_bottom_panel(ai_panel, "AI Assistant")
    
    mcp_client = MCPClient.new()
    mcp_client.connect_to_server("ws://localhost:6505")
    add_child(mcp_client)

func _exit_tree() -> void:
    remove_control_from_bottom_panel(ai_panel)
    mcp_client.disconnect_from_server()
```

### `plugin.cfg`

Standard Godot plugin configuration:

```ini
[plugin]
name="GodotForge"
description="AI-powered game development assistant"
author="GodotForge"
version="0.1.0"
script="plugin.gd"
```

---

## UI Components

### `ui/ai_panel.gd` + `ai_panel.tscn`

The main AI conversation interface, displayed as a bottom panel in the editor.

**Features:**

- Chat-style message display with markdown rendering
- Context-aware prompting (automatically includes current scene tree and selected node)
- Code block rendering with syntax highlighting and "Apply" buttons
- Message history with session management
- Loading indicators for async operations

**Key signals:**

- `message_sent(text: String)` -- User submitted a message
- `code_applied(script_path: String)` -- User applied generated code
- `asset_accepted(resource_path: String)` -- User accepted a generated asset

### `ui/asset_browser.gd` + `asset_browser.tscn`

Dedicated panel for browsing and generating art assets.

**Features:**

- Gallery view of generated assets with thumbnails
- Generation form with prompt input and style presets
- Drag-and-drop from the browser into the scene tree or filesystem
- Asset history and favorites
- Batch generation queue

### `ui/generation_preview.gd`

A popup window that shows a real-time preview of asset generation.

**Features:**

- Progress bar for generation steps
- Side-by-side comparison (prompt vs. result)
- Regenerate, accept, and discard buttons
- Parameter adjustment sliders (style strength, detail level)

### `ui/settings_dialog.gd`

Configuration dialog accessible from the editor menu.

**Settings:**

- MCP server connection URL
- AI services API endpoint
- Default LLM provider and model
- Image generation provider and presets
- Keyboard shortcut customisation
- Auto-context options (include scene tree, include scripts)

---

## MCP Client

### `mcp/mcp_client.gd`

WebSocket client that communicates with the MCP server using JSON-RPC 2.0.

```gdscript
class_name MCPClient
extends Node

signal connected
signal disconnected
signal tool_result(request_id: String, result: Dictionary)
signal error(message: String)

var _ws: WebSocketPeer
var _pending_requests: Dictionary  # id -> callback

func connect_to_server(url: String) -> void:
    _ws = WebSocketPeer.new()
    _ws.connect_to_url(url)

func call_tool(tool_name: String, arguments: Dictionary) -> String:
    var request_id = _generate_id()
    var message = {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments
        }
    }
    _ws.send_text(JSON.stringify(message))
    return request_id
```

### `mcp/tool_handler.gd`

Processes tool call results and translates them into editor actions:

- Applies scene modifications to the open scene
- Creates or updates script files
- Imports generated resources
- Updates the editor UI to reflect changes

### `mcp/message_protocol.gd`

Handles MCP message serialisation, request ID tracking, and timeout management. Implements the JSON-RPC 2.0 specification with MCP extensions.

---

## AI Modules

### `ai/code_assistant.gd`

Provides context-aware code assistance:

- Gathers the current script, scene tree, and project structure
- Formats prompts with relevant context
- Applies generated code to the correct script file
- Handles inline code suggestions and auto-completion

### `ai/scene_generator.gd`

Converts AI-generated scene descriptions into Godot scene trees:

- Parses structured scene definitions from LLM output
- Creates nodes with correct types and properties
- Handles resource dependencies (scripts, textures, materials)
- Validates the generated scene before applying

### `ai/asset_generator.gd`

Manages the asset generation workflow:

- Sends generation requests to the AI services REST API
- Downloads generated assets
- Imports them into the Godot project with proper settings
- Notifies the asset browser of new items

---

## Utility Modules

### `utils/http_client.gd`

Wrapper around `HTTPRequest` for REST API calls:

- JSON request/response helpers
- Authentication header injection
- Retry logic with exponential backoff
- Download progress tracking

### `utils/config_manager.gd`

Manages plugin configuration persistence:

- Reads/writes settings to `user://godot_forge_config.json`
- Provides default values for all settings
- Emits signals on configuration changes

---

## Installation

1. Copy the `addons/godot_forge/` directory into the project's `addons/` folder.
2. Enable the plugin in `Project > Project Settings > Plugins`.
3. Configure the MCP server URL in `Editor > GodotForge Settings`.

Alternatively, install via the Godot Asset Library (planned).

---

## Development

The plugin is developed as a standard Godot project located at `packages/godot-plugin/`. Open it in Godot 4.4+ to edit and test the plugin UI. The `project.godot` file in this directory is a test project for development purposes.

```bash
cd packages/godot-plugin
godot --editor .
```
