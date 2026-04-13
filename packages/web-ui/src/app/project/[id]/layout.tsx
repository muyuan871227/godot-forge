"use client";

import Link from "next/link";
import { usePathname, useParams } from "next/navigation";
import {
  LayoutDashboard,
  MessageSquare,
  Code2,
  Image,
  Layers,
  Package,
  Settings,
  ArrowLeft,
} from "lucide-react";

const tabs = [
  { segment: "", label: "Overview", icon: LayoutDashboard },
  { segment: "/chat", label: "Chat", icon: MessageSquare },
  { segment: "/editor", label: "Editor", icon: Code2 },
  { segment: "/assets", label: "Assets", icon: Image },
  { segment: "/build", label: "Build", icon: Package },
];

export default function ProjectLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const params = useParams();
  const projectId = params.id as string;
  const basePath = `/project/${projectId}`;

  return (
    <div className="flex flex-col h-full">
      {/* Project Header */}
      <header className="bg-godot-dark-surface border-b border-godot-dark-border px-6 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link
              href="/"
              className="p-2 text-gray-400 hover:text-white hover:bg-godot-dark-card rounded-lg transition-colors"
            >
              <ArrowLeft className="w-5 h-5" />
            </Link>
            <div>
              <h2 className="text-lg font-semibold text-white">
                Project #{projectId}
              </h2>
              <p className="text-xs text-gray-500">Godot 4.4 Project</p>
            </div>
          </div>
          <Link
            href={`${basePath}/settings`}
            className="p-2 text-gray-400 hover:text-white hover:bg-godot-dark-card rounded-lg transition-colors"
          >
            <Settings className="w-5 h-5" />
          </Link>
        </div>

        {/* Tab Navigation */}
        <nav className="flex items-center gap-1 mt-3 -mb-px">
          {tabs.map((tab) => {
            const href = `${basePath}${tab.segment}`;
            const isActive =
              tab.segment === ""
                ? pathname === basePath
                : pathname.startsWith(href);
            const Icon = tab.icon;

            return (
              <Link
                key={tab.segment}
                href={href}
                className={`tab-link flex items-center gap-2 ${isActive ? "tab-link-active" : ""}`}
              >
                <Icon className="w-4 h-4" />
                {tab.label}
              </Link>
            );
          })}
        </nav>
      </header>

      {/* Page Content */}
      <div className="flex-1 overflow-auto scrollbar-thin">{children}</div>
    </div>
  );
}
