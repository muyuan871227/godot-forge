import { Command } from "commander";
import fetch from "node-fetch";
import * as fs from "node:fs";
import * as path from "node:path";

const DEFAULT_AI_URL = "http://localhost:8100";

interface AssetListOptions {
  dir: string;
}

interface AssetGenerateOptions {
  type: string;
  output: string;
  url: string;
}

interface AssetImportOptions {
  target: string;
}

/** Recursively collect files matching common game-asset extensions. */
function collectAssets(dir: string): string[] {
  const extensions = new Set([
    ".png", ".jpg", ".jpeg", ".webp", ".svg",         // images
    ".glb", ".gltf", ".obj", ".fbx",                  // 3D models
    ".wav", ".ogg", ".mp3",                            // audio
    ".tres", ".res",                                   // Godot resources
    ".ttf", ".otf", ".woff", ".woff2",                 // fonts
    ".tscn",                                           // scenes
    ".gdshader", ".shader",                            // shaders
  ]);

  const results: string[] = [];

  function walk(current: string): void {
    if (!fs.existsSync(current)) return;
    for (const entry of fs.readdirSync(current, { withFileTypes: true })) {
      const full = path.join(current, entry.name);
      if (entry.isDirectory()) {
        // Skip hidden directories and .godot cache
        if (!entry.name.startsWith(".")) {
          walk(full);
        }
      } else {
        const ext = path.extname(entry.name).toLowerCase();
        if (extensions.has(ext)) {
          results.push(full);
        }
      }
    }
  }

  walk(dir);
  return results;
}

