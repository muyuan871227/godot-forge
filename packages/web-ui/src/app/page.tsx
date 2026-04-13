"use client";

import { useState } from "react";
import Link from "next/link";
import {
  Plus,
  Search,
  FolderOpen,
  Clock,
  MoreVertical,
  Gamepad2,
  Globe,
  Sword,
  Puzzle,
} from "lucide-react";

interface Project {
  id: string;
  name: string;
  description: string;
  template: string;
  lastModified: string;
  icon: React.ElementType;
  status: "active" | "building" | "archived";
}

const mockProjects: Project[] = [
  {
    id: "1",
    name: "Space Odyssey",
    description: "A 2D side-scrolling space shooter with procedural levels",
    template: "2D Platformer",
    lastModified: "2 hours ago",
    icon: Gamepad2,
    status: "active",
  },
  {
    id: "2",
    name: "Fantasy RPG",
    description: "Top-down RPG with AI-generated quests and dialogue",
    template: "2D Top-Down RPG",
    lastModified: "1 day ago",
    icon: Sword,
    status: "building",
  },
  {
    id: "3",
    name: "Web Puzzle",
    description: "Browser-based puzzle game with physics mechanics",
    template: "Puzzle",
    lastModified: "3 days ago",
    icon: Puzzle,
    status: "active",
  },
  {
    id: "4",
    name: "Multiplayer Arena",
    description: "3D multiplayer arena combat game",
    template: "3D FPS",
    lastModified: "1 week ago",
    icon: Globe,
    status: "archived",
  },
];

const statusColors: Record<string, string> = {
  active: "bg-godot-success/20 text-godot-success",
  building: "bg-godot-warning/20 text-godot-warning",
  archived: "bg-gray-500/20 text-gray-400",
};

export default function HomePage() {
  const [searchQuery, setSearchQuery] = useState("");

  const filtered = mockProjects.filter(
    (p) =>
      p.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      p.description.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-white">Projects</h1>
          <p className="text-gray-400 mt-1">
            Create and manage your Godot game projects
          </p>
        </div>
        <Link href="/templates" className="btn-primary flex items-center gap-2">
          <Plus className="w-5 h-5" />
          New Project
        </Link>
      </div>

      {/* Search */}
      <div className="relative mb-6">
        <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
        <input
          type="text"
          placeholder="Search projects..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="input-field pl-12"
        />
      </div>

      {/* Project Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
        {filtered.map((project) => {
          const Icon = project.icon;
          return (
            <Link
              key={project.id}
              href={`/project/${project.id}`}
              className="card group cursor-pointer"
            >
              <div className="flex items-start justify-between mb-4">
                <div className="w-12 h-12 bg-godot-accent/20 rounded-xl flex items-center justify-center group-hover:bg-godot-accent/30 transition-colors">
                  <Icon className="w-6 h-6 text-godot-accent" />
                </div>
                <div className="flex items-center gap-2">
                  <span
                    className={`text-xs px-2 py-1 rounded-full font-medium ${statusColors[project.status]}`}
                  >
                    {project.status}
                  </span>
                  <button
                    className="p-1 text-gray-500 hover:text-white transition-colors"
                    onClick={(e) => e.preventDefault()}
                  >
                    <MoreVertical className="w-4 h-4" />
                  </button>
                </div>
              </div>

              <h3 className="text-lg font-semibold text-white mb-1 group-hover:text-godot-accent transition-colors">
                {project.name}
              </h3>
              <p className="text-sm text-gray-400 mb-4 line-clamp-2">
                {project.description}
              </p>

              <div className="flex items-center justify-between text-xs text-gray-500">
                <span className="flex items-center gap-1">
                  <FolderOpen className="w-3.5 h-3.5" />
                  {project.template}
                </span>
                <span className="flex items-center gap-1">
                  <Clock className="w-3.5 h-3.5" />
                  {project.lastModified}
                </span>
              </div>
            </Link>
          );
        })}

        {/* New Project Card */}
        <Link
          href="/templates"
          className="card flex flex-col items-center justify-center min-h-[200px] border-dashed border-2 border-godot-dark-border hover:border-godot-accent/50 group cursor-pointer"
        >
          <div className="w-14 h-14 rounded-full bg-godot-dark-bg flex items-center justify-center mb-3 group-hover:bg-godot-accent/20 transition-colors">
            <Plus className="w-7 h-7 text-gray-500 group-hover:text-godot-accent transition-colors" />
          </div>
          <span className="text-sm font-medium text-gray-500 group-hover:text-gray-300 transition-colors">
            Create New Project
          </span>
        </Link>
      </div>
    </div>
  );
}
