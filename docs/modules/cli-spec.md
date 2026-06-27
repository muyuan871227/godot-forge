# CLI Architecture Specification

## Overview

The GodotForge CLI (`godotforge`) is a command-line tool for creating, developing, and managing Godot projects with AI assistance. It is the fastest way to scaffold a project, generate assets, run builds, and interact with the AI services without a browser or editor.

**Package:** `packages/cli`
**Language:** TypeScript
**Runtime:** Node.js 20+
**Binary name:** `godotforge`

---

## Installation

```bash
# Global install
npm install -g @godotforge/cli

# Or run directly with npx
npx @godotforge/cli init MyGame
```

---

## Command Reference

### `godotforge init`

Create a new Godot project from a template.

```bash
godotforge init <name> [options]

Options:
  --template, -t   Template name (default: blank-2d)
                    Choices: blank-2d, blank-3d, 2d-platformer,
                    2d-topdown-rpg, 3d-fps, 3d-third-person,
                    visual-novel, puzzle
  --godot-version  Godot version (default: 4.4)
  --path, -p       Output directory (default: ./<name>)
  --no-git         Skip git init
```

**Example:**
```bash
godotforge init SpaceShooter -t 2d-platformer
```

**Implementation (`commands/init.ts`):**

1. Validate the project name and output path.
2. Copy the selected template from the `templates/` directory.
3. Generate a `project.godot` file with the correct Godot version.
4. Initialise a git repository (unless `--no-git`).
5. Print a success message with next steps.

---

### `godotforge generate`

Generate game assets or code using AI.

```bash
godotforge generate <type> [options]

Types:
  script     Generate GDScript code
  sprite     Generate a sprite or sprite sheet
  tileset    Generate a tileset
  model      Generate a 3D model
  sfx        Generate a sound effect
  bgm        Generate background music
  scene      Generate a complete scene

Options:
  --prompt, -p     Description of what to generate (required)
  --output, -o     Output file path
  --style          Art style preset (pixel, hand-drawn, realistic, low-poly)
  --format         Output format (varies by type)
  --project        Path to Godot project (default: current directory)
```

**Examples:**
```bash
# Generate a player movement script
godotforge generate script -p "CharacterBody2D with 8-direction movement, 300px/s"

# Generate a sprite sheet
godotforge generate sprite -p "Pixel art warrior, 32x32, walk cycle" -o res://sprites/warrior.png

# Generate background music
godotforge generate bgm -p "Upbeat chiptune adventure theme, 120 BPM" -o res://audio/bgm.ogg
```

**Implementation (`commands/generate.ts`):**

1. Detect the current Godot project (or use `--project`).
2. Send a POST request to the appropriate AI services endpoint.
3. Display a progress spinner while waiting.
4. Save the generated asset to the output path.
5. If inside a Godot project, create the `.import` metadata file.

---

### `godotforge build`

Export the Godot project for a target platform.

```bash
godotforge build [options]

Options:
  --platform       Target platform (default: html5)
                   Choices: html5, windows, macos, linux, android, ios
  --preset         Export preset name from export_presets.cfg
  --output, -o     Output directory (default: ./build/)
  --godot-path     Path to Godot binary
  --release        Use release export (strips debug symbols)
```

**Example:**
```bash
godotforge build --platform html5 -o ./dist/
```

**Implementation (`commands/build.ts`):**

1. Locate the Godot project and validate `export_presets.cfg`.
2. Resolve the Godot binary path (env, config, or system PATH).
3. Run the Godot headless export command.
4. Monitor stdout/stderr for progress and errors.
5. Report the output path and file size on success.

---

### `godotforge serve`

Start the GodotForge development services (MCP server + AI services).

```bash
godotforge serve [options]

Options:
  --mcp-port       MCP server port (default: 6505)
  --ai-port        AI services port (default: 8100)
  --docker         Use Docker Compose instead of local processes
  --enterprise     Use the enterprise Docker Compose stack
  --detach, -d     Run in background
```

**Example:**
```bash
# Start local services
godotforge serve

# Start enterprise stack in background
godotforge serve --enterprise -d
```

**Implementation (`commands/serve.ts`):**

1. Check for required dependencies (Node.js, Python, or Docker).
2. Start the MCP server process.
3. Start the AI services process.
4. Monitor both processes and multiplex their output.
5. Handle graceful shutdown on SIGINT/SIGTERM.

---

### `godotforge asset`

Manage project assets.

```bash
godotforge asset <subcommand> [options]

Subcommands:
  list       List all assets in the project
  import     Import an external file into the project
  generate   Alias for 'godotforge generate'
  info       Show metadata about an asset
  delete     Remove an asset and clean up references
  optimize   Optimize assets (compress images, reduce poly count)

Options:
  --type, -t       Filter by asset type (texture, audio, model, script, scene)
  --format         Output format for list (table, json)
```

**Examples:**
```bash
# List all textures
godotforge asset list -t texture

# Import a PNG with specific settings
godotforge asset import ./character.png --filter-mode nearest --compress lossless

# Show asset info
godotforge asset info res://sprites/player.png
```

**Implementation (`commands/asset.ts`):**

1. Parse the project's resource filesystem.
2. Read `.import` files for metadata.
3. For imports, copy the file and generate appropriate import settings.
4. For deletions, scan for references before removing.

---

## Architecture

### Entry Point (`src/index.ts`)

Uses `commander` for argument parsing and command routing.

```typescript
import { Command } from "commander";
import { initCommand } from "./commands/init.js";
import { generateCommand } from "./commands/generate.js";
import { buildCommand } from "./commands/build.js";
import { serveCommand } from "./commands/serve.js";
import { assetCommand } from "./commands/asset.js";

const program = new Command()
  .name("godotforge")
  .description("AI-powered Godot game development CLI")
  .version("0.1.0");

program.addCommand(initCommand);
program.addCommand(generateCommand);
program.addCommand(buildCommand);
program.addCommand(serveCommand);
program.addCommand(assetCommand);

program.parse();
```

### Utilities (`src/utils/`)

- **config.ts** -- Reads `.godotforge.json` and environment variables for CLI configuration.
- **api.ts** -- HTTP client for communicating with the AI services REST API.
- **godot.ts** -- Helpers for locating the Godot binary and parsing `project.godot`.
- **spinner.ts** -- Terminal spinner/progress indicator.
- **logger.ts** -- Coloured console output with verbosity levels.

---

## Configuration File

The CLI reads project-level configuration from `.godotforge.json` in the project root:

```json
{
  "godot_version": "4.4",
  "godot_path": "/usr/local/bin/godot",
  "ai_services_url": "http://localhost:8100",
  "mcp_server_url": "ws://localhost:6505",
  "default_style": "pixel",
  "auth_token": ""
}
```

Global configuration is stored in `~/.godotforge/config.json`.

---

## Build and Development

```bash
cd packages/cli
npm install
npm run build        # TypeScript -> JavaScript
npm run dev          # Watch mode
npm link             # Install globally for testing
npm run test         # Vitest test suite
```

---

## Distribution

The CLI is published to npm as `@godotforge/cli`. Users can install it globally or use `npx` for one-off commands.

```bash
npm publish --access public
```