/** Pretty-print file size. */
function humanSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function registerAssetCommand(program: Command): void {
  const asset = program
    .command("asset")
    .description("Manage game assets (list, generate, import)");

  // --- asset list ---
  asset
    .command("list")
    .description("List all game assets in the project")
    .option("-d, --dir <dir>", "Project root directory", ".")
    .action((options: AssetListOptions) => {
      const dir = path.resolve(options.dir);
      console.log(`Scanning assets in ${dir}\n`);

      const files = collectAssets(dir);
      if (files.length === 0) {
        console.log("No assets found.");
        return;
      }

      // Group by extension category.
      const categories: Record<string, string[]> = {};
      for (const file of files) {
        const ext = path.extname(file).toLowerCase();
        let cat: string;
        if ([".png", ".jpg", ".jpeg", ".webp", ".svg"].includes(ext)) {
          cat = "Images";
        } else if ([".glb", ".gltf", ".obj", ".fbx"].includes(ext)) {
          cat = "3D Models";
        } else if ([".wav", ".ogg", ".mp3"].includes(ext)) {
          cat = "Audio";
        } else if ([".tres", ".res"].includes(ext)) {
          cat = "Resources";
        } else if ([".tscn"].includes(ext)) {
          cat = "Scenes";
        } else if ([".ttf", ".otf", ".woff", ".woff2"].includes(ext)) {
          cat = "Fonts";
        } else if ([".gdshader", ".shader"].includes(ext)) {
          cat = "Shaders";
        } else {
          cat = "Other";
        }
        if (!categories[cat]) categories[cat] = [];
        categories[cat].push(file);
      }

      for (const [cat, catFiles] of Object.entries(categories)) {
        console.log(`${cat} (${catFiles.length}):`);
        for (const f of catFiles) {
          const rel = path.relative(dir, f);
          const stat = fs.statSync(f);
          console.log(`  ${rel}  (${humanSize(stat.size)})`);
        }
        console.log("");
      }

      console.log(`Total: ${files.length} assets`);
    });

  // --- asset generate ---
  asset
    .command("generate")
    .description("Generate a game asset via AI")
    .argument("<prompt>", "Description of the asset to generate")
    .option(
      "-t, --type <type>",
      "Asset type: sprite | model | audio | tilemap",
      "sprite",
    )
    .option("-o, --output <dir>", "Output directory", ".")
    .option("--url <url>", "AI services base URL", DEFAULT_AI_URL)
    .action(async (prompt: string, options: AssetGenerateOptions) => {
      const validTypes = ["sprite", "model", "audio", "tilemap"];
      if (!validTypes.includes(options.type)) {
        console.error(
          `Invalid asset type "${options.type}". Must be one of: ${validTypes.join(", ")}`,
        );
        process.exit(1);
      }

      // Map asset types to AI service endpoints.
      const endpointMap: Record<string, string> = {
        sprite: "/api/v1/imagegen/generate",
        model: "/api/v1/modelgen/generate",
        audio: "/api/v1/audiogen/generate",
        tilemap: "/api/v1/imagegen/tilemap",
      };

      const url = `${options.url}${endpointMap[options.type]}`;
      const outputDir = path.resolve(options.output);

      console.log(`Generating ${options.type} asset...`);
      console.log(`  Prompt : ${prompt}`);
      console.log(`  Service: ${url}`);
      console.log(`  Output : ${outputDir}`);
      console.log("");

      let response: Awaited<ReturnType<typeof fetch>>;
      try {
        response = await fetch(url, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ prompt, type: options.type }),
        });
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : String(err);
        console.error("Failed to connect to AI services.");
        console.error(`  ${message}`);
        console.error("");
        console.error("Make sure the AI services are running:");
        console.error("  godot-forge serve");
        process.exit(1);
      }

      if (!response.ok) {
        const text = await response.text();
        console.error(
          `AI service returned HTTP ${response.status}: ${text}`,
        );
        process.exit(1);
      }

      const data = (await response.json()) as {
        success: boolean;
        files?: Array<{ path: string; content: string; encoding?: string }>;
        error?: string;
      };

      if (!data.success) {
        console.error(`Generation failed: ${data.error ?? "unknown error"}`);
        process.exit(1);
      }

      if (data.files && data.files.length > 0) {
        fs.mkdirSync(outputDir, { recursive: true });
        for (const file of data.files) {
          const filePath = path.resolve(outputDir, file.path);
          fs.mkdirSync(path.dirname(filePath), { recursive: true });

          if (file.encoding === "base64") {
            fs.writeFileSync(filePath, Buffer.from(file.content, "base64"));
          } else {
            fs.writeFileSync(filePath, file.content, "utf-8");
          }
          console.log(`  Created: ${filePath}`);
        }
      }

      console.log("");
      console.log("Asset generation complete.");
    });

  // --- asset import ---
  asset
    .command("import")
    .description("Import an external asset file into the project")
    .argument("<file>", "Path to the asset file to import")
    .option(
      "-t, --target <dir>",
      "Target directory inside the project (e.g. assets/sprites)",
      "assets",
    )
    .action((file: string, options: AssetImportOptions) => {
      const srcPath = path.resolve(file);

      if (!fs.existsSync(srcPath)) {
        console.error(`File not found: ${srcPath}`);
        process.exit(1);
      }

      if (!fs.statSync(srcPath).isFile()) {
        console.error(`Not a file: ${srcPath}`);
        process.exit(1);
      }

      const targetDir = path.resolve(options.target);
      fs.mkdirSync(targetDir, { recursive: true });

      const destPath = path.join(targetDir, path.basename(srcPath));
      if (fs.existsSync(destPath)) {
        console.error(`File already exists at ${destPath}`);
        console.error("Remove it first or choose a different target.");
        process.exit(1);
      }

      fs.copyFileSync(srcPath, destPath);
      console.log(`Imported: ${srcPath}`);
      console.log(`      -> ${destPath}`);

      // Create a minimal .import hint if this is an image.
      const ext = path.extname(destPath).toLowerCase();
      if ([".png", ".jpg", ".jpeg", ".webp"].includes(ext)) {
        console.log(
          "  (Godot will auto-import this texture on next editor launch)",
        );
      }
    });
}
