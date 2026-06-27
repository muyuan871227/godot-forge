import { Command } from "commander";
import { spawn, type ChildProcess } from "node:child_process";
import * as path from "node:path";

interface ServeOptions {
  aiPort: string;
  mcpPort: string;
  aiOnly: boolean;
  mcpOnly: boolean;
}

/** Resolve a sibling package directory in the monorepo. */
function resolvePackage(name: string): string {
  const cliDir = path.resolve(
    new URL(import.meta.url).pathname,
    "..",
    "..",
    "..",
  );
  return path.join(cliDir, "..", name);
}

/** Check if a command exists on PATH by trying `which`. */
async function commandExists(cmd: string): Promise<boolean> {
  const { execSync } = await import("node:child_process");
  try {
    execSync(`which ${cmd}`, { stdio: "ignore" });
    return true;
  } catch {
    return false;
  }
}

/**
 * Spawn a child process with prefixed stdout/stderr output.
 * Returns the ChildProcess handle for cleanup.
 */
function spawnService(
  label: string,
  command: string,
  args: string[],
  options: { cwd: string; env?: Record<string, string> },
): ChildProcess {
  const env = { ...process.env, ...options.env };
  const child = spawn(command, args, {
    cwd: options.cwd,
    env,
    stdio: ["ignore", "pipe", "pipe"],
  });

  const prefix = `[${label}]`;

  child.stdout?.on("data", (chunk: Buffer) => {
    for (const line of chunk.toString().split("\n")) {
      if (line.trim()) {
        console.log(`${prefix} ${line}`);
      }
    }
  });

  child.stderr?.on("data", (chunk: Buffer) => {
    for (const line of chunk.toString().split("\n")) {
      if (line.trim()) {
        console.error(`${prefix} ${line}`);
      }
    }
  });

  child.on("error", (err) => {
    console.error(`${prefix} Failed to start: ${err.message}`);
  });

  child.on("exit", (code, signal) => {
    if (signal) {
      console.log(`${prefix} Terminated by ${signal}`);
    } else if (code !== 0) {
      console.error(`${prefix} Exited with code ${code}`);
    }
  });

  return child;
}

export function registerServeCommand(program: Command): void {
  program
    .command("serve")
    .description("Start GodotForge services (AI services + MCP server)")
    .option("--ai-port <port>", "AI services port", "8100")
    .option("--mcp-port <port>", "MCP WebSocket port", "6505")
    .option("--ai-only", "Start only the AI services", false)
    .option("--mcp-only", "Start only the MCP server", false)
    .action(async (options: ServeOptions) => {
      const children: ChildProcess[] = [];

      const cleanup = () => {
        console.log("\nShutting down services...");
        for (const child of children) {
          if (!child.killed) {
            child.kill("SIGTERM");
          }
        }
      };

      process.on("SIGINT", cleanup);
      process.on("SIGTERM", cleanup);

      const startAI = !options.mcpOnly;
      const startMCP = !options.aiOnly;

      // --- AI Services (Python / uvicorn) ---
      if (startAI) {
        const aiDir = resolvePackage("ai-services");
        const hasPython = await commandExists("python3");
        const pythonCmd = hasPython ? "python3" : "python";

        console.log(`Starting AI services on port ${options.aiPort}...`);
        console.log(`  Directory: ${aiDir}`);

        const aiChild = spawnService(
          "AI",
          pythonCmd,
          [
            "-m",
            "uvicorn",
            "src.main:app",
            "--host",
            "0.0.0.0",
            "--port",
            options.aiPort,
            "--reload",
          ],
          {
            cwd: aiDir,
            env: {
              AI_PORT: options.aiPort,
            },
          },
        );
        children.push(aiChild);
      }

      // --- MCP Server (TypeScript / Node) ---
      if (startMCP) {
        const mcpDir = resolvePackage("mcp-server");
        const hasNpx = await commandExists("npx");

        console.log(`Starting MCP server on port ${options.mcpPort}...`);
        console.log(`  Directory: ${mcpDir}`);

        if (hasNpx) {
          const mcpChild = spawnService(
            "MCP",
            "npx",
            ["tsx", "src/index.ts"],
            {
              cwd: mcpDir,
              env: {
                GODOT_MCP_PORT: options.mcpPort,
              },
            },
          );
          children.push(mcpChild);
        } else {
          console.error("[MCP] npx not found — cannot start MCP server.");
          console.error("[MCP] Make sure Node.js >= 18 is installed.");
        }
      }

      if (children.length === 0) {
        console.error("No services were started.");
        process.exit(1);
      }

      console.log("");
      console.log("GodotForge services are running.");
      if (startAI) {
        console.log(`  AI services : http://localhost:${options.aiPort}`);
      }
      if (startMCP) {
        console.log(`  MCP server  : ws://localhost:${options.mcpPort}`);
      }
      console.log("");
      console.log("Press Ctrl+C to stop all services.");

      // Keep the process alive until a child exits with an error or we are killed.
      await new Promise<void>((resolve) => {
        let exited = 0;
        for (const child of children) {
          child.on("exit", () => {
            exited++;
            if (exited === children.length) {
              resolve();
            }
          });
        }
      });
    });
}
