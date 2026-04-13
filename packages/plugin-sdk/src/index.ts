/**
 * @godot-forge/plugin-sdk — Plugin SDK for GodotForge
 *
 * Provides interfaces and types for building community plugins that extend
 * GodotForge with custom tools, AI providers, and asset generators.
 */

import { z } from "zod";

// ---------------------------------------------------------------------------
// Logger
// ---------------------------------------------------------------------------

/** Structured logger available to plugins via PluginContext. */
export interface Logger {
  info(message: string, meta?: Record<string, unknown>): void;
  warn(message: string, meta?: Record<string, unknown>): void;
  error(message: string, meta?: Record<string, unknown>): void;
  debug(message: string, meta?: Record<string, unknown>): void;
}

// ---------------------------------------------------------------------------
// Tool Definition
// ---------------------------------------------------------------------------

/** Schema for a single parameter in a tool definition. */
export interface ToolParameterSchema {
  type: "string" | "number" | "boolean" | "object" | "array";
  description: string;
  required?: boolean;
  default?: unknown;
  enum?: string[];
  items?: ToolParameterSchema;
  properties?: Record<string, ToolParameterSchema>;
}

/** Definition of an MCP-compatible tool that plugins can register. */
export interface ToolDefinition {
  /** Unique tool name, e.g. "midjourney_generate_image" */
  name: string;
  /** Human-readable description shown in tool listings */
  description: string;
  /** JSON-Schema-style parameter definitions */
  parameters: Record<string, ToolParameterSchema>;
  /** Handler invoked when the tool is called */
  execute(params: Record<string, unknown>): Promise<ToolResult>;
}

/** Result returned from a tool execution. */
export interface ToolResult {
  success: boolean;
  data?: unknown;
  error?: string;
  /** Optional artifacts (files, images, etc.) produced by the tool */
  artifacts?: Array<{
    type: "file" | "image" | "audio" | "model3d" | "text";
    path?: string;
    content?: string | Buffer;
    mimeType?: string;
    metadata?: Record<string, unknown>;
  }>;
}

// ---------------------------------------------------------------------------
// Asset Result
// ---------------------------------------------------------------------------

/** Result of an asset generation operation. */
export interface AssetResult {
  /** Whether generation succeeded */
  success: boolean;
  /** File paths of generated assets, relative to project root */
  files: Array<{
    path: string;
    type: "image" | "audio" | "model3d" | "scene" | "script" | "resource";
    size: number;
    metadata?: Record<string, unknown>;
  }>;
  /** Preview image/thumbnail if available */
  preview?: {
    path: string;
    width: number;
    height: number;
  };
  /** Error message if generation failed */
  error?: string;
  /** Time taken in milliseconds */
  durationMs?: number;
}

// ---------------------------------------------------------------------------
// Project API
// ---------------------------------------------------------------------------

/** API for interacting with the current Godot project. */
export interface ProjectAPI {
  /** Get the absolute path to the project root */
  getProjectPath(): string;

  /** Read a file from the project (path relative to project root) */
  readFile(relativePath: string): Promise<string>;

  /** Write a file to the project (path relative to project root) */
  writeFile(relativePath: string, content: string | Buffer): Promise<void>;

  /** Delete a file from the project */
  deleteFile(relativePath: string): Promise<void>;

  /** List files in a project directory */
  listFiles(relativePath?: string): Promise<string[]>;

  /** Check whether a file exists */
  fileExists(relativePath: string): Promise<boolean>;

  /** Get project metadata (name, version, etc.) */
  getProjectInfo(): Promise<{
    name: string;
    godotVersion: string;
    mainScene: string;
    features: string[];
  }>;
}

// ---------------------------------------------------------------------------
// Godot Connection
// ---------------------------------------------------------------------------

/** Interface for communicating with the Godot editor or runtime. */
export interface GodotConnection {
  /** Whether a Godot editor instance is currently connected */
  isConnected(): boolean;

  /** Send a command to the Godot editor via WebSocket */
  sendCommand(command: string, args?: Record<string, unknown>): Promise<unknown>;

  /** Run a GDScript expression and return the result */
  evaluate(gdscript: string): Promise<unknown>;

  /** Take a screenshot of the current editor/game viewport */
  screenshot(): Promise<Buffer>;

  /** Subscribe to editor events (scene changed, node selected, etc.) */
  on(event: string, handler: (data: unknown) => void): void;

  /** Unsubscribe from editor events */
  off(event: string, handler: (data: unknown) => void): void;
}

// ---------------------------------------------------------------------------
// AI Provider
// ---------------------------------------------------------------------------

/** Type of content an AI provider can generate. */
export type AIProviderType =
  | "code"
  | "image"
  | "audio"
  | "model3d"
  | "text"
  | "animation"
  | "level";

/** Configuration for an AI generation request. */
export interface AIGenerateOptions {
  prompt: string;
  /** Additional context for the generation */
  context?: Record<string, unknown>;
  /** Desired output format or parameters */
  outputConfig?: Record<string, unknown>;
  /** Timeout in milliseconds */
  timeoutMs?: number;
  /** Callback for streaming progress updates */
  onProgress?: (progress: number, message?: string) => void;
}

