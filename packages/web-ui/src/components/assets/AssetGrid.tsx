"use client";

import {
  Image,
  Box,
  Music,
  Film,
  MoreVertical,
  Download,
  Trash2,
  Eye,
  FileType,
} from "lucide-react";

interface Asset {
  id: string;
  name: string;
  type: "sprites" | "models" | "audio" | "animations";
  path: string;
  size: string;
  dimensions?: string;
  duration?: string;
  createdAt: string;
}

const mockAssets: Asset[] = [
  {
    id: "1",
    name: "player_idle.png",
    type: "sprites",
    path: "assets/sprites/player_idle.png",
    size: "4.2 KB",
    dimensions: "32x32",
    createdAt: "2 hours ago",
  },
  {
    id: "2",
    name: "player_run.png",
    type: "sprites",
    path: "assets/sprites/player_run.png",
    size: "12.8 KB",
    dimensions: "128x32",
    createdAt: "2 hours ago",
  },
  {
    id: "3",
    name: "tileset_forest.png",
    type: "sprites",
    path: "assets/sprites/tileset_forest.png",
    size: "24.1 KB",
    dimensions: "256x256",
    createdAt: "1 day ago",
  },
  {
    id: "4",
    name: "enemy_goblin.png",
    type: "sprites",
    path: "assets/sprites/enemy_goblin.png",
    size: "6.4 KB",
    dimensions: "32x32",
    createdAt: "1 day ago",
  },
  {
    id: "5",
    name: "treasure_chest.glb",
    type: "models",
    path: "assets/models/treasure_chest.glb",
    size: "128 KB",
    dimensions: "1,200 tris",
    createdAt: "3 days ago",
  },
  {
    id: "6",
    name: "tree_pine.glb",
    type: "models",
    path: "assets/models/tree_pine.glb",
    size: "96 KB",
    dimensions: "800 tris",
    createdAt: "3 days ago",
  },
  {
    id: "7",
    name: "jump.ogg",
    type: "audio",
    path: "assets/audio/jump.ogg",
    size: "18 KB",
    duration: "0.3s",
    createdAt: "1 week ago",
  },
  {
    id: "8",
    name: "bgm_forest.ogg",
    type: "audio",
    path: "assets/audio/bgm_forest.ogg",
    size: "2.1 MB",
    duration: "2:34",
    createdAt: "1 week ago",
  },
  {
    id: "9",
    name: "coin_collect.ogg",
    type: "audio",
    path: "assets/audio/coin_collect.ogg",
    size: "12 KB",
    duration: "0.5s",
    createdAt: "1 week ago",
  },
  {
    id: "10",
    name: "player_attack.tres",
    type: "animations",
    path: "assets/animations/player_attack.tres",
    size: "3.2 KB",
    duration: "0.8s",
    createdAt: "5 days ago",
  },
];

const typeIcons: Record<string, React.ElementType> = {
  sprites: Image,
  models: Box,
  audio: Music,
  animations: Film,
};

const typeColors: Record<string, string> = {
  sprites: "text-green-400 bg-green-400/10",
  models: "text-cyan-400 bg-cyan-400/10",
  audio: "text-yellow-400 bg-yellow-400/10",
  animations: "text-purple-400 bg-purple-400/10",
};

interface AssetGridProps {
  filter: string;
  viewMode: "grid" | "list";
  searchQuery: string;
}

export default function AssetGrid({ filter, viewMode, searchQuery }: AssetGridProps) {
  const filtered = mockAssets.filter((a) => {
    const matchesFilter = filter === "all" || a.type === filter;
    const matchesSearch =
      !searchQuery ||
      a.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      a.path.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesFilter && matchesSearch;
  });

  if (filtered.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-gray-500">
        <FileType className="w-12 h-12 mb-3 text-gray-600" />
        <p className="text-sm font-medium">No assets found</p>
        <p className="text-xs mt-1">
          Try a different filter or generate new assets
        </p>
      </div>
    );
  }

  if (viewMode === "list") {
    return (
      <div className="space-y-1">
        {/* List Header */}
        <div className="flex items-center gap-4 px-4 py-2 text-xs text-gray-500 font-medium">
          <span className="flex-1">Name</span>
          <span className="w-20 text-center">Type</span>
          <span className="w-20 text-right">Size</span>
          <span className="w-24 text-right">Details</span>
          <span className="w-24 text-right">Created</span>
          <span className="w-8" />
        </div>

        {filtered.map((asset) => {
          const Icon = typeIcons[asset.type];
          return (
            <div
              key={asset.id}
              className="flex items-center gap-4 px-4 py-2.5 rounded-lg hover:bg-godot-dark-card transition-colors cursor-pointer group"
            >
              <div className="flex items-center gap-3 flex-1 min-w-0">
                <div className={`w-8 h-8 rounded flex items-center justify-center ${typeColors[asset.type]}`}>
                  <Icon className="w-4 h-4" />
                </div>
                <div className="min-w-0">
                  <p className="text-sm text-gray-200 truncate">{asset.name}</p>
                  <p className="text-xs text-gray-600 truncate">{asset.path}</p>
                </div>
              </div>
              <span className="w-20 text-center text-xs text-gray-400 capitalize">
                {asset.type}
              </span>
              <span className="w-20 text-right text-xs text-gray-400">
                {asset.size}
              </span>
              <span className="w-24 text-right text-xs text-gray-500">
                {asset.dimensions || asset.duration || "-"}
              </span>
              <span className="w-24 text-right text-xs text-gray-600">
                {asset.createdAt}
              </span>
              <button className="w-8 p-1 text-gray-600 hover:text-gray-300 opacity-0 group-hover:opacity-100 transition-all">
                <MoreVertical className="w-4 h-4" />
              </button>
            </div>
          );
        })}
      </div>
    );
  }

  // Grid View
  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
      {filtered.map((asset) => {
        const Icon = typeIcons[asset.type];
        return (
          <div
            key={asset.id}
            className="group bg-godot-dark-card border border-godot-dark-border rounded-xl overflow-hidden hover:border-godot-accent/50 transition-all cursor-pointer"
          >
            {/* Thumbnail */}
            <div className="aspect-square bg-godot-dark-bg flex items-center justify-center relative">
              <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${typeColors[asset.type]}`}>
                <Icon className="w-6 h-6" />
              </div>

              {/* Hover overlay */}
              <div className="absolute inset-0 bg-black/60 flex items-center justify-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                <button className="p-2 bg-white/10 rounded-lg hover:bg-white/20 transition-colors">
                  <Eye className="w-4 h-4 text-white" />
                </button>
                <button className="p-2 bg-white/10 rounded-lg hover:bg-white/20 transition-colors">
                  <Download className="w-4 h-4 text-white" />
                </button>
                <button className="p-2 bg-white/10 rounded-lg hover:bg-white/20 transition-colors">
                  <Trash2 className="w-4 h-4 text-godot-error" />
                </button>
              </div>

              {/* Size badge */}
              <span className="absolute top-2 right-2 text-[10px] bg-black/60 text-gray-400 px-1.5 py-0.5 rounded">
                {asset.size}
              </span>
            </div>

            {/* Info */}
            <div className="p-3">
              <p className="text-sm text-gray-200 truncate font-medium">
                {asset.name}
              </p>
              <div className="flex items-center justify-between mt-1">
                <span className="text-xs text-gray-500">
                  {asset.dimensions || asset.duration || asset.type}
                </span>
                <span className="text-xs text-gray-600">{asset.createdAt}</span>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
