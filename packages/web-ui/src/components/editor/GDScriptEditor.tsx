"use client";

import { useRef, useCallback } from "react";
import Editor, { OnMount, BeforeMount } from "@monaco-editor/react";

interface GDScriptEditorProps {
  value: string;
  onChange?: (value: string | undefined) => void;
  path?: string;
  readOnly?: boolean;
}

// GDScript language definition for Monaco
const gdscriptLanguage = {
  defaultToken: "",
  tokenPostfix: ".gd",

  keywords: [
    "if", "elif", "else", "for", "while", "match", "break", "continue",
    "pass", "return", "class", "class_name", "extends", "is", "as", "self",
    "signal", "func", "static", "const", "enum", "var", "onready", "export",
    "setget", "tool", "yield", "assert", "breakpoint", "remote", "sync",
    "master", "puppet", "slave", "remotesync", "mastersync", "puppetsync",
    "await", "in", "and", "or", "not", "true", "false", "null", "void",
    "super", "get", "set",
  ],

  typeKeywords: [
    "int", "float", "bool", "String", "StringName", "NodePath",
    "Vector2", "Vector2i", "Vector3", "Vector3i", "Vector4", "Vector4i",
    "Rect2", "Rect2i", "Transform2D", "Transform3D", "Basis",
    "Quaternion", "AABB", "Plane", "Color",
    "Array", "Dictionary", "PackedByteArray", "PackedInt32Array",
    "PackedFloat32Array", "PackedStringArray", "PackedVector2Array",
    "PackedVector3Array", "PackedColorArray",
    "Object", "Node", "Node2D", "Node3D", "Control", "Resource",
    "CharacterBody2D", "CharacterBody3D", "RigidBody2D", "RigidBody3D",
    "StaticBody2D", "StaticBody3D", "Area2D", "Area3D",
    "Sprite2D", "Sprite3D", "AnimatedSprite2D",
    "Camera2D", "Camera3D", "Light2D",
    "CollisionShape2D", "CollisionShape3D",
    "Timer", "AudioStreamPlayer", "AnimationPlayer",
    "TileMap", "TileSet", "PackedScene",
  ],

  builtins: [
    "Input", "Engine", "OS", "ProjectSettings", "ResourceLoader",
    "ResourceSaver", "Time", "Performance", "Geometry2D", "Geometry3D",
    "print", "prints", "printt", "push_error", "push_warning",
    "move_toward", "lerp", "clamp", "abs", "sign", "min", "max",
    "floor", "ceil", "round", "sqrt", "pow", "sin", "cos", "tan",
    "randf", "randi", "randf_range", "randi_range", "randomize",
    "str", "load", "preload", "instance",
    "get_tree", "get_node", "get_parent", "get_viewport",
    "queue_free", "add_child", "remove_child",
    "connect", "disconnect", "emit_signal",
    "move_and_slide", "is_on_floor", "is_on_wall", "is_on_ceiling",
    "get_gravity",
  ],

  operators: [
    "=", ">", "<", "!", "~", "?", ":",
    "==", "<=", ">=", "!=", "&&", "||",
    "++", "--", "+", "-", "*", "/", "%",
    "&", "|", "^", "<<", ">>",
    "+=", "-=", "*=", "/=", "%=",
    "&=", "|=", "^=", "<<=", ">>=",
    "->",
  ],

  symbols: /[=><!~?:&|+\-*\/\^%]+/,

  escapes: /\\(?:[abfnrtv\\"']|x[0-9A-Fa-f]{1,4}|u[0-9A-Fa-f]{4}|U[0-9A-Fa-f]{8})/,

  tokenizer: {
    root: [
      // Comments
      [/#.*$/, "comment"],

      // Annotations
      [/@\w+/, "annotation"],

      // Strings
      [/"([^"\\]|\\.)*$/, "string.invalid"],
      [/'([^'\\]|\\.)*$/, "string.invalid"],
      [/"/, "string", "@string_double"],
      [/'/, "string", "@string_single"],

      // Multi-line strings
      [/"""/, "string", "@string_triple_double"],
      [/'''/, "string", "@string_triple_single"],

      // Numbers
      [/0[xX][0-9a-fA-F]+/, "number.hex"],
      [/0[bB][01]+/, "number.binary"],
      [/\d*\.\d+([eE][\-+]?\d+)?/, "number.float"],
      [/\d+/, "number"],

      // Identifiers and keywords
      [
        /[a-zA-Z_]\w*/,
        {
          cases: {
            "@keywords": "keyword",
            "@typeKeywords": "type",
            "@builtins": "predefined",
            "@default": "identifier",
          },
        },
      ],

      // Operators
      [/@symbols/, { cases: { "@operators": "operator", "@default": "" } }],

      // Delimiters
      [/[{}()\[\]]/, "delimiter.bracket"],
      [/[,;.]/, "delimiter"],
    ],

    string_double: [
      [/[^\\"]+/, "string"],
      [/@escapes/, "string.escape"],
      [/"/, "string", "@pop"],
    ],

    string_single: [
      [/[^\\']+/, "string"],
      [/@escapes/, "string.escape"],
      [/'/, "string", "@pop"],
    ],

    string_triple_double: [
      [/[^\\"]+/, "string"],
      [/@escapes/, "string.escape"],
      [/"""/, "string", "@pop"],
      [/"/, "string"],
    ],

    string_triple_single: [
      [/[^\\']+/, "string"],
      [/@escapes/, "string.escape"],
      [/'''/, "string", "@pop"],
      [/'/, "string"],
    ],
  },
};

const gdscriptTheme = {
  base: "vs-dark" as const,
  inherit: true,
  rules: [
    { token: "comment", foreground: "6A737D", fontStyle: "italic" },
    { token: "keyword", foreground: "C792EA" },
    { token: "type", foreground: "82AAFF" },
    { token: "predefined", foreground: "FFCB6B" },
    { token: "string", foreground: "A5D6A7" },
    { token: "string.escape", foreground: "89DDFF" },
    { token: "number", foreground: "F78C6C" },
    { token: "number.hex", foreground: "F78C6C" },
    { token: "number.float", foreground: "F78C6C" },
    { token: "number.binary", foreground: "F78C6C" },
    { token: "operator", foreground: "89DDFF" },
    { token: "annotation", foreground: "FFCB6B" },
    { token: "identifier", foreground: "EEFFFF" },
    { token: "delimiter", foreground: "89DDFF" },
    { token: "delimiter.bracket", foreground: "89DDFF" },
  ],
  colors: {
    "editor.background": "#0d1117",
    "editor.foreground": "#e6edf3",
    "editor.lineHighlightBackground": "#161b22",
    "editor.selectionBackground": "#264f78",
    "editorCursor.foreground": "#6c63ff",
    "editorLineNumber.foreground": "#484f58",
    "editorLineNumber.activeForeground": "#e6edf3",
    "editor.inactiveSelectionBackground": "#1d2d3e",
    "editorIndentGuide.background": "#21262d",
    "editorIndentGuide.activeBackground": "#30363d",
  },
};

export default function GDScriptEditor({
  value,
  onChange,
  path,
  readOnly = false,
}: GDScriptEditorProps) {
  const editorRef = useRef<any>(null);

  const handleBeforeMount: BeforeMount = useCallback((monaco) => {
    // Register GDScript language
    monaco.languages.register({ id: "gdscript" });
    monaco.languages.setMonarchTokensProvider("gdscript", gdscriptLanguage as any);

    // Register theme
    monaco.editor.defineTheme("godot-dark", gdscriptTheme);

    // Register completion provider
    monaco.languages.registerCompletionItemProvider("gdscript", {
      provideCompletionItems: (model: any, position: any) => {
        const word = model.getWordUntilPosition(position);
        const range = {
          startLineNumber: position.lineNumber,
          endLineNumber: position.lineNumber,
          startColumn: word.startColumn,
          endColumn: word.endColumn,
        };

        const suggestions = [
          ...gdscriptLanguage.keywords.map((kw) => ({
            label: kw,
            kind: monaco.languages.CompletionItemKind.Keyword,
            insertText: kw,
            range,
          })),
          ...gdscriptLanguage.typeKeywords.map((t) => ({
            label: t,
            kind: monaco.languages.CompletionItemKind.Class,
            insertText: t,
            range,
          })),
          ...gdscriptLanguage.builtins.map((b) => ({
            label: b,
            kind: monaco.languages.CompletionItemKind.Function,
            insertText: b,
            range,
          })),
          {
            label: "func",
            kind: monaco.languages.CompletionItemKind.Snippet,
            insertText: "func ${1:name}(${2:}) -> ${3:void}:\n\t${0:pass}",
            insertTextRules:
              monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
            documentation: "Function definition",
            range,
          },
          {
            label: "_ready",
            kind: monaco.languages.CompletionItemKind.Snippet,
            insertText: "func _ready() -> void:\n\t${0:pass}",
            insertTextRules:
              monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
            documentation: "Called when node enters the scene tree",
            range,
          },
          {
            label: "_process",
            kind: monaco.languages.CompletionItemKind.Snippet,
            insertText:
              "func _process(delta: float) -> void:\n\t${0:pass}",
            insertTextRules:
              monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
            documentation: "Called every frame",
            range,
          },
          {
            label: "_physics_process",
            kind: monaco.languages.CompletionItemKind.Snippet,
            insertText:
              "func _physics_process(delta: float) -> void:\n\t${0:pass}",
            insertTextRules:
              monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
            documentation: "Called every physics frame",
            range,
          },
        ];

        return { suggestions };
      },
    });
  }, []);

  const handleMount: OnMount = useCallback((editor) => {
    editorRef.current = editor;
    editor.focus();
  }, []);

  // Determine language from file path
  const getLanguage = (filePath?: string) => {
    if (!filePath) return "gdscript";
    if (filePath.endsWith(".gd")) return "gdscript";
    if (filePath.endsWith(".tres") || filePath.endsWith(".tscn")) return "ini";
    if (filePath.endsWith(".json")) return "json";
    if (filePath.endsWith(".cfg")) return "ini";
    if (filePath.endsWith(".shader") || filePath.endsWith(".gdshader"))
      return "gdscript";
    return "gdscript";
  };

  return (
    <Editor
      height="100%"
      language={getLanguage(path)}
      value={value}
      onChange={onChange}
      theme="godot-dark"
      beforeMount={handleBeforeMount}
      onMount={handleMount}
      options={{
        readOnly,
        fontSize: 14,
        fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
        fontLigatures: true,
        lineNumbers: "on",
        minimap: { enabled: true, scale: 2 },
        scrollBeyondLastLine: false,
        wordWrap: "off",
        tabSize: 4,
        insertSpaces: false,
        renderWhitespace: "selection",
        bracketPairColorization: { enabled: true },
        guides: {
          bracketPairs: true,
          indentation: true,
        },
        smoothScrolling: true,
        cursorBlinking: "smooth",
        cursorSmoothCaretAnimation: "on",
        padding: { top: 16 },
        suggest: {
          showKeywords: true,
          showSnippets: true,
        },
      }}
      loading={
        <div className="flex items-center justify-center h-full bg-[#0d1117] text-gray-500">
          Loading editor...
        </div>
      }
    />
  );
}
