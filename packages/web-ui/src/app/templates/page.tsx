"use client";

import {
  Gamepad2,
  Map,
  Crosshair,
  UserCircle,
  BookOpen,
  Puzzle,
  ArrowRight,
  Star,
  Clock,
} from "lucide-react";

interface Template {
  id: string;
  name: string;
  description: string;
  icon: React.ElementType;
  category: string;
  difficulty: "Beginner" | "Intermediate" | "Advanced";
  estimatedTime: string;
  features: string[];
  popular?: boolean;
}

const templates: Template[] = [
  {
    id: "2d-platformer",
    name: "2D Platformer",
    description:
      "Classic side-scrolling platformer with physics-based movement, collectibles, and level progression.",
    icon: Gamepad2,
    category: "2D",
    difficulty: "Beginner",
    estimatedTime: "30 min",
    features: ["Player Controller", "Tilemap Levels", "Collectibles", "Enemy AI"],
    popular: true,
  },
  {
    id: "2d-topdown-rpg",
    name: "2D Top-Down RPG",
    description:
      "Explore a world with NPC dialogue, inventory system, and quest mechanics.",
    icon: Map,
    category: "2D",
    difficulty: "Intermediate",
    estimatedTime: "1 hour",
    features: ["Dialogue System", "Inventory", "Quest System", "NPC AI"],
  },
  {
    id: "3d-fps",
    name: "3D First-Person Shooter",
    description:
      "Fast-paced FPS with weapon switching, health system, and arena-style maps.",
    icon: Crosshair,
    category: "3D",
    difficulty: "Advanced",
    estimatedTime: "2 hours",
    features: ["FPS Controller", "Weapon System", "Health & Ammo", "Enemy Spawner"],
  },
  {
    id: "3d-third-person",
    name: "3D Third-Person Adventure",
    description:
      "Third-person character controller with camera orbit, combat, and exploration.",
    icon: UserCircle,
    category: "3D",
    difficulty: "Intermediate",
    estimatedTime: "1.5 hours",
    features: ["Orbit Camera", "Melee Combat", "Exploration", "Checkpoints"],
  },
  {
    id: "visual-novel",
    name: "Visual Novel",
    description:
      "Story-driven game with branching dialogue, character sprites, and multiple endings.",
    icon: BookOpen,
    category: "Narrative",
    difficulty: "Beginner",
    estimatedTime: "45 min",
    features: ["Branching Dialogue", "Character Art", "Save/Load", "Multiple Endings"],
    popular: true,
  },
  {
    id: "puzzle",
    name: "Puzzle Game",
    description:
      "Grid-based puzzle game with level editor, scoring system, and progressive difficulty.",
    icon: Puzzle,
    category: "Casual",
    difficulty: "Beginner",
    estimatedTime: "30 min",
    features: ["Grid System", "Level Editor", "Score Tracking", "Hints"],
  },
];

const difficultyColors: Record<string, string> = {
  Beginner: "text-godot-success bg-godot-success/10",
  Intermediate: "text-godot-warning bg-godot-warning/10",
  Advanced: "text-godot-error bg-godot-error/10",
};

export default function TemplatesPage() {
  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white">Templates</h1>
        <p className="text-gray-400 mt-1">
          Start a new project from a game template. Each template comes with
          pre-built mechanics and AI-ready structure.
        </p>
      </div>

      {/* Template Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
        {templates.map((template) => {
          const Icon = template.icon;
          return (
            <div key={template.id} className="card group flex flex-col">
              {/* Header */}
              <div className="flex items-start justify-between mb-4">
                <div className="w-14 h-14 bg-godot-accent/20 rounded-2xl flex items-center justify-center group-hover:bg-godot-accent/30 transition-colors">
                  <Icon className="w-7 h-7 text-godot-accent" />
                </div>
                <div className="flex items-center gap-2">
                  {template.popular && (
                    <span className="flex items-center gap-1 text-xs text-godot-warning bg-godot-warning/10 px-2 py-0.5 rounded-full">
                      <Star className="w-3 h-3" />
                      Popular
                    </span>
                  )}
                  <span className="text-xs text-gray-500 bg-godot-dark-bg px-2 py-0.5 rounded-full">
                    {template.category}
                  </span>
                </div>
              </div>

              {/* Content */}
              <h3 className="text-lg font-semibold text-white mb-2 group-hover:text-godot-accent transition-colors">
                {template.name}
              </h3>
              <p className="text-sm text-gray-400 mb-4 flex-1">
                {template.description}
              </p>

              {/* Features */}
              <div className="flex flex-wrap gap-1.5 mb-4">
                {template.features.map((f) => (
                  <span
                    key={f}
                    className="text-xs bg-godot-dark-bg text-gray-400 px-2 py-1 rounded"
                  >
                    {f}
                  </span>
                ))}
              </div>

              {/* Footer */}
              <div className="flex items-center justify-between pt-4 border-t border-godot-dark-border">
                <div className="flex items-center gap-3">
                  <span
                    className={`text-xs px-2 py-0.5 rounded-full font-medium ${difficultyColors[template.difficulty]}`}
                  >
                    {template.difficulty}
                  </span>
                  <span className="flex items-center gap-1 text-xs text-gray-500">
                    <Clock className="w-3 h-3" />
                    {template.estimatedTime}
                  </span>
                </div>
                <button className="flex items-center gap-1 text-sm font-medium text-godot-accent hover:text-godot-accent-hover transition-colors">
                  Use Template
                  <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
