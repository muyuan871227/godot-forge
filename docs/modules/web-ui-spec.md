# Web UI Architecture Specification

## Overview

The Web UI provides a browser-based management interface for GodotForge. It enables project management, AI-assisted game development conversations, asset management, and build/export workflows without requiring the Godot editor to be installed locally.

**Package:** `packages/web-ui`
**Language:** TypeScript
**Framework:** React 18 + Next.js 14 (App Router)
**Default port:** 3000

---

## Architecture Diagram

```
+----------------------------------------------------+
|                   Browser                          |
|  +------------------------------------------------+|
|  |             Next.js App Router                 ||
|  +---+----------+----------+----------+-----------+|
|      |          |          |          |            |
|      v          v          v          v            |
|   Home/      Project     Templates   Settings     |
|  Projects   Workspace    Market      Page         |
|              |   |   |                             |
|              v   v   v                             |
|           Chat Assets Build                        |
|              |                                     |
|  +-----------v-----------+                         |
|  |    State Management   |                         |
|  |    (Zustand stores)   |                         |
|  +-----------+-----------+                         |
|              |                                     |
|  +-----------v-----------+                         |
|  |   API Client (REST)   |  WebSocket (MCP)       |
|  +-----------+-----------+  +----------+           |
+----------------------------------------------------+
               |                         |
         HTTP :8100                WS :6505
               |                         |
        AI Services                MCP Server
```

---

## Route Structure

| Route | Page | Description |
|-------|------|-------------|
| `/` | `page.tsx` | Home page with project list and quick-start actions |
| `/project/[id]` | `page.tsx` | Project workspace overview |
| `/project/[id]/chat` | `chat/page.tsx` | AI conversation for the project |
| `/project/[id]/assets` | `assets/page.tsx` | Asset management and generation |
| `/project/[id]/build` | `build/page.tsx` | Build configuration and export |
| `/templates` | `templates/page.tsx` | Template marketplace |
| `/settings` | `settings/page.tsx` | Platform-wide settings |

---

## Component Library

### Chat Components (`components/chat/`)

- **ChatWindow** -- Main chat container with message list and input area
- **MessageBubble** -- Individual message with markdown rendering, code blocks, and action buttons
- **CodeBlock** -- Syntax-highlighted code display with copy and apply buttons
- **AssetPreview** -- Inline preview of generated images, models, and audio
- **ContextIndicator** -- Shows what context is attached to the current conversation (scene, scripts)
- **TypingIndicator** -- Animated indicator while waiting for AI response

### Editor Components (`components/editor/`)

- **SceneTreeViewer** -- Read-only visualisation of the project's scene tree
- **ScriptEditor** -- Monaco-based code editor with GDScript syntax highlighting
- **PropertyInspector** -- View and edit node properties
- **FileExplorer** -- Project file tree with drag-and-drop

### Preview Components (`components/preview/`)

- **GamePreview** -- Embedded game player (HTML5 export) in an iframe
- **AssetGallery** -- Grid view of project assets with filtering
- **ModelViewer** -- Three.js-based 3D model preview
- **AudioPlayer** -- Waveform display with playback controls

### Asset Components (`components/assets/`)

- **GenerationForm** -- Prompt input with style presets and parameter controls
- **AssetCard** -- Thumbnail card with metadata and action buttons
- **BatchQueue** -- Displays batch generation progress
- **ImportDialog** -- Upload and import external assets

---

## State Management

State is managed with Zustand stores in `lib/stores/`.

### `projectStore`

```typescript
interface ProjectState {
  projects: Project[];
  currentProject: Project | null;
  loading: boolean;
  fetchProjects: () => Promise<void>;
  createProject: (data: CreateProjectInput) => Promise<Project>;
  selectProject: (id: string) => Promise<void>;
}
```

### `chatStore`

```typescript
interface ChatState {
  messages: Message[];
  isGenerating: boolean;
  context: ChatContext;
  sendMessage: (text: string) => Promise<void>;
  clearMessages: () => void;
  setContext: (ctx: Partial<ChatContext>) => void;
}
```

### `assetStore`

```typescript
interface AssetState {
  assets: Asset[];
  generationQueue: GenerationJob[];
  fetchAssets: (projectId: string) => Promise<void>;
  generateAsset: (request: GenerateRequest) => Promise<GenerationJob>;
  deleteAsset: (id: string) => Promise<void>;
}
```

---

## API Client (`lib/api.ts`)

Typed HTTP client for the AI Services REST API.

```typescript
import ky from "ky";

const api = ky.create({
  prefixUrl: process.env.NEXT_PUBLIC_API_URL,
  hooks: {
    beforeRequest: [
      (request) => {
        const token = localStorage.getItem("token");
        if (token) {
          request.headers.set("Authorization", `Bearer ${token}`);
        }
      },
    ],
  },
});

export const codegen = {
  generate: (body: CodeGenRequest) =>
    api.post("api/v1/codegen/generate", { json: body }).json<CodeGenResponse>(),
  fix: (body: FixRequest) =>
    api.post("api/v1/codegen/fix", { json: body }).json<CodeGenResponse>(),
};

// Similar exports for imagegen, modelgen, audiogen, npcai, etc.
```

## WebSocket Client (`lib/websocket.ts`)

Manages the WebSocket connection to the MCP server for real-time editor synchronisation.

```typescript
class MCPWebSocket {
  private ws: WebSocket;
  private pending: Map<string, { resolve: Function; reject: Function }>;

  connect(url: string): void {
    this.ws = new WebSocket(url);
    this.ws.onmessage = this.handleMessage.bind(this);
  }

  async callTool(name: string, args: Record<string, unknown>): Promise<unknown> {
    const id = crypto.randomUUID();
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
      this.ws.send(JSON.stringify({
        jsonrpc: "2.0",
        id,
        method: "tools/call",
        params: { name, arguments: args },
      }));
    });
  }
}
```

---

## Styling

The application uses Tailwind CSS with a custom design system defined in `styles/`. The theme supports light and dark modes and uses CSS variables for brand colours.

---

## Build and Development

```bash
cd packages/web-ui
npm install
npm run dev          # Development server on :3000
npm run build        # Production build
npm run start        # Start production server
npm run lint         # ESLint
npm run typecheck    # TypeScript type checking
```

---

## Deployment

The Web UI is deployed as a Docker container or as a static export on any CDN. In the enterprise stack, it runs behind the same reverse proxy as the AI services.

```bash
docker build -f docker/Dockerfile.web -t godotforge/web-ui .
docker run -p 3000:3000 godotforge/web-ui
```
