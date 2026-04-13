import { spawn } from "child_process";
import { resolve } from "path";

const GODOT_PATH = process.env.GODOTFORGE_GODOT_PATH || "godot";
const SCRIPTS_DIR = resolve(import.meta.dirname, "../../scripts");

export interface HeadlessResult {
  success: boolean;
  data: Record<string, any>;
  stderr: string;
}

/**
 * Run a Godot headless operation using the godot_operations.gd script.
 */
export async function runHeadlessOperation(
  projectPath: string,
  operation: string,
  params: Record<string, any> = {},
  timeout = 60000,
): Promise<HeadlessResult> {
  return new Promise((resolve, reject) => {
    const args = [
      "--headless",
      "--path", projectPath,
      "--script", `${SCRIPTS_DIR}/godot_operations.gd`,
      "--operation", operation,
      "--params", JSON.stringify(params),
    ];

    const proc = spawn(GODOT_PATH, args, { timeout });
    let stdout = "";
    let stderr = "";

    proc.stdout.on("data", (data) => { stdout += data.toString(); });
    proc.stderr.on("data", (data) => { stderr += data.toString(); });

    proc.on("close", (code) => {
      try {
        const data = JSON.parse(stdout.trim());
        resolve({ success: code === 0, data, stderr });
      } catch {
        resolve({
          success: false,
          data: { error: "Failed to parse output", raw: stdout },
          stderr,
        });
      }
    });

    proc.on("error", (err) => {
      reject(new Error(`Failed to run Godot: ${err.message}`));
    });
  });
}

/**
 * Take a screenshot of a Godot scene.
 */
export async function captureScreenshot(
  projectPath: string,
  scenePath: string,
  outputPath: string,
  waitFrames = 10,
): Promise<HeadlessResult> {
  return runHeadlessOperation(projectPath, "screenshot", {
    scene: scenePath,
    output: outputPath,
    wait_frames: waitFrames,
  });
}

/**
 * Validate a Godot project (check for script errors, missing resources).
 */
export async function validateProject(projectPath: string): Promise<HeadlessResult> {
  return runHeadlessOperation(projectPath, "validate_project");
}

/**
 * Run a compile check on all GDScript files.
 */
export async function compileCheck(projectPath: string): Promise<HeadlessResult> {
  return runHeadlessOperation(projectPath, "compile_check");
}
