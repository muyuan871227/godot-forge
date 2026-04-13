"use client";

import { useState } from "react";
import FileTree from "@/components/editor/FileTree";
import GamePreview from "@/components/preview/GamePreview";
import {
  Play,
  Square,
  RotateCcw,
  Maximize2,
  FileCode2,
  FolderTree,
  Monitor,
} from "lucide-react";

export default function ProjectOverviewPage() {
  const [isRunning, setIsRunning] = useState(false);

  return (
    <div className="flex h-full">
      {/* File Tree Panel */}
      <div className="w-72 border-r border-godot-dark-border bg-godot-dark-surface flex flex-col shrink-0">
        <div className="p-4 border-b border-godot-dark-border flex items-center justify-between">
          <h3 className="text-sm font-semibold text-white flex items-center gap-2">
            <FolderTree className="w-4 h-4 text-godot-accent" />
            File Explorer
          </h3>
        </div>
        <div className="flex-1 overflow-auto scrollbar-thin p-2">
          <FileTree />
        </div>
      </div>

      {/* Preview Panel */}
      <div className="flex-1 flex flex-col">
        {/* Toolbar */}
        <div className="px-4 py-3 border-b border-godot-dark-border bg-godot-dark-surface flex items-center justify-between">
          <div className="flex items-center gap-2">
            <button
              onClick={() => setIsRunning(!isRunning)}
              className={`flex items-center gap-2 px-4 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                isRunning
                  ? "bg-godot-error/20 text-godot-error hover:bg-godot-error/30"
                  : "bg-godot-success/20 text-godot-success hover:bg-godot-success/30"
              }`}
            >
              {isRunning ? (
                <>
                  <Square className="w-4 h-4" /> Stop
                </>
              ) : (
                <>
                  <Play className="w-4 h-4" /> Run
                </>
              )}
            </button>
            <button className="p-2 text-gray-400 hover:text-white hover:bg-godot-dark-card rounded-lg transition-colors">
              <RotateCcw className="w-4 h-4" />
            </button>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-xs text-gray-500 flex items-center gap-1">
              <Monitor className="w-3.5 h-3.5" />
              1920 x 1080
            </span>
            <button className="p-2 text-gray-400 hover:text-white hover:bg-godot-dark-card rounded-lg transition-colors">
              <Maximize2 className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Preview Area */}
        <div className="flex-1 p-6 flex items-center justify-center">
          {isRunning ? (
            <GamePreview />
          ) : (
            <div className="text-center">
              <div className="w-24 h-24 mx-auto mb-6 bg-godot-dark-card rounded-2xl flex items-center justify-center">
                <FileCode2 className="w-12 h-12 text-gray-600" />
              </div>
              <h3 className="text-xl font-semibold text-gray-300 mb-2">
                Project Overview
              </h3>
              <p className="text-gray-500 max-w-md">
                Click Run to preview your game, or use the Chat tab to generate
                content with AI assistance.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
