"use client";

import { useState } from "react";
import {
  ChevronRight,
  ChevronDown,
  File,
  FileCode2,
  FileImage,
  FileAudio,
  Folder,
  FolderOpen,
  FileJson,
  Cog,
} from "lucide-react";

interface FileNode {
  name: string;
  type: "file" | "folder";
  path: string;
  children?: FileNode[];
}

const projectTree: FileNode[] = [
  {
    name: "res://",
    type: "folder",
    path: "res://",
    children: [
      {
        name: "scenes",
        type: "folder",
        path: "scenes",
        children: [
          { name: "main.tscn", type: "file", path: "scenes/main.tscn" },
          { name: "player.tscn", type: "file", path: "scenes/player.tscn" },
          { name: "enemy.tscn", type: "file", path: "scenes/enemy.tscn" },
          { name: "ui.tscn", type: "file", path: "scenes/ui.tscn" },
          {
            name: "levels",
            type: "folder",
            path: "scenes/levels",
            children: [
              {
                name: "level_01.tscn",
                type: "file",
                path: "scenes/levels/level_01.tscn",
              },
              {
                name: "level_02.tscn",
                type: "file",
                path: "scenes/levels/level_02.tscn",
              },
            ],
          },
        ],
      },
      {
        name: "scripts",
        type: "folder",
        path: "scripts",
        children: [
          { name: "player.gd", type: "file", path: "scripts/player.gd" },
          { name: "enemy.gd", type: "file", path: "scripts/enemy.gd" },
          { name: "game_manager.gd", type: "file", path: "scripts/game_manager.gd" },
          { name: "ui_controller.gd", type: "file", path: "scripts/ui_controller.gd" },
          {
            name: "autoload",
            type: "folder",
            path: "scripts/autoload",
            children: [
              {
                name: "globals.gd",
                type: "file",
                path: "scripts/autoload/globals.gd",
              },
              {
                name: "save_manager.gd",
                type: "file",
                path: "scripts/autoload/save_manager.gd",
              },
            ],
          },
        ],
      },
      {
        name: "assets",
        type: "folder",
        path: "assets",
        children: [
          {
            name: "sprites",
            type: "folder",
            path: "assets/sprites",
            children: [
              {
                name: "player.png",
                type: "file",
                path: "assets/sprites/player.png",
              },
              {
                name: "tileset.png",
                type: "file",
                path: "assets/sprites/tileset.png",
              },
            ],
          },
          {
            name: "audio",
            type: "folder",
            path: "assets/audio",
            children: [
              {
                name: "jump.ogg",
                type: "file",
                path: "assets/audio/jump.ogg",
              },
              {
                name: "bgm.ogg",
                type: "file",
                path: "assets/audio/bgm.ogg",
              },
            ],
          },
        ],
      },
      { name: "project.godot", type: "file", path: "project.godot" },
      { name: "export_presets.cfg", type: "file", path: "export_presets.cfg" },
    ],
  },
];

function getFileIcon(name: string) {
  const ext = name.split(".").pop()?.toLowerCase();
  switch (ext) {
    case "gd":
      return <FileCode2 className="w-4 h-4 text-purple-400" />;
    case "tscn":
    case "tres":
      return <FileCode2 className="w-4 h-4 text-cyan-400" />;
    case "png":
    case "jpg":
    case "svg":
    case "webp":
      return <FileImage className="w-4 h-4 text-green-400" />;
    case "ogg":
    case "wav":
    case "mp3":
      return <FileAudio className="w-4 h-4 text-yellow-400" />;
    case "json":
      return <FileJson className="w-4 h-4 text-orange-400" />;
    case "godot":
    case "cfg":
      return <Cog className="w-4 h-4 text-gray-400" />;
    default:
      return <File className="w-4 h-4 text-gray-400" />;
  }
}

interface TreeNodeProps {
  node: FileNode;
  depth: number;
  onFileSelect?: (path: string) => void;
  selectedPath?: string;
}

function TreeNode({ node, depth, onFileSelect, selectedPath }: TreeNodeProps) {
  const [expanded, setExpanded] = useState(depth < 2);

  if (node.type === "folder") {
    return (
      <div>
        <button
          onClick={() => setExpanded(!expanded)}
          className="flex items-center gap-1.5 w-full px-2 py-1 text-sm text-gray-300 hover:bg-godot-dark-card rounded transition-colors"
          style={{ paddingLeft: `${depth * 12 + 8}px` }}
        >
          {expanded ? (
            <ChevronDown className="w-3.5 h-3.5 text-gray-500 shrink-0" />
          ) : (
            <ChevronRight className="w-3.5 h-3.5 text-gray-500 shrink-0" />
          )}
          {expanded ? (
            <FolderOpen className="w-4 h-4 text-godot-accent shrink-0" />
          ) : (
            <Folder className="w-4 h-4 text-godot-accent shrink-0" />
          )}
          <span className="truncate">{node.name}</span>
        </button>
        {expanded && node.children && (
          <div>
            {node.children.map((child) => (
              <TreeNode
                key={child.path}
                node={child}
                depth={depth + 1}
                onFileSelect={onFileSelect}
                selectedPath={selectedPath}
              />
            ))}
          </div>
        )}
      </div>
    );
  }

  const isSelected = selectedPath === node.path;

  return (
    <button
      onClick={() => onFileSelect?.(node.path)}
      className={`flex items-center gap-1.5 w-full px-2 py-1 text-sm rounded transition-colors ${
        isSelected
          ? "bg-godot-accent/20 text-godot-accent"
          : "text-gray-400 hover:bg-godot-dark-card hover:text-gray-200"
      }`}
      style={{ paddingLeft: `${depth * 12 + 24}px` }}
    >
      {getFileIcon(node.name)}
      <span className="truncate">{node.name}</span>
    </button>
  );
}

interface FileTreeProps {
  onFileSelect?: (path: string) => void;
  selectedPath?: string;
}

export default function FileTree({ onFileSelect, selectedPath }: FileTreeProps) {
  return (
    <div className="text-sm">
      {projectTree.map((node) => (
        <TreeNode
          key={node.path}
          node={node}
          depth={0}
          onFileSelect={onFileSelect}
          selectedPath={selectedPath}
        />
      ))}
    </div>
  );
}
