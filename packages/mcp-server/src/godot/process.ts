import { spawn, ChildProcess } from "child_process";

const GODOT_PATH = process.env.GODOTFORGE_GODOT_PATH || "godot";

export interface GodotProcessOptions {
  projectPath: string;
  scene?: string;
  headless?: boolean;
  extraArgs?: string[];
}

/**
 * Manages a running Godot process (editor or game instance).
 */
export class GodotProcess {
  private process: ChildProcess | null = null;
  private running = false;
  private output: string[] = [];

  async start(options: GodotProcessOptions): Promise<void> {
    if (this.running) {
      throw new Error("Godot process already running");
    }

    const args = ["--path", options.projectPath];

    if (options.headless) {
      args.push("--headless");
    }
    if (options.scene) {
      args.push(options.scene);
    }
    if (options.extraArgs) {
      args.push(...options.extraArgs);
    }

    this.process = spawn(GODOT_PATH, args);
    this.running = true;
    this.output = [];

    this.process.stdout?.on("data", (data) => {
      this.output.push(data.toString());
    });

    this.process.stderr?.on("data", (data) => {
      this.output.push(data.toString());
    });

    this.process.on("close", () => {
      this.running = false;
    });
  }

  stop(): void {
    if (this.process && this.running) {
      this.process.kill("SIGTERM");
      this.running = false;
    }
  }

  get isRunning(): boolean {
    return this.running;
  }

  getOutput(lines?: number): string[] {
    if (lines) {
      return this.output.slice(-lines);
    }
    return [...this.output];
  }
}
