"use client";

import { useState } from "react";
import GDScriptEditor from "@/components/editor/GDScriptEditor";
import FileTree from "@/components/editor/FileTree";
import { FolderTree, Save, Play, Settings2, X } from "lucide-react";

interface OpenTab {
  path: string;
  name: string;
  content: string;
}

const defaultContent = `extends CharacterBody2D

const SPEED = 300.0
const JUMP_VELOCITY = -400.0

func _physics_process(delta: float) -> void:
\tvar velocity = Vector2.ZERO

\t# Handle horizontal movement
\tvar direction = Input.get_axis("move_left", "move_right")
\tif direction:
\t\tvelocity.x = direction * SPEED
\telse:
\t\tvelocity.x = move_toward(velocity.x, 0, SPEED)

\t# Handle jump
\tif is_on_floor() and Input.is_action_just_pressed("jump"):
\t\tvelocity.y = JUMP_VELOCITY

\t# Apply gravity
\tif not is_on_floor():
\t\tvelocity.y += ProjectSettings.get_setting("physics/2d/default_gravity") * delta

\tself.velocity = velocity
\tmove_and_slide()
`;

export default function EditorPage() {
  const [openTabs, setOpenTabs] = useState<OpenTab[]>([
    {
      path: "scripts/player.gd",
      name: "player.gd",
      content: defaultContent,
    },
  ]);
  const [activeTab, setActiveTab] = useState(0);

  const handleFileSelect = (path: string) => {
    const existing = openTabs.findIndex((t) => t.path === path);
    if (existing >= 0) {
      setActiveTab(existing);
    } else {
      const name = path.split("/").pop() || path;
      const newTab: OpenTab = {
        path,
        name,
        content: `# ${path}\n# File content loaded from project\n`,
      };
      setOpenTabs([...openTabs, newTab]);
      setActiveTab(openTabs.length);
    }
  };

  const handleCloseTab = (index: number, e: React.MouseEvent) => {
    e.stopPropagation();
    const next = openTabs.filter((_, i) => i !== index);
    setOpenTabs(next);
    if (activeTab >= next.length) {
      setActiveTab(Math.max(0, next.length - 1));
    }
  };

  return (
    <div className="flex h-full">
      {/* File Sidebar */}
      <div className="w-64 border-r border-godot-dark-border bg-godot-dark-surface flex flex-col shrink-0">
        <div className="p-3 border-b border-godot-dark-border flex items-center gap-2">
          <FolderTree className="w-4 h-4 text-godot-accent" />
          <span className="text-sm font-semibold text-white">Explorer</span>
        </div>
        <div className="flex-1 overflow-auto scrollbar-thin p-1">
          <FileTree onFileSelect={handleFileSelect} />
        </div>
      </div>

      {/* Editor Area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Tab Bar */}
        <div className="flex items-center bg-godot-dark-surface border-b border-godot-dark-border">
          <div className="flex-1 flex items-center overflow-x-auto scrollbar-thin">
            {openTabs.map((tab, index) => (
              <button
                key={tab.path}
                onClick={() => setActiveTab(index)}
                className={`flex items-center gap-2 px-4 py-2.5 text-sm border-r border-godot-dark-border shrink-0 transition-colors ${
                  index === activeTab
                    ? "bg-godot-dark-bg text-white border-b-2 border-b-godot-accent"
                    : "text-gray-400 hover:text-gray-200 hover:bg-godot-dark-bg/50"
                }`}
              >
                <span>{tab.name}</span>
                <button
                  onClick={(e) => handleCloseTab(index, e)}
                  className="ml-1 p-0.5 rounded hover:bg-godot-dark-border transition-colors"
                >
                  <X className="w-3 h-3" />
                </button>
              </button>
            ))}
          </div>

          {/* Editor Actions */}
          <div className="flex items-center gap-1 px-2">
            <button className="p-2 text-gray-400 hover:text-white hover:bg-godot-dark-card rounded transition-colors">
              <Save className="w-4 h-4" />
            </button>
            <button className="p-2 text-gray-400 hover:text-white hover:bg-godot-dark-card rounded transition-colors">
              <Play className="w-4 h-4" />
            </button>
            <button className="p-2 text-gray-400 hover:text-white hover:bg-godot-dark-card rounded transition-colors">
              <Settings2 className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Monaco Editor */}
        <div className="flex-1">
          {openTabs.length > 0 && openTabs[activeTab] ? (
            <GDScriptEditor
              value={openTabs[activeTab].content}
              onChange={(value) => {
                const updated = [...openTabs];
                updated[activeTab] = { ...updated[activeTab], content: value || "" };
                setOpenTabs(updated);
              }}
              path={openTabs[activeTab].path}
            />
          ) : (
            <div className="flex items-center justify-center h-full text-gray-500">
              <p>Open a file from the explorer to start editing</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
