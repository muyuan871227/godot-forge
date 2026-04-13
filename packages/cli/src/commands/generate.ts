import { Command } from "commander";
import fetch from "node-fetch";

const DEFAULT_AI_URL = "http://localhost:8100";
const GENERATE_ENDPOINT = "/api/v1/codegen/generate";

type GenerateType = "code" | "scene" | "asset" | "full";

interface GenerateOptions {
  type: GenerateType;
  apply: boolean;
  output?: string;
  url: string;
}

interface GenerateRequest {
  prompt: string;
  type: GenerateType;
  apply: boolean;
  project_dir?: string;
}

interface GenerateResponse {
  success: boolean;
  type: GenerateType;
  files?: Array<{ path: string; content: string }>;
  code?: string;
  scene?: string;
  error?: string;
  message?: string;
}

/** Write generated files to disk when --apply is used. */
async function applyFiles(
  files: Array<{ path: string; content: string }>,
  outputDir: string,
): Promise<void> {
  const fs = await import("node:fs");
  const path = await import("node:path");

  for (const file of files) {
    const filePath = path.resolve(outputDir, file.path);
    fs.mkdirSync(path.dirname(filePath), { recursive: true });
    fs.writeFileSync(filePath, file.content, "utf-8");
    console.log(`  Written: ${filePath}`);
  }
}

export function registerGenerateCommand(program: Command): void {
  program
    .command("generate")
    .description("Generate game content from a natural-language prompt")
    .argument("<prompt>", "Natural-language description of what to generate")
    .option(
      "-t, --type <type>",
      "Generation type: code | scene | asset | full",
      "code",
    )
    .option(
      "-a, --apply",
      "Apply generated output directly to the project directory",
      false,
    )
    .option(
      "-o, --output <dir>",
      "Output directory when --apply is used (defaults to cwd)",
    )
    .option(
      "--url <url>",
      "AI services base URL",
      DEFAULT_AI_URL,
    )
    .action(async (prompt: string, options: GenerateOptions) => {
      const validTypes: GenerateType[] = ["code", "scene", "asset", "full"];
      if (!validTypes.includes(options.type)) {
        console.error(
          `Invalid type "${options.type}". Must be one of: ${validTypes.join(", ")}`,
        );
        process.exit(1);
      }

      const url = `${options.url}${GENERATE_ENDPOINT}`;
      const outputDir = options.output ?? process.cwd();

      console.log(`Generating ${options.type} content...`);
      console.log(`  Prompt : ${prompt}`);
      console.log(`  Service: ${url}`);
      if (options.apply) {
        console.log(`  Output : ${outputDir}`);
      }
      console.log("");

      const body: GenerateRequest = {
        prompt,
        type: options.type,
        apply: options.apply,
        project_dir: options.apply ? outputDir : undefined,
      };

      let response: Awaited<ReturnType<typeof fetch>>;
      try {
        response = await fetch(url, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        });
      } catch (err: unknown) {
        const message =
          err instanceof Error ? err.message : String(err);
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

      const data = (await response.json()) as GenerateResponse;

      if (!data.success) {
        console.error(`Generation failed: ${data.error ?? "unknown error"}`);
        process.exit(1);
      }

      // Display the generated content.
      if (data.message) {
        console.log(data.message);
        console.log("");
      }

      if (data.files && data.files.length > 0) {
        if (options.apply) {
          console.log("Applying generated files:");
          await applyFiles(data.files, outputDir);
        } else {
          console.log("Generated files (use --apply to write to disk):");
          for (const file of data.files) {
            console.log(`\n--- ${file.path} ---`);
            console.log(file.content);
          }
        }
      } else if (data.code) {
        console.log("Generated code:");
        console.log(data.code);
      } else if (data.scene) {
        console.log("Generated scene:");
        console.log(data.scene);
      }

      console.log("");
      console.log("Generation complete.");
    });
}
