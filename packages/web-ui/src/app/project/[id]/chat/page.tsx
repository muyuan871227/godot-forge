"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import ChatInterface from "@/components/chat/ChatInterface";
import GamePreview from "@/components/preview/GamePreview";
import { useChatStore } from "@/lib/stores/chat";
import { GripVertical } from "lucide-react";

const MIN_PANEL_PCT = 25; // minimum panel width in percent
const DEFAULT_SPLIT = 50; // default 50/50 split

export default function ChatPage() {
  const { previewUrl, previewLoading } = useChatStore();
  const [splitPct, setSplitPct] = useState(DEFAULT_SPLIT);
  const containerRef = useRef<HTMLDivElement>(null);
  const dragging = useRef(false);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    dragging.current = true;
  }, []);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!dragging.current || !containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      let pct = ((e.clientX - rect.left) / rect.width) * 100;
      pct = Math.max(MIN_PANEL_PCT, Math.min(100 - MIN_PANEL_PCT, pct));
      setSplitPct(pct);
    };

    const handleMouseUp = () => {
      dragging.current = false;
    };

    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);
    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
    };
  }, []);

  return (
    <div ref={containerRef} className="flex h-full overflow-hidden">
      {/* Left panel: Chat */}
      <div
        className="h-full overflow-hidden"
        style={{ width: `${splitPct}%` }}
      >
        <ChatInterface />
      </div>

      {/* Draggable divider */}
      <div
        onMouseDown={handleMouseDown}
        className="w-2 flex-shrink-0 cursor-col-resize bg-godot-dark-border hover:bg-godot-accent/40 transition-colors relative group"
      >
        <div className="absolute inset-y-0 left-1/2 -translate-x-1/2 flex items-center">
          <GripVertical className="w-3 h-3 text-gray-600 group-hover:text-godot-accent transition-colors" />
        </div>
      </div>

      {/* Right panel: Game Preview */}
      <div
        className="h-full overflow-hidden"
        style={{ width: `${100 - splitPct}%` }}
      >
        <GamePreview src={previewUrl ?? undefined} loading={previewLoading} />
      </div>
    </div>
  );
}