/** Result of an AI generation request. */
export interface AIGenerateResult {
  success: boolean;
  /** The generated content (type depends on provider) */
  content: unknown;
  /** File paths if content was written to disk */
  files?: string[];
  /** Token/credit usage information */
  usage?: {
    inputTokens?: number;
    outputTokens?: number;
    cost?: number;
    currency?: string;
  };
  error?: string;
}

/**
 * An AI provider that plugins can register to add new generation capabilities.
 * For example, a Midjourney plugin registers an image provider.
 */
export interface AIProvider {
  /** Unique provider ID, e.g. "midjourney" */
  id: string;
  /** Human-readable name, e.g. "Midjourney v6" */
  name: string;
  /** What type of content this provider generates */
  type: AIProviderType;
  /** Generate content from a prompt */
  generate(options: AIGenerateOptions): Promise<AIGenerateResult>;
  /** Check if the provider is available (API key set, service reachable, etc.) */
  isAvailable(): Promise<boolean>;
}

// ---------------------------------------------------------------------------
// Asset Generator
// ---------------------------------------------------------------------------

/**
 * An asset generator produces game-ready assets from parameters.
 * Unlike raw AI providers, generators handle the full pipeline:
 * prompt building, generation, post-processing, and Godot import.
 */
export interface AssetGenerator {
  /** Unique generator ID, e.g. "midjourney-spritesheet" */
  id: string;
  /** Human-readable name */
  name: string;
  /** Asset category for UI grouping */
  category: "sprite" | "tilemap" | "character" | "environment" | "ui" | "audio" | "model3d" | "effect" | "other";
  /** Zod schema describing the generator's input parameters */
  inputSchema: z.ZodType<unknown>;
  /** Run the generator and produce game-ready assets */
  generate(input: unknown, projectApi: ProjectAPI): Promise<AssetResult>;
}

// ---------------------------------------------------------------------------
// Plugin Context
// ---------------------------------------------------------------------------

/**
 * Context object passed to a plugin during activation.
 * Provides access to all extension points in GodotForge.
 */
export interface PluginContext {
  /** Register a new MCP-compatible tool */
  registerTool(tool: ToolDefinition): void;

  /** Register an AI generation provider */
  registerAIProvider(provider: AIProvider): void;

  /** Register an asset generator */
  registerAssetGenerator(generator: AssetGenerator): void;

  /** API for accessing and modifying the current project */
  projectApi: ProjectAPI;

  /** Connection to the Godot editor/runtime */
  godotConnection: GodotConnection;

  /** Structured logger */
  log: Logger;

  /** Plugin-scoped configuration store (persisted across sessions) */
  getConfig<T = unknown>(key: string): Promise<T | undefined>;
  setConfig<T = unknown>(key: string, value: T): Promise<void>;
}

// ---------------------------------------------------------------------------
// Plugin
// ---------------------------------------------------------------------------

/** Type of plugin for categorisation. */
export type PluginType = "ai-provider" | "asset-generator" | "tool" | "theme" | "template" | "integration";

/**
 * Main interface every GodotForge plugin must implement.
 *
 * A plugin module should default-export an object satisfying this interface.
 */
export interface GodotForgePlugin {
  /** Unique plugin identifier (reverse-domain style recommended) */
  id: string;
  /** Human-readable plugin name */
  name: string;
  /** Semantic version string */
  version: string;
  /** Plugin type for marketplace categorisation */
  type: PluginType;
  /** Optional description */
  description?: string;
  /** Optional author information */
  author?: {
    name: string;
    email?: string;
    url?: string;
  };
  /** Optional dependencies on other plugins */
  dependencies?: Record<string, string>;

  /**
   * Called when the plugin is activated.
   * Use the context to register tools, providers, and generators.
   */
  activate(context: PluginContext): Promise<void>;

  /**
   * Called when the plugin is deactivated.
   * Clean up any resources (timers, connections, temp files, etc.).
   */
  deactivate(): Promise<void>;
}

// ---------------------------------------------------------------------------
// Plugin Metadata (for registry)
// ---------------------------------------------------------------------------

/** Metadata stored in the plugin registry. */
export interface PluginMetadata {
  id: string;
  name: string;
  version: string;
  type: PluginType;
  description: string;
  author: {
    name: string;
    email?: string;
    url?: string;
  };
  /** npm package name or local path */
  source: string;
  /** Keywords for search */
  keywords: string[];
  /** Download count */
  downloads: number;
  /** Average rating (0-5) */
  rating: number;
  /** Number of ratings */
  ratingCount: number;
  /** ISO date string */
  createdAt: string;
  /** ISO date string */
  updatedAt: string;
  /** Whether the plugin is verified by the GodotForge team */
  verified: boolean;
}

// ---------------------------------------------------------------------------
// Re-exports
// ---------------------------------------------------------------------------

export { PluginLoader } from "./loader.js";
export { PluginRegistry } from "./registry.js";
