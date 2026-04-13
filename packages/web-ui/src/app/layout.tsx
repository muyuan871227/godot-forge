"use client";

import "./globals.css";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  FolderKanban,
  LayoutTemplate,
  Settings,
  Gamepad2,
  Sparkles,
} from "lucide-react";

const sidebarItems = [
  { href: "/", label: "Projects", icon: FolderKanban },
  { href: "/templates", label: "Templates", icon: LayoutTemplate },
  { href: "/settings", label: "Settings", icon: Settings },
];

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();

  return (
    <html lang="en" className="dark">
      <body className="flex h-screen overflow-hidden">
        {/* Sidebar */}
        <aside className="w-64 bg-godot-dark-surface border-r border-godot-dark-border flex flex-col shrink-0">
          {/* Logo */}
          <div className="p-6 border-b border-godot-dark-border">
            <Link href="/" className="flex items-center gap-3">
              <div className="w-10 h-10 bg-godot-accent rounded-xl flex items-center justify-center">
                <Gamepad2 className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-lg font-bold text-white">GodotForge</h1>
                <p className="text-xs text-gray-500 flex items-center gap-1">
                  <Sparkles className="w-3 h-3" />
                  AI Game Creator
                </p>
              </div>
            </Link>
          </div>

          {/* Navigation */}
          <nav className="flex-1 p-4 space-y-1">
            {sidebarItems.map((item) => {
              const Icon = item.icon;
              const isActive =
                item.href === "/"
                  ? pathname === "/"
                  : pathname.startsWith(item.href);

              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`sidebar-link ${isActive ? "sidebar-link-active" : ""}`}
                >
                  <Icon className="w-5 h-5" />
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </nav>

          {/* Footer */}
          <div className="p-4 border-t border-godot-dark-border">
            <div className="text-xs text-gray-500">
              <p>GodotForge v0.1.0</p>
              <p className="mt-1">Godot 4.4+ | MIT License</p>
            </div>
          </div>
        </aside>

        {/* Main Content */}
        <main className="flex-1 overflow-auto scrollbar-thin">{children}</main>
      </body>
    </html>
  );
}
