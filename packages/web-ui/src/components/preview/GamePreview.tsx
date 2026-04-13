"use client";

import { useState } from "react";
import {
  Maximize2,
  Minimize2,
  RotateCcw,
  Volume2,
  VolumeX,
  Smartphone,
  Monitor,
  Tablet,
} from "lucide-react";

type Viewport = "desktop" | "tablet" | "mobile";

const viewportSizes: Record<Viewport, { width: number; height: number; label: string }> = {
  desktop: { width: 1920, height: 1080, label: "1920x1080" },
  tablet: { width: 1024, height: 768, label: "1024x768" },
  mobile: { width: 375, height: 667, label: "375x667" },
};

export default function GamePreview() {
  const [viewport, setViewport] = useState<Viewport>("desktop");
  const [muted, setMuted] = useState(false);
  const [fullscreen, setFullscreen] = useState(false);

  const size = viewportSizes[viewport];

  return (
    <div className="flex flex-col h-full w-full">
      {/* Preview Controls */}
      <div className="flex items-center justify-between px-4 py-2 bg-godot-dark-surface border-b border-godot-dark-border">
        <div className="flex items-center gap-2">
          {/* Viewport Presets */}
          <div className="flex items-center bg-godot-dark-bg rounded-lg p-0.5">
            <button
              onClick={() => setViewport("desktop")}
              className={`p-1.5 rounded transition-colors ${
                viewport === "desktop"
                  ? "bg-godot-dark-card text-white"
                  : "text-gray-500 hover:text-gray-300"
              }`}
              title="Desktop"
            >
              <Monitor className="w-4 h-4" />
            </button>
            <button
              onClick={() => setViewport("tablet")}
              className={`p-1.5 rounded transition-colors ${
                viewport === "tablet"
                  ? "bg-godot-dark-card text-white"
                  : "text-gray-500 hover:text-gray-300"
              }`}
              title="Tablet"
            >
              <Tablet className="w-4 h-4" />
            </button>
            <button
              onClick={() => setViewport("mobile")}
              className={`p-1.5 rounded transition-colors ${
                viewport === "mobile"
                  ? "bg-godot-dark-card text-white"
                  : "text-gray-500 hover:text-gray-300"
              }`}
              title="Mobile"
            >
              <Smartphone className="w-4 h-4" />
            </button>
          </div>
          <span className="text-xs text-gray-500">{size.label}</span>
        </div>

        <div className="flex items-center gap-1">
          <button
            onClick={() => setMuted(!muted)}
            className="p-2 text-gray-400 hover:text-white rounded transition-colors"
          >
            {muted ? (
              <VolumeX className="w-4 h-4" />
            ) : (
              <Volume2 className="w-4 h-4" />
            )}
          </button>
          <button className="p-2 text-gray-400 hover:text-white rounded transition-colors">
            <RotateCcw className="w-4 h-4" />
          </button>
          <button
            onClick={() => setFullscreen(!fullscreen)}
            className="p-2 text-gray-400 hover:text-white rounded transition-colors"
          >
            {fullscreen ? (
              <Minimize2 className="w-4 h-4" />
            ) : (
              <Maximize2 className="w-4 h-4" />
            )}
          </button>
        </div>
      </div>

      {/* Preview Canvas */}
      <div className="flex-1 flex items-center justify-center bg-black/50 p-4 overflow-auto">
        <div
          className="relative bg-godot-dark-bg border border-godot-dark-border rounded-lg overflow-hidden shadow-2xl"
          style={{
            width: "100%",
            maxWidth: viewport === "mobile" ? "375px" : viewport === "tablet" ? "768px" : "100%",
            aspectRatio: `${size.width} / ${size.height}`,
          }}
        >
          {/* Placeholder content - would be replaced with actual game iframe/canvas */}
          <div className="absolute inset-0 flex flex-col items-center justify-center text-gray-600">
            <div className="w-16 h-16 mb-4 border-2 border-gray-700 rounded-xl flex items-center justify-center">
              <Monitor className="w-8 h-8" />
            </div>
            <p className="text-sm font-medium">Game Preview</p>
            <p className="text-xs text-gray-700 mt-1">
              Running on Godot 4.4 Runtime
            </p>

            {/* Simulated game elements */}
            <div className="absolute bottom-8 left-1/2 -translate-x-1/2">
              <div className="w-8 h-12 bg-godot-accent/30 rounded-t-lg border-2 border-godot-accent/50" />
            </div>
            <div className="absolute bottom-0 left-0 right-0 h-8 bg-godot-success/20 border-t-2 border-godot-success/30" />

            {/* FPS Counter */}
            <div className="absolute top-3 right-3 bg-black/60 px-2 py-1 rounded text-xs font-mono text-godot-success">
              60 FPS
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
