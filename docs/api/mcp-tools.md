# MCP Tools Reference

GodotForge exposes **142 tools** across 15 categories via the [Model Context Protocol](https://modelcontextprotocol.io/) (MCP). These tools enable AI models to create, inspect, and manipulate every aspect of a Godot 4.x project.

## Connection

The MCP server communicates over **stdio** (default) or **WebSocket** (`ws://localhost:6505`).

```jsonc
// Claude Desktop configuration
{
  "mcpServers": {
    "godotforge": {
      "command": "npx",
      "args": ["-y", "@godotforge/mcp-server"]
    }
  }
}
```

---

## 1. Project Management (`project.ts`) -- 8 tools

| Tool | Description |
|------|-------------|
| `project_create` | Create a new Godot 4.x project with `project.godot`, default environment, and folder structure. Accepts a template name to scaffold from built-in templates. |
| `project_open` | Open an existing project by path. Validates the `project.godot` file and returns the project metadata. |
| `project_list` | List all known projects in the workspace registry. |
| `project_info` | Return detailed information about the current project: Godot version, rendering backend, enabled plugins, and dependency list. |
| `project_settings_get` | Read one or more project settings from `project.godot` by section and key. |
| `project_settings_set` | Write project settings. Accepts a map of `section/key` to value. |
| `project_export` | Trigger an export preset build (HTML5, Windows, macOS, Linux, Android, iOS). Returns the output path. |
| `project_close` | Close the current project and release file locks. |

**Example -- create a project from a template:**
```json
{
  "tool": "project_create",
  "arguments": {
    "name": "SpaceShooter",
    "path": "/home/user/games/SpaceShooter",
    "template": "2d-topdown-rpg",
    "godot_version": "4.4"
  }
}
```

---

## 2. Scene Operations (`scene.ts`) -- 15 tools

| Tool | Description |
|------|-------------|
| `scene_create` | Create a new `.tscn` scene file with a specified root node type. |
| `scene_open` | Open a scene for editing. Returns the full scene tree. |
| `scene_save` | Save the current scene to disk. |
| `scene_save_as` | Save a copy of the current scene under a new path. |
| `scene_close` | Close a scene without saving. |
| `scene_list` | List all `.tscn` and `.scn` files in the project. |
| `scene_tree` | Return the full node hierarchy of a scene as a JSON tree. |
| `scene_instantiate` | Instance a packed scene as a child of a target node. |
| `scene_merge` | Merge nodes from one scene into another. |
| `scene_diff` | Compare two scene files and return structural differences. |
| `scene_set_main` | Set a scene as the project's main scene in `project.godot`. |
| `scene_get_dependencies` | List all resources (scripts, textures, etc.) referenced by a scene. |
| `scene_validate` | Validate a scene for common errors (missing resources, broken references). |
| `scene_convert` | Convert between `.tscn` (text) and `.scn` (binary) formats. |
| `scene_thumbnail` | Generate a thumbnail preview image of a scene. |

---

## 3. Node CRUD (`node.ts`) -- 20 tools

| Tool | Description |
|------|-------------|
| `node_add` | Add a new node to the scene tree. Specify type, name, and parent path. |
| `node_remove` | Remove a node and all its children from the scene tree. |
| `node_rename` | Rename a node. |
| `node_move` | Reparent a node to a different parent. |
| `node_duplicate` | Duplicate a node and its subtree. |
| `node_get` | Get all properties of a specific node. |
| `node_set_property` | Set one or more properties on a node. |
| `node_get_property` | Read a specific property value from a node. |
| `node_list_children` | List the immediate children of a node. |
| `node_find` | Find nodes matching a name pattern or type filter. |
| `node_set_transform` | Set position, rotation, and scale (2D or 3D). |
| `node_get_transform` | Get the current transform of a node. |
| `node_set_visible` | Toggle visibility of a CanvasItem or Node3D. |
| `node_set_process_mode` | Set the process mode (inherit, pausable, always, disabled). |
| `node_add_to_group` | Add a node to a named group. |
| `node_remove_from_group` | Remove a node from a group. |
| `node_get_groups` | List all groups a node belongs to. |
| `node_set_owner` | Change the owner of a node (affects scene serialisation). |
| `node_get_signals` | List all signals emitted by a node type. |
| `node_connect_signal` | Connect a signal from one node to a method on another. |

**Example -- add a CharacterBody2D:**
```json
{
  "tool": "node_add",
  "arguments": {
    "scene": "res://scenes/player.tscn",
    "parent": "/root",
    "type": "CharacterBody2D",
    "name": "Player",
    "properties": {
      "position": {"x": 100, "y": 200}
    }
  }
}
```

---

## 4. Script Operations (`script.ts`) -- 12 tools

| Tool | Description |
|------|-------------|
| `script_create` | Create a new GDScript or C# file with optional boilerplate. |
| `script_read` | Read the full contents of a script file. |
| `script_write` | Overwrite a script file with new content. |
| `script_attach` | Attach a script to a node. |
| `script_detach` | Detach the script from a node. |
| `script_list` | List all script files in the project. |
| `script_parse` | Parse a GDScript file and return its AST (classes, functions, signals, exports). |
| `script_validate` | Run the GDScript compiler on a file and return errors/warnings. |
| `script_rename` | Rename a script file and update all references. |
| `script_search` | Search for text patterns across all scripts. |
| `script_add_function` | Append a function to an existing script. |
| `script_modify_function` | Replace the body of a specific function in a script. |

---

## 5. Resource Management (`resource.ts`) -- 10 tools

| Tool | Description |
|------|-------------|
| `resource_import` | Import an external file (PNG, OGG, GLTF, etc.) into the project with proper `.import` metadata. |
| `resource_list` | List resources filtered by type (Texture2D, AudioStream, PackedScene, etc.). |
| `resource_info` | Get metadata about a resource (size, format, import settings). |
| `resource_move` | Move a resource file to a new location and update all references. |
| `resource_delete` | Delete a resource and optionally clean up dangling references. |
| `resource_create` | Create a new resource (Theme, StyleBox, Material, etc.) from parameters. |
| `resource_export` | Export a resource to an external format. |
| `resource_reimport` | Force reimport of a resource with updated import settings. |
| `resource_set_import_options` | Change import preset options for an asset (e.g., filter mode, compression). |
| `resource_find_references` | Find all scenes and scripts that reference a given resource. |

---

## 6. Editor Control (`editor.ts`) -- 8 tools

| Tool | Description |
|------|-------------|
| `editor_run_project` | Launch the game in the Godot player. |
| `editor_stop_project` | Stop the running game instance. |
| `editor_run_scene` | Run a specific scene directly. |
| `editor_screenshot` | Capture a screenshot of the running game viewport. |
| `editor_get_open_scenes` | List currently open scenes in the editor. |
| `editor_switch_scene` | Switch the active editor tab to a different scene. |
| `editor_reload_scripts` | Force reload all scripts from disk. |
| `editor_get_version` | Return the Godot editor version and platform. |

---

## 7. Debug Tools (`debug.ts`) -- 10 tools

| Tool | Description |
|------|-------------|
| `debug_set_breakpoint` | Set a breakpoint at a script line. |
| `debug_remove_breakpoint` | Remove a breakpoint. |
| `debug_list_breakpoints` | List all active breakpoints. |
| `debug_step` | Step to the next line in the debugger. |
| `debug_continue` | Continue execution from a breakpoint. |
| `debug_get_stack` | Get the current call stack. |
| `debug_inspect_variable` | Inspect a variable's value at the current breakpoint. |
| `debug_get_logs` | Read the latest log output from the running game. |
| `debug_get_errors` | Get runtime errors and warnings. |
| `debug_profile` | Start/stop the built-in profiler and return frame timings. |

---

## 8. Physics System (`physics.ts`) -- 8 tools

| Tool | Description |
|------|-------------|
| `physics_set_layer` | Configure collision layers and masks on a body. |
| `physics_get_layer` | Read collision layer/mask configuration. |
| `physics_add_shape` | Add a collision shape to a body node. |
| `physics_remove_shape` | Remove a collision shape. |
| `physics_set_body_properties` | Set mass, friction, bounce, gravity scale on RigidBody nodes. |
| `physics_raycast` | Perform a raycast query and return hit results. |
| `physics_set_2d_gravity` | Set the global 2D physics gravity vector. |
| `physics_set_3d_gravity` | Set the global 3D physics gravity vector. |

---

## 9. Animation System (`animation.ts`) -- 10 tools

| Tool | Description |
|------|-------------|
| `animation_create_player` | Add an AnimationPlayer node to a parent. |
| `animation_create` | Create a new animation on an AnimationPlayer. |
| `animation_add_track` | Add a property, method, or bezier track to an animation. |
| `animation_add_keyframe` | Insert a keyframe at a given time on a track. |
| `animation_remove_keyframe` | Remove a keyframe from a track. |
| `animation_set_length` | Set the duration of an animation. |
| `animation_set_loop` | Enable or disable looping. |
| `animation_list` | List all animations on an AnimationPlayer. |
| `animation_play` | Play a named animation. |
| `animation_create_tree` | Create an AnimationTree with a state machine or blend tree. |

---

## 10. Audio System (`audio.ts`) -- 6 tools

| Tool | Description |
|------|-------------|
| `audio_add_player` | Add an AudioStreamPlayer (2D or 3D) node. |
| `audio_set_stream` | Assign an audio resource to a player node. |
| `audio_play` | Play audio on a specific player. |
| `audio_stop` | Stop audio playback. |
| `audio_set_bus` | Configure the audio bus (volume, effects) for a player. |
| `audio_create_bus` | Create a new audio bus with optional effects (reverb, delay, etc.). |

---

## 11. UI Controls (`ui.ts`) -- 10 tools

| Tool | Description |
|------|-------------|
| `ui_add_control` | Add a Control node (Button, Label, TextureRect, etc.) to the UI tree. |
| `ui_set_anchor` | Set anchor and margin presets for responsive layout. |
| `ui_set_theme` | Apply a Theme resource to a Control subtree. |
| `ui_create_theme` | Generate a Theme resource from parameters (colors, fonts, styleboxes). |
| `ui_set_text` | Set the text property on Label, Button, or RichTextLabel. |
| `ui_set_font` | Assign a font resource to a text control. |
| `ui_add_container` | Add a layout container (HBox, VBox, Grid, Margin, etc.). |
| `ui_create_dialog` | Create a popup dialog (confirmation, file, color picker). |
| `ui_set_focus` | Set the focus neighbor chain for keyboard/gamepad navigation. |
| `ui_create_rich_text` | Create a RichTextLabel with BBCode content. |

---

## 12. Rendering (`rendering.ts`) -- 8 tools

| Tool | Description |
|------|-------------|
| `rendering_set_environment` | Configure the WorldEnvironment (sky, fog, tonemap, SSAO). |
| `rendering_add_light` | Add a light node (DirectionalLight3D, OmniLight3D, SpotLight3D). |
| `rendering_set_material` | Assign or create a material on a MeshInstance3D. |
| `rendering_set_shader` | Attach a custom shader to a material. |
| `rendering_add_camera` | Add a Camera2D or Camera3D node. |
| `rendering_set_viewport` | Configure viewport settings (MSAA, resolution, stretch mode). |
| `rendering_add_particles` | Add a GPUParticles2D/3D node with configurable emission. |
| `rendering_set_canvas_layer` | Add and configure CanvasLayer nodes for parallax or HUD. |

---

## 13. Input Simulation (`input.ts`) -- 6 tools

| Tool | Description |
|------|-------------|
| `input_action_press` | Simulate pressing an input action. |
| `input_action_release` | Simulate releasing an input action. |
| `input_mouse_move` | Move the virtual mouse to a position. |
| `input_mouse_click` | Simulate a mouse click at a position. |
| `input_key_press` | Simulate a physical key press. |
| `input_create_action` | Define a new input action mapping in project settings. |

---

## 14. Navigation System (`navigation.ts`) -- 5 tools

| Tool | Description |
|------|-------------|
| `navigation_add_region` | Add a NavigationRegion2D/3D with a navigation mesh. |
| `navigation_bake_mesh` | Bake (generate) the navigation mesh for a region. |
| `navigation_add_agent` | Add a NavigationAgent2D/3D to a character node. |
| `navigation_set_target` | Set the target position for a navigation agent. |
| `navigation_add_obstacle` | Add a NavigationObstacle for dynamic avoidance. |

---

## 15. Networking (`networking.ts`) -- 6 tools

| Tool | Description |
|------|-------------|
| `networking_setup_peer` | Configure the multiplayer peer (ENet, WebSocket, WebRTC). |
| `networking_create_spawner` | Add a MultiplayerSpawner for automatic scene replication. |
| `networking_create_synchronizer` | Add a MultiplayerSynchronizer for property replication. |
| `networking_set_authority` | Set the multiplayer authority for a node. |
| `networking_add_rpc` | Add an `@rpc` annotation to a function in a script. |
| `networking_configure_server` | Set up server connection parameters (port, max clients, etc.). |

---

## Error Handling

All tools return a standard MCP result. On failure the `isError` flag is `true` and `content` contains a human-readable message:

```json
{
  "isError": true,
  "content": [
    {
      "type": "text",
      "text": "Scene not found: res://scenes/missing.tscn"
    }
  ]
}
```

## Tool Discovery

Clients can call `tools/list` to enumerate all registered tools with their JSON schemas at runtime.
