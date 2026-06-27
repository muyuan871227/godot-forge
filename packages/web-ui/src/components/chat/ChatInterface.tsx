"use client";

import { useRef, useEffect } from "react";
import { useParams } from "next/navigation";
import ChatMessage from "./ChatMessage";
import {
  Send,
  Code2,
  Image,
  Box,
  Music,
  Paperclip,
  Sparkles,
  Loader2,
  Settings2,
} from "lucide-react";
import { useChatStore, type ChatMode } from "@/lib/stores/chat";

const modes: { value: ChatMode; label: string; icon: React.ElementType; description: string }[] = [
  { value: "code", label: "Code", icon: Code2, description: "Generate GDScript code" },
  { value: "2d", label: "2D Art", icon: Image, description: "Generate sprites & textures" },
  { value: "3d", label: "3D Model", icon: Box, description: "Generate 3D models" },
  { value: "audio", label: "Audio", icon: Music, description: "Generate sound & music" },
];

const welcomeMessage = {
  id: "welcome",
  role: "assistant" as const,
  content: `Welcome to GodotForge AI Assistant! I can help you with:

- **Code Generation**: Write GDScript for player controllers, enemy AI, UI systems, and more
- **2D Assets**: Generate sprites, tilesets, and sprite sheets
- **3D Models**: Create 3D models and environments
- **Audio**: Generate sound effects and background music

Select a mode above and describe what you need. I'll generate the code or assets and you can apply them directly to your project.`,
  mode: "code" as ChatMode,
  timestamp: new Date(),
};

export default function ChatInterface() {
  const params = useParams();
  const projectId = (params?.id as string) || "default";

  const {
    messages,
    isLoading,
    mode,
    inputValue,
    setMode,
    setInputValue,
    sendMessage,
  } = useChatStore();

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Add welcome message if empty
  const displayMessages =
    messages.length === 0 ? [welcomeMessage, ...messages] : messages;

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async () => {
    if (!inputValue.trim() || isLoading) return;
    const content = inputValue;
    setInputValue("");
    await sendMessage(projectId, content, mode);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex flex-col h-full bg-godot-dark-bg">
      {/* Mode Selector */}
      <div className="px-4 py-3 border-b border-godot-dark-border bg-godot-dark-surface">
        <div className="flex items-center gap-2">
          {modes.map((m) => {
            const Icon = m.icon;
            return (
              <button
                key={m.value}
                onClick={() => setMode(m.value)}
                title={m.description}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  mode === m.value
                    ? "bg-godot-accent/20 text-godot-accent border border-godot-accent/30"
                    : "text-gray-400 hover:text-gray-200 hover:bg-godot-dark-card border border-transparent"
                }`}
              >
                <Icon className="w-4 h-4" />
                {m.label}
              </button>
            );
          })}
          <div className="flex-1" />
          <button className="p-2 text-gray-500 hover:text-gray-300 transition-colors">
            <Settings2 className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-auto scrollbar-thin px-4 py-6 space-y-6">
        {displayMessages.map((message) => (
          <ChatMessage key={message.id} message={message} />
        ))}
        {isLoading && (
          <div className="flex items-center gap-3 px-4 py-3">
            <div className="w-8 h-8 rounded-lg bg-godot-accent/20 flex items-center justify-center">
              <Sparkles className="w-4 h-4 text-godot-accent" />
            </div>
            <div className="flex items-center gap-2 text-sm text-gray-400">
              <Loader2 className="w-4 h-4 animate-spin" />
              Generating response...
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="border-t border-godot-dark-border bg-godot-dark-surface p-4">
        <div className="flex items-end gap-3 max-w-4xl mx-auto">
          <button className="p-2.5 text-gray-500 hover:text-gray-300 hover:bg-godot-dark-card rounded-lg transition-colors shrink-0">
            <Paperclip className="w-5 h-5" />
          </button>
          <div className="flex-1 relative">
            <textarea
              ref={inputRef}
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={
                mode === "code"
                  ? "Describe the code you need..."
                  : mode === "2d"
                    ? "Describe the sprite or texture..."
                    : mode === "3d"
                      ? "Describe the 3D model..."
                      : "Describe the sound or music..."
              }
              rows={1}
              className="input-field text-sm pr-12 resize-none min-h-[44px] max-h-32"
              style={{
                height: "auto",
                minHeight: "44px",
              }}
              onInput={(e) => {
                const target = e.target as HTMLTextAreaElement;
                target.style.height = "auto";
                target.style.height = Math.min(target.scrollHeight, 128) + "px";
              }}
            />
          </div>
          <button
            onClick={handleSend}
            disabled={!inputValue.trim() || isLoading}
            className="p-2.5 bg-godot-accent hover:bg-godot-accent-hover text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed shrink-0"
          >
            <Send className="w-5 h-5" />
          </button>
        </div>
        <p className="text-xs text-gray-600 text-center mt-2">
          Press Enter to send, Shift+Enter for new line
        </p>
      </div>
    </div>
  );
}
