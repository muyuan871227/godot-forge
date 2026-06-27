"use client";

import { useState, useRef, useCallback } from "react";
import {
  Maximize2,
  Minimize2,
  RotateCcw,
  Volume2,
  VolumeX,
  Smartphone,
  Monitor,
  Tablet,
  Loader2,
} from "lucide-react";

type Viewport = "desktop" | "tablet" | "mobile";

const viewportSizes: Record<Viewport, { width: number; height: number; label: string }> = {
  desktop: { width: 1920, height: 1080, label: "1920x1080" },
  tablet: { width: 1024, height: 768, label: "1024x768" },
  mobile: { width: 375, height: 667, label: "375x667" },
};

interface GamePreviewProps {
  src?: string | null;
  loading?: boolean;
}

export default function GamePreview({ src, loading }: GamePreviewProps) {
  const [viewport, setViewport] = useState<Viewport>("desktop");
  const [muted, setMuted] = useState(false);
  const [fullscreen, setFullscreen] = useState(false);
  const [iframeLoading, setIframeLoading] = useState(false);
  const iframeRef = useRef<HTMLIFrameElement>(null);

  const size = viewportSizes[viewport];

  const handleReload = useCallback(() => {
    if (iframeRef.current && src) {
      setIframeLoading(true);
      iframeRef.current.src = src;
    }
  }, [src]);

  const handleIframeLoad = useCallback(() => {
    setIframeLoading(false);
  }, []);

  const showLoading = loading || iframeLoading;

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
          <button
            onClick={handleReload}
            disabled={!src}
            className="p-2 text-gray-400 hover:text-white rounded transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
            title="Reload preview"
          >
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
      <div className="flex-1 flex items-center justify-center bg-black/50 p-4 overflow-auto relative">
        {/* Loading overlay */}
        {showLoading && (
          <div className="absolute inset-0 z-10 flex flex-col items-center justify-center bg-black/70">
            <Loader2 className="w-10 h-10 text-godot-accent animate-spin mb-3" />
            <p className="text-sm text-gray-300">
              {loading ? "Generating preview..." : "Loading preview..."}
            </p>
          </div>
        )}

        {src ? (
          /* Live iframe preview */
          <div
            className="relative bg-godot-dark-bg border border-godot-dark-border rounded-lg overflow-hidden shadow-2xl"
            style={{
              width: "100%",
              maxWidth: viewport === "mobile" ? "375px" : viewport === "tablet" ? "768px" : "100%",
              aspectRatio: `${size.width} / ${size.height}`,
            }}
          >
            <iframe
              ref={iframeRef}
              src={src}
              onLoad={handleIframeLoad}
              className="absolute inset-0 w-full h-full border-0"
              title="Game Preview"
              sandbox="allow-scripts allow-same-origin allow-popups"
              allow="autoplay; fullscreen"
            />
          </div>
        ) : (
          /* Placeholder when no preview URL */
          <div
            className="relative bg-godot-dark-bg border border-godot-dark-border rounded-lg overflow-hidden shadow-2xl"
            style={{
              width: "100%",
              maxWidth: viewport === "mobile" ? "375px" : viewport === "tablet" ? "768px" : "100%",
              aspectRatio: `${size.width} / ${size.height}`,
            }}
          >
            <div className="absolute inset-0 flex flex-col items-center justify-center text-gray-600">
              <div className="w-16 h-16 mb-4 border-2 border-gray-700 rounded-xl flex items-center justify-center">
                <Monitor className="w-8 h-8" />
              </div>
              <p className="text-sm font-medium">Game Preview</p>
              <p className="text-xs text-gray-700 mt-1">
                Send a prompt to generate and preview your game
              </p>

              {/* Simulated game elements */}
              <div className="absolute bottom-8 left-1/2 -translate-x-1/2">
                <div className="w-8 h-12 bg-godot-accent/30 rounded-t-lg border-2 border-godot-accent/50" />
              </div>
              <div className="absolute bottom-0 left-0 right-0 h-8 bg-godot-success/20 border-t-2 border-godot-success/30" />

              {/* FPS Counter */}
              <div className="absolute top-3 right-3 bg-black/60 px-2 py-1 rounded text-xs font-mono text-godot-success">
                -- FPS
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
