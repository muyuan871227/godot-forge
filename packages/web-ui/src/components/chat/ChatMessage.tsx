"use client";

import { useState } from "react";
import {
  User,
  Sparkles,
  Copy,
  Check,
  FileCode2,
  Download,
  ChevronDown,
  ChevronRight,
} from "lucide-react";

interface FileBlock {
  name: string;
  content: string;
  language: string;
}

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  mode: string;
  timestamp: Date;
  files?: FileBlock[];
}

// Simple keyword-based syntax highlighting for GDScript
function highlightGDScript(code: string): string {
  const keywords = [
    "extends",
    "func",
    "var",
    "const",
    "if",
    "else",
    "elif",
    "for",
    "while",
    "return",
    "class",
    "class_name",
    "signal",
    "enum",
    "export",
    "onready",
    "static",
    "void",
    "pass",
    "break",
    "continue",
    "match",
    "and",
    "or",
    "not",
    "in",
    "is",
    "as",
    "self",
    "true",
    "false",
    "null",
    "await",
  ];
  const types = [
    "int",
    "float",
    "bool",
    "String",
    "Vector2",
    "Vector3",
    "Array",
    "Dictionary",
    "Node",
    "CharacterBody2D",
    "CharacterBody3D",
    "RigidBody2D",
    "Sprite2D",
    "Area2D",
    "CollisionShape2D",
    "Timer",
    "PackedScene",
    "Resource",
    "Object",
  ];
  const builtins = [
    "Input",
    "ProjectSettings",
    "Engine",
    "OS",
    "ResourceLoader",
    "print",
    "push_error",
    "push_warning",
    "move_toward",
    "clamp",
    "lerp",
    "abs",
    "sign",
    "min",
    "max",
    "randf",
    "randi",
    "get_gravity",
    "move_and_slide",
    "is_on_floor",
  ];

  let escaped = code
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");

  // Comments
  escaped = escaped.replace(
    /(#.*)$/gm,
    '<span class="text-gray-500 italic">$1</span>'
  );

  // Strings
  escaped = escaped.replace(
    /(&quot;[^&]*&quot;|"[^"]*")/g,
    '<span class="text-green-400">$1</span>'
  );

  // Numbers
  escaped = escaped.replace(
    /\b(\d+\.?\d*)\b/g,
    '<span class="text-orange-400">$1</span>'
  );

  // Types
  types.forEach((t) => {
    const regex = new RegExp(`\\b(${t})\\b`, "g");
    escaped = escaped.replace(regex, '<span class="text-cyan-400">$1</span>');
  });

  // Keywords
  keywords.forEach((kw) => {
    const regex = new RegExp(`\\b(${kw})\\b`, "g");
    escaped = escaped.replace(regex, '<span class="text-purple-400">$1</span>');
  });

  // Built-in functions/objects
  builtins.forEach((b) => {
    const regex = new RegExp(`\\b(${b})\\b`, "g");
    escaped = escaped.replace(regex, '<span class="text-yellow-400">$1</span>');
  });

  // Function definitions
  escaped = escaped.replace(
    /\b(func)\b\s+(\w+)/g,
    '<span class="text-purple-400">$1</span> <span class="text-blue-400">$2</span>'
  );

  return escaped;
}

function renderMarkdown(text: string): string {
  let html = text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");

  // Bold
  html = html.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  // Italic
  html = html.replace(/\*(.+?)\*/g, "<em>$1</em>");
  // Inline code
  html = html.replace(
    /`([^`]+)`/g,
    '<code class="bg-godot-dark-bg px-1.5 py-0.5 rounded text-sm text-pink-400">$1</code>'
  );
  // Lists
  html = html.replace(
    /^- (.+)$/gm,
    '<li class="ml-4 list-disc text-gray-300">$1</li>'
  );
  // Paragraphs
  html = html
    .split("\n\n")
    .map((p) => `<p class="mb-2">${p}</p>`)
    .join("");
  // Line breaks within paragraphs
  html = html.replace(/\n/g, "<br/>");

  return html;
}

function CodeBlock({ file }: { file: FileBlock }) {
  const [copied, setCopied] = useState(false);
  const [expanded, setExpanded] = useState(true);

  const handleCopy = () => {
    navigator.clipboard.writeText(file.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const highlighted = highlightGDScript(file.content);

  return (
    <div className="mt-3 border border-godot-dark-border rounded-xl overflow-hidden">
      {/* File Header */}
      <div className="flex items-center justify-between px-4 py-2 bg-godot-dark-surface border-b border-godot-dark-border">
        <button
          onClick={() => setExpanded(!expanded)}
          className="flex items-center gap-2 text-sm text-gray-300 hover:text-white transition-colors"
        >
          {expanded ? (
            <ChevronDown className="w-4 h-4" />
          ) : (
            <ChevronRight className="w-4 h-4" />
          )}
          <FileCode2 className="w-4 h-4 text-godot-accent" />
          <span className="font-mono">{file.name}</span>
          <span className="text-xs text-gray-600 ml-2">{file.language}</span>
        </button>
        <div className="flex items-center gap-1">
          <button
            onClick={handleCopy}
            className="p-1.5 text-gray-500 hover:text-white rounded transition-colors"
            title="Copy code"
          >
            {copied ? (
              <Check className="w-4 h-4 text-godot-success" />
            ) : (
              <Copy className="w-4 h-4" />
            )}
          </button>
          <button
            className="px-3 py-1 text-xs font-medium text-godot-accent hover:bg-godot-accent/10 rounded-lg transition-colors"
            title="Apply to project"
          >
            Apply
          </button>
        </div>
      </div>

      {/* Code Content */}
      {expanded && (
        <div className="overflow-x-auto">
          <pre className="p-4 text-sm font-mono leading-relaxed bg-[#0d1117]">
            <code dangerouslySetInnerHTML={{ __html: highlighted }} />
          </pre>
        </div>
      )}
    </div>
  );
}

export default function ChatMessage({ message }: { message: Message }) {
  const isUser = message.role === "user";

  return (
    <div className={`flex gap-4 max-w-4xl mx-auto ${isUser ? "justify-end" : ""}`}>
      {/* Avatar */}
      {!isUser && (
        <div className="w-8 h-8 rounded-lg bg-godot-accent/20 flex items-center justify-center shrink-0 mt-1">
          <Sparkles className="w-4 h-4 text-godot-accent" />
        </div>
      )}

      {/* Content */}
      <div
        className={`flex-1 max-w-[85%] ${isUser ? "flex flex-col items-end" : ""}`}
      >
        <div
          className={`rounded-2xl px-5 py-3 ${
            isUser
              ? "bg-godot-accent text-white rounded-br-md"
              : "bg-godot-dark-card text-gray-200 rounded-bl-md"
          }`}
        >
          {isUser ? (
            <p className="text-sm whitespace-pre-wrap">{message.content}</p>
          ) : (
            <div
              className="text-sm prose-sm prose-invert"
              dangerouslySetInnerHTML={{ __html: renderMarkdown(message.content) }}
            />
          )}
        </div>

        {/* File Blocks */}
        {message.files?.map((file, i) => (
          <CodeBlock key={i} file={file} />
        ))}

        {/* Timestamp */}
        <p className="text-xs text-gray-600 mt-1.5 px-1">
          {message.timestamp.toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
          })}
        </p>
      </div>

      {/* User Avatar */}
      {isUser && (
        <div className="w-8 h-8 rounded-lg bg-godot-dark-card flex items-center justify-center shrink-0 mt-1">
          <User className="w-4 h-4 text-gray-400" />
        </div>
      )}
    </div>
  );
}
