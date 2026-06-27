import { Command } from "commander";
import { execSync } from "child_process";
import { readFileSync, writeFileSync, existsSync, mkdirSync } from "fs";
import { resolve, join } from "path";

const PLUGINS_DIR = ".godotforge/plugins";
const REGISTRY_FILE = ".godotforge/plugins.json";

interface PluginEntry {
  name: string;
  version: string;
  type: string;
  installedAt: string;
  enabled: boolean;
}

function ensurePluginDir(): void {
  if (!existsSync(PLUGINS_DIR)) {
    mkdirSync(PLUGINS_DIR, { recursive: true });
  }
  if (!existsSync(REGISTRY_FILE)) {
    writeFileSync(REGISTRY_FILE, JSON.stringify({ plugins: [] }, null, 2));
  }
}

function loadRegistry(): { plugins: PluginEntry[] } {
  ensurePluginDir();
  return JSON.parse(readFileSync(REGISTRY_FILE, "utf-8"));
}

function saveRegistry(registry: { plugins: PluginEntry[] }): void {
  writeFileSync(REGISTRY_FILE, JSON.stringify(registry, null, 2));
}

export function registerPluginCommand(program: Command): void {
  const plugin = program
    .command("plugin")
    .description("Manage GodotForge plugins");

  plugin
    .command("install <package>")
    .description("Install a plugin from npm")
    .option("--local <path>", "Install from local path instead of npm")
    .action(async (packageName: string, options: { local?: string }) => {
      console.log(`\nInstalling plugin: ${packageName}...\n`);

      try {
        if (options.local) {
          // Link local plugin
          execSync(`npm link ${resolve(options.local)}`, { stdio: "inherit" });
        } else {
          // Install from npm
          execSync(`npm install ${packageName}`, {
            stdio: "inherit",
            cwd: PLUGINS_DIR,
          });
        }

        // Register plugin
        const registry = loadRegistry();
        const existing = registry.plugins.find((p) => p.name === packageName);
        if (existing) {
          console.log(`Plugin ${packageName} already registered, updating...`);
          existing.version = "latest";
          existing.installedAt = new Date().toISOString();
        } else {
          registry.plugins.push({
            name: packageName,
            version: "latest",
            type: "unknown",
            installedAt: new Date().toISOString(),
            enabled: true,
          });
        }
        saveRegistry(registry);

        console.log(`\nPlugin ${packageName} installed successfully.`);
      } catch (error: any) {
        console.error(`Failed to install plugin: ${error.message}`);
        process.exit(1);
      }
    });

  plugin
    .command("list")
    .description("List installed plugins")
    .action(() => {
      const registry = loadRegistry();

      if (registry.plugins.length === 0) {
        console.log("\nNo plugins installed.\n");
        console.log("Install one with: godot-forge plugin install <package>");
        return;
      }

      console.log("\nInstalled plugins:\n");
      for (const p of registry.plugins) {
        const status = p.enabled ? "enabled" : "disabled";
        console.log(`  ${p.name}@${p.version} (${p.type}) [${status}]`);
      }
      console.log();
    });

  plugin
    .command("remove <package>")
    .description("Remove an installed plugin")
    .action((packageName: string) => {
      const registry = loadRegistry();
      const idx = registry.plugins.findIndex((p) => p.name === packageName);

      if (idx === -1) {
        console.error(`Plugin ${packageName} is not installed.`);
        process.exit(1);
      }

      registry.plugins.splice(idx, 1);
      saveRegistry(registry);

      try {
        execSync(`npm uninstall ${packageName}`, {
          stdio: "inherit",
          cwd: PLUGINS_DIR,
        });
      } catch {
        // Continue even if npm uninstall fails
      }

      console.log(`Plugin ${packageName} removed.`);
    });

  plugin
    .command("enable <package>")
    .description("Enable a disabled plugin")
    .action((packageName: string) => {
      const registry = loadRegistry();
      const p = registry.plugins.find((p) => p.name === packageName);
      if (!p) {
        console.error(`Plugin ${packageName} is not installed.`);
        process.exit(1);
      }
      p.enabled = true;
      saveRegistry(registry);
      console.log(`Plugin ${packageName} enabled.`);
    });

  plugin
    .command("disable <package>")
    .description("Disable a plugin without removing it")
    .action((packageName: string) => {
      const registry = loadRegistry();
      const p = registry.plugins.find((p) => p.name === packageName);
      if (!p) {
        console.error(`Plugin ${packageName} is not installed.`);
        process.exit(1);
      }
      p.enabled = false;
      saveRegistry(registry);
      console.log(`Plugin ${packageName} disabled.`);
    });

  plugin
    .command("search <query>")
    .description("Search for plugins in the registry")
    .action(async (query: string) => {
      console.log(`\nSearching for plugins matching "${query}"...\n`);
      try {
        const result = execSync(`npm search @godotforge ${query} --json`, {
          encoding: "utf-8",
        });
        const packages = JSON.parse(result);
        if (packages.length === 0) {
          console.log("No plugins found.");
        } else {
          for (const pkg of packages.slice(0, 10)) {
            console.log(`  ${pkg.name}@${pkg.version} — ${pkg.description || ""}`);
          }
        }
      } catch {
        console.log("Search is not available. Check npm connectivity.");
      }
      console.log();
    });
}
