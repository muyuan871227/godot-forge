/**
 * PluginRegistry — Local JSON-backed registry for discovering and managing plugins.
 *
 * Stores plugin metadata in a JSON file on disk. In production this would be
 * backed by a database / remote API, but the JSON file works well for
 * development and single-user setups.
 */

import { readFile, writeFile, mkdir } from "node:fs/promises";
import { dirname } from "node:path";

import type { PluginMetadata, PluginType } from "./index.js";

// ---------------------------------------------------------------------------
// PluginRegistry
// ---------------------------------------------------------------------------

export class PluginRegistry {
  private registryPath: string;
  private cache: PluginMetadata[] | null = null;

  /**
   * @param registryPath Absolute path to the registry JSON file.
   *                     Created automatically if it doesn't exist.
   */
  constructor(registryPath: string) {
    this.registryPath = registryPath;
  }

  // -----------------------------------------------------------------------
  // CRUD
  // -----------------------------------------------------------------------

  /**
   * Register (or update) a plugin in the registry.
   *
   * If a plugin with the same ID already exists its metadata is replaced and
   * `updatedAt` is bumped.
   */
  async register(plugin: Omit<PluginMetadata, "downloads" | "rating" | "ratingCount" | "createdAt" | "updatedAt" | "verified"> & Partial<PluginMetadata>): Promise<PluginMetadata> {
    const plugins = await this.loadAll();
    const now = new Date().toISOString();

    const existingIndex = plugins.findIndex((p) => p.id === plugin.id);

    const entry: PluginMetadata = {
      downloads: 0,
      rating: 0,
      ratingCount: 0,
      createdAt: now,
      verified: false,
      ...plugin,
      updatedAt: now,
    };

    if (existingIndex >= 0) {
      // Preserve original creation date and accumulated stats
      entry.createdAt = plugins[existingIndex].createdAt;
      entry.downloads = plugins[existingIndex].downloads;
      entry.rating = plugins[existingIndex].rating;
      entry.ratingCount = plugins[existingIndex].ratingCount;
      plugins[existingIndex] = entry;
    } else {
      plugins.push(entry);
    }

    await this.saveAll(plugins);
    return entry;
  }

  /**
   * Search for plugins by keyword.
   *
   * Matches against name, description, keywords, and author name.
   * Optionally filter by plugin type.
   */
  async search(
    query: string,
    type?: PluginType,
    options?: { limit?: number; offset?: number; sortBy?: "downloads" | "rating" | "updatedAt" | "name" },
  ): Promise<{ plugins: PluginMetadata[]; total: number }> {
    let plugins = await this.loadAll();

    // Filter by type
    if (type) {
      plugins = plugins.filter((p) => p.type === type);
    }

    // Filter by query
    if (query.trim().length > 0) {
      const lowerQuery = query.toLowerCase();
      plugins = plugins.filter((p) => {
        const searchable = [
          p.name,
          p.description,
          p.author.name,
          ...p.keywords,
        ]
          .join(" ")
          .toLowerCase();
        return searchable.includes(lowerQuery);
      });
    }

    const total = plugins.length;

    // Sort
    const sortBy = options?.sortBy ?? "downloads";
    plugins.sort((a, b) => {
      switch (sortBy) {
        case "downloads":
          return b.downloads - a.downloads;
        case "rating":
          return b.rating - a.rating;
        case "updatedAt":
          return new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime();
        case "name":
          return a.name.localeCompare(b.name);
        default:
          return 0;
      }
    });

    // Pagination
    const offset = options?.offset ?? 0;
    const limit = options?.limit ?? 20;
    plugins = plugins.slice(offset, offset + limit);

    return { plugins, total };
  }

  /**
   * Get a single plugin by ID.
   * Returns `undefined` if not found.
   */
  async getPlugin(id: string): Promise<PluginMetadata | undefined> {
    const plugins = await this.loadAll();
    return plugins.find((p) => p.id === id);
  }

  /**
   * Remove a plugin from the registry.
   * Returns true if the plugin was found and removed.
   */
  async unregister(id: string): Promise<boolean> {
    const plugins = await this.loadAll();
    const filtered = plugins.filter((p) => p.id !== id);
    if (filtered.length === plugins.length) return false;
    await this.saveAll(filtered);
    return true;
  }

  /**
   * Increment the download counter for a plugin.
   */
  async recordDownload(id: string): Promise<void> {
    const plugins = await this.loadAll();
    const plugin = plugins.find((p) => p.id === id);
    if (plugin) {
      plugin.downloads += 1;
      await this.saveAll(plugins);
    }
  }

  /**
   * Add a rating to a plugin (1-5). Updates the running average.
   */
  async addRating(id: string, score: number): Promise<{ rating: number; ratingCount: number } | undefined> {
    if (score < 1 || score > 5) {
      throw new Error("Rating must be between 1 and 5");
    }

    const plugins = await this.loadAll();
    const plugin = plugins.find((p) => p.id === id);
    if (!plugin) return undefined;

    // Running average
    const totalScore = plugin.rating * plugin.ratingCount + score;
    plugin.ratingCount += 1;
    plugin.rating = Math.round((totalScore / plugin.ratingCount) * 100) / 100;

    await this.saveAll(plugins);
    return { rating: plugin.rating, ratingCount: plugin.ratingCount };
  }

  /**
   * List all plugins in the registry (no filtering).
   */
  async listAll(): Promise<PluginMetadata[]> {
    return this.loadAll();
  }

  // -----------------------------------------------------------------------
  // Persistence
  // -----------------------------------------------------------------------

  private async loadAll(): Promise<PluginMetadata[]> {
    if (this.cache !== null) return this.cache;

    try {
      const raw = await readFile(this.registryPath, "utf-8");
      const data = JSON.parse(raw);
      this.cache = Array.isArray(data) ? data : [];
    } catch {
      // File doesn't exist or is corrupt — start fresh
      this.cache = [];
    }

    return this.cache;
  }

  private async saveAll(plugins: PluginMetadata[]): Promise<void> {
    this.cache = plugins;
    await mkdir(dirname(this.registryPath), { recursive: true });
    await writeFile(this.registryPath, JSON.stringify(plugins, null, 2), "utf-8");
  }

  /** Force reload from disk on next access. */
  invalidateCache(): void {
    this.cache = null;
  }
}
