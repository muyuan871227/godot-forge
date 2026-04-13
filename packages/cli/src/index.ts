#!/usr/bin/env node

import { Command } from "commander";
import { registerInitCommand } from "./commands/init.js";
import { registerGenerateCommand } from "./commands/generate.js";
import { registerServeCommand } from "./commands/serve.js";
import { registerAssetCommand } from "./commands/asset.js";
import { registerPluginCommand } from "./commands/plugin.js";

const VERSION = "0.1.0";

const program = new Command();

program
  .name("godot-forge")
  .description("GodotForge CLI — AI-powered game creation platform for Godot 4.x")
  .version(VERSION);

registerInitCommand(program);
registerGenerateCommand(program);
registerServeCommand(program);
registerAssetCommand(program);
registerPluginCommand(program);

program.parse(process.argv);
