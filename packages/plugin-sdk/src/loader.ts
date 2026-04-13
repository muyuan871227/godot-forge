/**
 * PluginLoader — Dynamic loading and lifecycle management for GodotForge plugins.
 *
 * Supports loading plugins from:
 *   - A local file path (dynamic import)
 *   - An installed npm package (resolve from node_modules)
 *
 * Each loaded plugin goes through activate/deactivate lifecycle hooks.
 */

import { pathToFileURL } from "node:url";
import { resolve } from "node:path";
import { stat } from "node:fs/promises";

import type {
  GodotForgePlugin,
  PluginContext,
  ToolDefinition,
  AIProvider,
  AssetGenerator,
  Logger,
} from "./index.js";

// ---------------------------------------------------------------------------
// Internal types
// ---------------------------------------------------------------------------

interface ActivePlugin {
  plugin: GodotForgePlugin;
  context: PluginContext;
  registeredTools: string[];
  registeredProviders: string[];
  registeredGenerators: string[];
  activatedAt: Date;
}

// ---------------------------------------------------------------------------
// PluginLoader
// ---------------------------------------------------------------------------

export class PluginLoader {
  private activePlugins = new Map<string, ActivePlugin>();
  private tools = new Map<string, ToolDefinition>();
  private providers = new Map<string, AIProvider>();
  private generators = new Map<string, AssetGenerator>();
  private logger: Logger;

  constructor(logger?: Logger) {
    this.logger = logger ?? {
      info: (msg: string) => console.log(`[PluginLoader] ${msg}`),
      warn: (msg: string) => console.warn(`[PluginLoader] ${msg}`),
      error: (msg: string) => console.error(`[PluginLoader] ${msg}`),
      debug: (msg: string) => console.debug(`[PluginLoader] ${msg}`),
    };
  }

  // -----------------------------------------------------------------------
  // Loading
  // -----------------------------------------------------------------------

  /**
   * Load a plugin from a local file path.
   *
   * The file must default-export a {@link GodotForgePlugin} object.
   * Supports `.ts` (via tsx / ts-node) and `.js` files.
   */
  async loadFromPath(pluginPath: string): Promise<GodotForgePlugin> {
    const absolutePath = resolve(pluginPath);

    // Verify the path exists
    try {
      await stat(absolutePath);
    } catch {
      throw new Error(`Plugin path does not exist: ${absolutePath}`);
    }

    this.logger.info(`Loading plugin from path: ${absolutePath}`);

    try {
      const fileUrl = pathToFileURL(absolutePath).href;
      const mod = await import(fileUrl);
      const plugin = (mod.default ?? mod) as GodotForgePlugin;

      this.validatePlugin(plugin);
      this.logger.info(`Loaded plugin "${plugin.name}" v${plugin.version} (${plugin.id})`);
      return plugin;
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      throw new Error(`Failed to load plugin from ${absolutePath}: ${message}`);
    }
  }

  /**
   * Load a plugin from an installed npm package.
   *
   * The package must default-export a {@link GodotForgePlugin} object.
   */
  async loadFromPackage(packageName: string): Promise<GodotForgePlugin> {
    this.logger.info(`Loading plugin from package: ${packageName}`);

    try {
      const mod = await import(packageName);
      const plugin = (mod.default ?? mod) as GodotForgePlugin;

      this.validatePlugin(plugin);
      this.logger.info(`Loaded plugin "${plugin.name}" v${plugin.version} (${plugin.id})`);
      return plugin;
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      throw new Error(`Failed to load plugin package "${packageName}": ${message}`);
    }
  }

  // -----------------------------------------------------------------------
  // Lifecycle
  // -----------------------------------------------------------------------

