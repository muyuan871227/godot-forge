"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Plus,
  Search,
  FolderOpen,
  Clock,
  MoreVertical,
  Gamepad2,
  Loader2,
  AlertCircle,
} from "lucide-react";
import { useProjectStore } from "@/lib/stores/project";

const statusColors: Record<string, string> = {
  active: "bg-godot-success/20 text-godot-success",
  building: "bg-godot-warning/20 text-godot-warning",
  archived: "bg-gray-500/20 text-gray-400",
};

function formatDate(dateStr: string): string {
  try {
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    if (diffMins < 60) return `${diffMins}m ago`;
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours}h ago`;
    const diffDays = Math.floor(diffHours / 24);
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  } catch {
    return dateStr;
  }
}

export default function HomePage() {
  const [searchQuery, setSearchQuery] = useState("");
  const router = useRouter();
  const {
    projects,
    projectsLoading,
    projectsError,
    fetchProjects,
    createProject,
    deleteProject,
  } = useProjectStore();

  useEffect(() => {
    fetchProjects();
  }, [fetchProjects]);

  const filtered = projects.filter(
    (p) =>
      p.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      p.description.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleNewProject = async () => {
    const name = window.prompt("Enter project name:");
    if (!name?.trim()) return;
    const description = window.prompt("Enter project description (optional):") || "";
    try {
      const project = await createProject({ name: name.trim(), description });
      router.push(`/project/${project.id}`);
    } catch {
      // Error is already stored in projectsError
    }
  };

  const handleDelete = async (e: React.MouseEvent, id: string) => {
    e.preventDefault();
    e.stopPropagation();
    if (!window.confirm("Are you sure you want to delete this project?")) return;
    try {
      await deleteProject(id);
    } catch {
      // Error is already stored in projectsError
    }
  };

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
        <button onClick={handleNewProject} className="btn-primary flex items-center gap-2">
          <Plus className="w-5 h-5" />
          New Project
        </button>
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

      {/* Error State */}
      {projectsError && (
        <div className="mb-6 p-4 rounded-xl bg-godot-error/10 border border-godot-error/30 flex items-center gap-3">
          <AlertCircle className="w-5 h-5 text-godot-error shrink-0" />
          <p className="text-sm text-godot-error">{projectsError}</p>
        </div>
      )}

      {/* Loading State */}
      {projectsLoading && projects.length === 0 && (
        <div className="flex flex-col items-center justify-center py-20">
          <Loader2 className="w-8 h-8 text-godot-accent animate-spin mb-4" />
          <p className="text-gray-400">Loading projects...</p>
        </div>
      )}

      {/* Empty State */}
      {!projectsLoading && !projectsError && projects.length === 0 && (
        <div className="flex flex-col items-center justify-center py-20">
          <div className="w-20 h-20 rounded-2xl bg-godot-dark-card flex items-center justify-center mb-4">
            <Gamepad2 className="w-10 h-10 text-gray-600" />
          </div>
          <h3 className="text-lg font-semibold text-gray-300 mb-2">No projects yet</h3>
          <p className="text-gray-500 mb-6">Create your first Godot game project to get started.</p>
          <button onClick={handleNewProject} className="btn-primary flex items-center gap-2">
            <Plus className="w-5 h-5" />
            Create Project
          </button>
        </div>
      )}

      {/* Project Grid */}
      {filtered.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
          {filtered.map((project) => (
            <Link
              key={project.id}
              href={`/project/${project.id}`}
              className="card group cursor-pointer"
            >
              <div className="flex items-start justify-between mb-4">
                <div className="w-12 h-12 bg-godot-accent/20 rounded-xl flex items-center justify-center group-hover:bg-godot-accent/30 transition-colors">
                  <Gamepad2 className="w-6 h-6 text-godot-accent" />
                </div>
                <div className="flex items-center gap-2">
                  <span
                    className={`text-xs px-2 py-1 rounded-full font-medium ${statusColors[project.status] || statusColors.active}`}
                  >
                    {project.status}
                  </span>
                  <button
                    className="p-1 text-gray-500 hover:text-white transition-colors"
                    onClick={(e) => handleDelete(e, project.id)}
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
                  {project.template || "Custom"}
                </span>
                <span className="flex items-center gap-1">
                  <Clock className="w-3.5 h-3.5" />
                  {formatDate(project.createdAt)}
                </span>
              </div>
            </Link>
          ))}

          {/* New Project Card */}
          <button
            onClick={handleNewProject}
            className="card flex flex-col items-center justify-center min-h-[200px] border-dashed border-2 border-godot-dark-border hover:border-godot-accent/50 group cursor-pointer"
          >
            <div className="w-14 h-14 rounded-full bg-godot-dark-bg flex items-center justify-center mb-3 group-hover:bg-godot-accent/20 transition-colors">
              <Plus className="w-7 h-7 text-gray-500 group-hover:text-godot-accent transition-colors" />
            </div>
            <span className="text-sm font-medium text-gray-500 group-hover:text-gray-300 transition-colors">
              Create New Project
            </span>
          </button>
        </div>
      )}
    </div>
  );
}
