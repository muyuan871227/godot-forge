import { captureScreenshot } from "./headless.js";
import { readFileSync } from "fs";

/**
 * Capture a screenshot and return it as base64 PNG.
 */
export async function takeScreenshot(
  projectPath: string,
  scenePath: string,
): Promise<{ base64: string; width: number; height: number }> {
  const outputPath = `/tmp/godotforge/screenshot_${Date.now()}.png`;

  const result = await captureScreenshot(projectPath, scenePath, outputPath);

  if (!result.success) {
    throw new Error(`Screenshot failed: ${JSON.stringify(result.data)}`);
  }

  const imageBuffer = readFileSync(outputPath);
  const base64 = imageBuffer.toString("base64");

  return {
    base64,
    width: result.data.size?.[0] ?? 0,
    height: result.data.size?.[1] ?? 0,
  };
}