  /**
   * Activate a loaded plugin by calling its `activate` method with a fresh context.
   *
   * The context collects all tools, providers, and generators registered by the plugin.
   */
  async activatePlugin(
    plugin: GodotForgePlugin,
    baseContext: Omit<PluginContext, "registerTool" | "registerAIProvider" | "registerAssetGenerator">,
  ): Promise<void> {
    if (this.activePlugins.has(plugin.id)) {
      this.logger.warn(`Plugin "${plugin.id}" is already active — deactivating first`);
      await this.deactivatePlugin(plugin.id);
    }

    const registeredTools: string[] = [];
    const registeredProviders: string[] = [];
    const registeredGenerators: string[] = [];

    // Build plugin-scoped context with registration hooks
    const context: PluginContext = {
      ...baseContext,

      registerTool: (tool: ToolDefinition) => {
        if (this.tools.has(tool.name)) {
          this.logger.warn(`Tool "${tool.name}" already registered — overwriting`);
        }
        this.tools.set(tool.name, tool);
        registeredTools.push(tool.name);
        this.logger.debug(`Plugin "${plugin.id}" registered tool: ${tool.name}`);
      },

      registerAIProvider: (provider: AIProvider) => {
        if (this.providers.has(provider.id)) {
          this.logger.warn(`AI provider "${provider.id}" already registered — overwriting`);
        }
        this.providers.set(provider.id, provider);
        registeredProviders.push(provider.id);
        this.logger.debug(`Plugin "${plugin.id}" registered AI provider: ${provider.id}`);
      },

      registerAssetGenerator: (generator: AssetGenerator) => {
        if (this.generators.has(generator.id)) {
          this.logger.warn(`Asset generator "${generator.id}" already registered — overwriting`);
        }
        this.generators.set(generator.id, generator);
        registeredGenerators.push(generator.id);
        this.logger.debug(`Plugin "${plugin.id}" registered asset generator: ${generator.id}`);
      },
    };

    try {
      await plugin.activate(context);
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      // Roll back any registrations from a failed activation
      for (const name of registeredTools) this.tools.delete(name);
      for (const id of registeredProviders) this.providers.delete(id);
      for (const id of registeredGenerators) this.generators.delete(id);
      throw new Error(`Failed to activate plugin "${plugin.id}": ${message}`);
    }

    this.activePlugins.set(plugin.id, {
      plugin,
      context,
      registeredTools,
      registeredProviders,
      registeredGenerators,
      activatedAt: new Date(),
    });

    this.logger.info(
      `Activated plugin "${plugin.id}": ` +
        `${registeredTools.length} tools, ` +
        `${registeredProviders.length} providers, ` +
        `${registeredGenerators.length} generators`,
    );
  }

  /**
   * Deactivate a plugin by its ID.
   *
   * Calls the plugin's `deactivate` method and removes all its registrations.
   */
  async deactivatePlugin(pluginId: string): Promise<void> {
    const entry = this.activePlugins.get(pluginId);
    if (!entry) {
      this.logger.warn(`Plugin "${pluginId}" is not active — nothing to deactivate`);
      return;
    }

    // Call the plugin's cleanup hook
    try {
      await entry.plugin.deactivate();
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      this.logger.error(`Error during deactivation of "${pluginId}": ${message}`);
    }

    // Remove all registrations
    for (const name of entry.registeredTools) this.tools.delete(name);
    for (const id of entry.registeredProviders) this.providers.delete(id);
    for (const id of entry.registeredGenerators) this.generators.delete(id);

    this.activePlugins.delete(pluginId);
    this.logger.info(`Deactivated plugin "${pluginId}"`);
  }

  // -----------------------------------------------------------------------
  // Queries
  // -----------------------------------------------------------------------

  /** List all currently active plugins. */
  listActivePlugins(): Array<{
    id: string;
    name: string;
    version: string;
    type: string;
    activatedAt: Date;
    tools: string[];
    providers: string[];
    generators: string[];
  }> {
    return Array.from(this.activePlugins.values()).map((entry) => ({
      id: entry.plugin.id,
      name: entry.plugin.name,
      version: entry.plugin.version,
      type: entry.plugin.type,
      activatedAt: entry.activatedAt,
      tools: [...entry.registeredTools],
      providers: [...entry.registeredProviders],
      generators: [...entry.registeredGenerators],
    }));
  }

  /** Get a registered tool by name. */
  getTool(name: string): ToolDefinition | undefined {
    return this.tools.get(name);
  }

  /** Get all registered tools. */
  getAllTools(): ToolDefinition[] {
    return Array.from(this.tools.values());
  }

  /** Get a registered AI provider by ID. */
  getProvider(id: string): AIProvider | undefined {
    return this.providers.get(id);
  }

  /** Get all registered AI providers. */
  getAllProviders(): AIProvider[] {
    return Array.from(this.providers.values());
  }

  /** Get a registered asset generator by ID. */
  getGenerator(id: string): AssetGenerator | undefined {
    return this.generators.get(id);
  }

  /** Get all registered asset generators. */
  getAllGenerators(): AssetGenerator[] {
    return Array.from(this.generators.values());
  }

  /** Check if a plugin is currently active. */
  isActive(pluginId: string): boolean {
    return this.activePlugins.has(pluginId);
  }

  // -----------------------------------------------------------------------
  // Validation
  // -----------------------------------------------------------------------

  private validatePlugin(plugin: unknown): asserts plugin is GodotForgePlugin {
    const p = plugin as Partial<GodotForgePlugin>;

    if (!p || typeof p !== "object") {
      throw new Error("Plugin module must export an object");
    }
    if (typeof p.id !== "string" || p.id.length === 0) {
      throw new Error("Plugin must have a non-empty string 'id'");
    }
    if (typeof p.name !== "string" || p.name.length === 0) {
      throw new Error("Plugin must have a non-empty string 'name'");
    }
    if (typeof p.version !== "string" || p.version.length === 0) {
      throw new Error("Plugin must have a non-empty string 'version'");
    }
    if (typeof p.type !== "string") {
      throw new Error("Plugin must have a string 'type'");
    }
    if (typeof p.activate !== "function") {
      throw new Error("Plugin must have an 'activate' function");
    }
    if (typeof p.deactivate !== "function") {
      throw new Error("Plugin must have a 'deactivate' function");
    }
  }
}
