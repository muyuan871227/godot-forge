/**
 * Example community plugin — Midjourney Image Provider for GodotForge
 *
 * Demonstrates how to build a plugin that:
 *   1. Registers an AI provider (Midjourney image generation)
 *   2. Registers an asset generator (sprite sheet pipeline)
 *   3. Registers a tool (direct Midjourney prompt tool)
 *
 * Usage:
 *   import midjourneyPlugin from "./plugin-midjourney.js";
 *   await loader.activatePlugin(midjourneyPlugin, context);
 */

import { z } from "zod";
import type {
  GodotForgePlugin,
  PluginContext,
  AIProvider,
  AIGenerateOptions,
  AIGenerateResult,
  AssetGenerator,
  AssetResult,
  ProjectAPI,
  ToolDefinition,
  ToolResult,
} from "@godot-forge/plugin-sdk";

// ---------------------------------------------------------------------------
// Midjourney API client (simplified for example)
// ---------------------------------------------------------------------------

interface MidjourneyConfig {
  apiKey: string;
  baseUrl: string;
  defaultModel: string;
}

class MidjourneyClient {
  private config: MidjourneyConfig;

  constructor(config: MidjourneyConfig) {
    this.config = config;
  }

  async imagine(prompt: string, options?: {
    aspectRatio?: string;
    style?: string;
    chaos?: number;
    quality?: number;
  }): Promise<{ imageUrl: string; taskId: string }> {
    // Build the full prompt with Midjourney parameters
    let fullPrompt = prompt;
    if (options?.aspectRatio) fullPrompt += ` --ar ${options.aspectRatio}`;
    if (options?.style) fullPrompt += ` --style ${options.style}`;
    if (options?.chaos) fullPrompt += ` --chaos ${options.chaos}`;
    if (options?.quality) fullPrompt += ` --q ${options.quality}`;

    const response = await fetch(`${this.config.baseUrl}/imagine`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${this.config.apiKey}`,
      },
      body: JSON.stringify({ prompt: fullPrompt, model: this.config.defaultModel }),
    });

    if (!response.ok) {
      throw new Error(`Midjourney API error: ${response.status} ${response.statusText}`);
    }

    const result = (await response.json()) as { imageUrl: string; taskId: string };
    return result;
  }

  async downloadImage(imageUrl: string): Promise<Buffer> {
    const response = await fetch(imageUrl);
    if (!response.ok) {
      throw new Error(`Failed to download image: ${response.status}`);
    }
    return Buffer.from(await response.arrayBuffer());
  }

  async checkHealth(): Promise<boolean> {
    try {
      const response = await fetch(`${this.config.baseUrl}/health`, {
        headers: { Authorization: `Bearer ${this.config.apiKey}` },
      });
      return response.ok;
    } catch {
      return false;
    }
  }
}

// ---------------------------------------------------------------------------
// AI Provider: Midjourney image generation
// ---------------------------------------------------------------------------

function createMidjourneyProvider(client: MidjourneyClient): AIProvider {
  return {
    id: "midjourney",
    name: "Midjourney v6",
    type: "image",

    async generate(options: AIGenerateOptions): Promise<AIGenerateResult> {
      try {
        const config = (options.outputConfig ?? {}) as Record<string, unknown>;
        const result = await client.imagine(options.prompt, {
          aspectRatio: config.aspectRatio as string | undefined,
          style: config.style as string | undefined,
          chaos: config.chaos as number | undefined,
          quality: config.quality as number | undefined,
        });

        return {
          success: true,
          content: {
            imageUrl: result.imageUrl,
            taskId: result.taskId,
          },
        };
      } catch (err) {
        return {
          success: false,
          content: null,
          error: err instanceof Error ? err.message : String(err),
        };
      }
    },

    async isAvailable(): Promise<boolean> {
      return client.checkHealth();
    },
  };
}

// ---------------------------------------------------------------------------
// Asset Generator: Sprite sheet from Midjourney
// ---------------------------------------------------------------------------

const spriteSheetInputSchema = z.object({
  characterDescription: z.string().describe("Description of the character to generate"),
  frameCount: z.number().min(1).max(16).default(4).describe("Number of animation frames"),
  frameSize: z.number().min(16).max(512).default(64).describe("Size of each frame in pixels"),
  animationType: z
    .enum(["idle", "walk", "run", "attack", "jump", "death"])
    .default("idle")
    .describe("Type of animation to generate"),
  style: z.string().default("pixel art").describe("Art style for the sprite"),
  transparent: z.boolean().default(true).describe("Whether the background should be transparent"),
});

type SpriteSheetInput = z.infer<typeof spriteSheetInputSchema>;

function createSpriteSheetGenerator(client: MidjourneyClient): AssetGenerator {
  return {
    id: "midjourney-spritesheet",
    name: "Midjourney Sprite Sheet Generator",
    category: "sprite",
    inputSchema: spriteSheetInputSchema,

    async generate(rawInput: unknown, projectApi: ProjectAPI): Promise<AssetResult> {
      const startTime = Date.now();

      // Validate input
      const input = spriteSheetInputSchema.parse(rawInput) as SpriteSheetInput;

      // Build a Midjourney-optimized prompt for sprite sheets
      const prompt = [
        `${input.style} sprite sheet`,
        `${input.characterDescription}`,
        `${input.frameCount} frames of ${input.animationType} animation`,
        `${input.frameSize}x${input.frameSize} pixel frames`,
        input.transparent ? "transparent background" : "",
        "game asset, clean lines, consistent style across all frames",
        "--ar 4:1 --style raw --no text --no watermark",
      ]
        .filter(Boolean)
        .join(", ");

      try {
        const result = await client.imagine(prompt);
        const imageData = await client.downloadImage(result.imageUrl);

        // Write the sprite sheet to the project
        const filename = `sprites/${input.animationType}_${Date.now()}.png`;
        await projectApi.writeFile(filename, imageData.toString("base64"));

        // Write a .tres import resource for Godot
        const importConfig = [
          "[remap]",
          "",
          `path="res://${filename}"`,
          'importer="texture"',
          "",
          "[params]",
          "",
          `process/size_limit=${input.frameSize * input.frameCount}`,
          `detect_3d/compress_to=0`,
        ].join("\n");

        const importPath = `${filename}.import`;
        await projectApi.writeFile(importPath, importConfig);

        return {
          success: true,
          files: [
            {
              path: filename,
              type: "image",
              size: imageData.length,
              metadata: {
                frameCount: input.frameCount,
                frameSize: input.frameSize,
                animationType: input.animationType,
                midjourneyTaskId: result.taskId,
              },
            },
          ],
          preview: {
            path: filename,
            width: input.frameSize * input.frameCount,
            height: input.frameSize,
          },
          durationMs: Date.now() - startTime,
        };
      } catch (err) {
        return {
          success: false,
          files: [],
          error: err instanceof Error ? err.message : String(err),
          durationMs: Date.now() - startTime,
        };
      }
    },
  };
}

// ---------------------------------------------------------------------------
// Tool: Direct Midjourney prompt
// ---------------------------------------------------------------------------

function createMidjourneyTool(client: MidjourneyClient): ToolDefinition {
  return {
    name: "midjourney_generate_image",
    description:
      "Generate an image using Midjourney. Returns an image URL that can be " +
      "downloaded and imported into the project as a texture, sprite, or background.",
    parameters: {
      prompt: {
        type: "string",
        description: "The image generation prompt",
        required: true,
      },
      aspect_ratio: {
        type: "string",
        description: "Aspect ratio (e.g. '16:9', '1:1', '4:3')",
        default: "1:1",
      },
      style: {
        type: "string",
        description: "Midjourney style preset",
        enum: ["raw", "scenic", "cute", "expressive"],
        default: "raw",
      },
      save_to: {
        type: "string",
        description: "Optional project-relative path to save the image",
      },
    },

    async execute(params: Record<string, unknown>): Promise<ToolResult> {
      const prompt = params.prompt as string;
      if (!prompt) {
        return { success: false, error: "prompt is required" };
      }

      try {
        const result = await client.imagine(prompt, {
          aspectRatio: params.aspect_ratio as string | undefined,
          style: params.style as string | undefined,
        });

        return {
          success: true,
          data: {
            imageUrl: result.imageUrl,
            taskId: result.taskId,
          },
          artifacts: [
            {
              type: "image",
              path: params.save_to as string | undefined,
              mimeType: "image/png",
              metadata: { taskId: result.taskId },
            },
          ],
        };
      } catch (err) {
        return {
          success: false,
          error: err instanceof Error ? err.message : String(err),
        };
      }
    },
  };
}

// ---------------------------------------------------------------------------
// Plugin entry point
// ---------------------------------------------------------------------------

let midjourneyClient: MidjourneyClient | null = null;

const midjourneyPlugin: GodotForgePlugin = {
  id: "community.midjourney",
  name: "Midjourney for GodotForge",
  version: "1.0.0",
  type: "ai-provider",
  description: "Adds Midjourney image generation as an AI provider, with sprite sheet and texture asset generators.",
  author: {
    name: "GodotForge Community",
    url: "https://github.com/godot-forge/plugin-midjourney",
  },
  dependencies: {},

  async activate(context: PluginContext): Promise<void> {
    context.log.info("Activating Midjourney plugin...");

    // Load configuration
    const apiKey = await context.getConfig<string>("midjourney_api_key");
    const baseUrl = await context.getConfig<string>("midjourney_base_url");

    if (!apiKey) {
      context.log.warn(
        "Midjourney API key not configured. Set it via plugin settings: midjourney_api_key",
      );
    }

    midjourneyClient = new MidjourneyClient({
      apiKey: apiKey ?? "",
      baseUrl: baseUrl ?? "https://api.midjourney.example.com/v1",
      defaultModel: "v6",
    });

    // Register the AI provider
    context.registerAIProvider(createMidjourneyProvider(midjourneyClient));

    // Register the sprite sheet asset generator
    context.registerAssetGenerator(createSpriteSheetGenerator(midjourneyClient));

    // Register the direct-prompt tool
    context.registerTool(createMidjourneyTool(midjourneyClient));

    context.log.info("Midjourney plugin activated successfully");
  },

  async deactivate(): Promise<void> {
    midjourneyClient = null;
  },
};

export default midjourneyPlugin;
