"use client";

import { useState, useRef, useEffect } from "react";
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
  RotateCcw,
  Settings2,
} from "lucide-react";

export type ChatMode = "code" | "2d" | "3d" | "audio";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  mode: ChatMode;
  timestamp: Date;
  files?: { name: string; content: string; language: string }[];
}

const modes: { value: ChatMode; label: string; icon: React.ElementType; description: string }[] = [
  { value: "code", label: "Code", icon: Code2, description: "Generate GDScript code" },
  { value: "2d", label: "2D Art", icon: Image, description: "Generate sprites & textures" },
  { value: "3d", label: "3D Model", icon: Box, description: "Generate 3D models" },
  { value: "audio", label: "Audio", icon: Music, description: "Generate sound & music" },
];

const welcomeMessage: Message = {
  id: "welcome",
  role: "assistant",
  content: `Welcome to GodotForge AI Assistant! I can help you with:

- **Code Generation**: Write GDScript for player controllers, enemy AI, UI systems, and more
- **2D Assets**: Generate sprites, tilesets, and sprite sheets
- **3D Models**: Create 3D models and environments
- **Audio**: Generate sound effects and background music

Select a mode above and describe what you need. I'll generate the code or assets and you can apply them directly to your project.`,
  mode: "code",
  timestamp: new Date(),
};

export default function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([welcomeMessage]);
  const [input, setInput] = useState("");
  const [mode, setMode] = useState<ChatMode>("code");
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content: input,
      mode,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);

    // Simulate AI response
    setTimeout(() => {
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: getSimulatedResponse(input, mode),
        mode,
        timestamp: new Date(),
        files:
          mode === "code"
            ? [
                {
                  name: "player_controller.gd",
                  content: `extends CharacterBody2D

const SPEED = 300.0
const JUMP_VELOCITY = -400.0

func _physics_process(delta: float) -> void:
    var direction = Input.get_axis("move_left", "move_right")
    if direction:
        velocity.x = direction * SPEED
    else:
        velocity.x = move_toward(velocity.x, 0, SPEED)

    if is_on_floor() and Input.is_action_just_pressed("jump"):
        velocity.y = JUMP_VELOCITY

    if not is_on_floor():
        velocity.y += get_gravity().y * delta

    move_and_slide()`,
                  language: "gdscript",
                },
              ]
            : undefined,
      };
      setMessages((prev) => [...prev, assistantMessage]);
      setIsLoading(false);
    }, 2000);
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
        {messages.map((message) => (
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
              value={input}
              onChange={(e) => setInput(e.target.value)}
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
            disabled={!input.trim() || isLoading}
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

function getSimulatedResponse(input: string, mode: ChatMode): string {
  if (mode === "code") {
    return `Here's a GDScript implementation based on your request:

I've created a \`player_controller.gd\` script that includes:

- **Movement**: Horizontal movement with configurable speed
- **Jumping**: Physics-based jump with gravity
- **Input mapping**: Uses Godot's input action system

You can apply this script to a \`CharacterBody2D\` node. Make sure to set up the input actions \`move_left\`, \`move_right\`, and \`jump\` in your project settings.`;
  }
  if (mode === "2d") {
    return `I've generated a sprite based on your description. The asset has been added to your project's \`res://assets/sprites/\` directory.

**Details:**
- Resolution: 32x32 pixels
- Format: PNG with transparency
- Style: Pixel art

You can drag it into your scene or assign it to a \`Sprite2D\` node.`;
  }
  if (mode === "3d") {
    return `I've generated a 3D model based on your description. The model has been saved to \`res://assets/models/\`.

**Details:**
- Format: GLTF 2.0
- Polygons: ~1,200 (optimized for real-time)
- Materials: PBR-ready with albedo and normal maps

Import it into your Godot scene as a \`MeshInstance3D\`.`;
  }
  return `I've generated an audio clip based on your description. The file has been saved to \`res://assets/audio/\`.

**Details:**
- Format: OGG Vorbis
- Duration: 3.2 seconds
- Sample Rate: 44.1 kHz

Add it to an \`AudioStreamPlayer\` node to use it in your game.`;
}
