"use client";

import { useState } from "react";
import AssetGrid from "@/components/assets/AssetGrid";
import {
  Search,
  Upload,
  Sparkles,
  Image,
  Music,
  Box,
  Film,
  Filter,
  Grid3X3,
  List,
  Wand2,
  Loader2,
  AlertCircle,
} from "lucide-react";
import { imagegenApi, audiogenApi, modelgenApi } from "@/lib/api";

type AssetType = "all" | "sprites" | "models" | "audio" | "animations";
type ViewMode = "grid" | "list";

const assetFilters: { value: AssetType; label: string; icon: React.ElementType }[] = [
  { value: "all", label: "All", icon: Grid3X3 },
  { value: "sprites", label: "Sprites", icon: Image },
  { value: "models", label: "3D Models", icon: Box },
  { value: "audio", label: "Audio", icon: Music },
  { value: "animations", label: "Animations", icon: Film },
];

export default function AssetsPage() {
  const [filter, setFilter] = useState<AssetType>("all");
  const [viewMode, setViewMode] = useState<ViewMode>("grid");
  const [searchQuery, setSearchQuery] = useState("");
  const [generatePrompt, setGeneratePrompt] = useState("");
  const [generateType, setGenerateType] = useState<"sprite" | "3d" | "audio">("sprite");
  const [isGenerating, setIsGenerating] = useState(false);

  const [generateError, setGenerateError] = useState<string | null>(null);
  const [generatedAssets, setGeneratedAssets] = useState<
    { id: string; name: string; type: "sprites" | "models" | "audio"; path: string; size: string; createdAt: string }[]
  >([]);

  const handleGenerate = async () => {
    if (!generatePrompt.trim()) return;
    setIsGenerating(true);
    setGenerateError(null);

    try {
      if (generateType === "sprite") {
        const result = await imagegenApi.generate(generatePrompt, {
          style: "pixel_art",
          width: 32,
          height: 32,
        });
        const newAsset = {
          id: Date.now().toString(),
          name: result.image_path.split("/").pop() || "sprite.png",
          type: "sprites" as const,
          path: result.image_path,
          size: "N/A",
          createdAt: "just now",
        };
        setGeneratedAssets((prev) => [newAsset, ...prev]);
      } else if (generateType === "3d") {
        const result = await modelgenApi.generate(generatePrompt);
        const newAsset = {
          id: Date.now().toString(),
          name: result.model_path.split("/").pop() || "model.glb",
          type: "models" as const,
          path: result.model_path,
          size: "N/A",
          createdAt: "just now",
        };
        setGeneratedAssets((prev) => [newAsset, ...prev]);
      } else if (generateType === "audio") {
        const result = await audiogenApi.sfx(generatePrompt);
        const newAsset = {
          id: Date.now().toString(),
          name: result.filename,
          type: "audio" as const,
          path: `assets/audio/${result.filename}`,
          size: "N/A",
          createdAt: "just now",
        };
        setGeneratedAssets((prev) => [newAsset, ...prev]);
      }
      setGeneratePrompt("");
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Generation failed. Please try again.";
      setGenerateError(message);
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div className="flex h-full">
      {/* Main Content */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Toolbar */}
        <div className="p-4 border-b border-godot-dark-border bg-godot-dark-surface">
          <div className="flex items-center gap-4 mb-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
              <input
                type="text"
                placeholder="Search assets..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="input-field pl-10 text-sm"
              />
            </div>
            <button className="btn-secondary flex items-center gap-2 text-sm">
              <Upload className="w-4 h-4" />
              Import
            </button>
          </div>

          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1">
              {assetFilters.map((f) => {
                const Icon = f.icon;
                return (
                  <button
                    key={f.value}
                    onClick={() => setFilter(f.value)}
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                      filter === f.value
                        ? "bg-godot-accent/20 text-godot-accent"
                        : "text-gray-400 hover:text-gray-200 hover:bg-godot-dark-card"
                    }`}
                  >
                    <Icon className="w-3.5 h-3.5" />
                    {f.label}
                  </button>
                );
              })}
            </div>
            <div className="flex items-center gap-1">
              <button
                onClick={() => setViewMode("grid")}
                className={`p-2 rounded transition-colors ${
                  viewMode === "grid" ? "text-white bg-godot-dark-card" : "text-gray-500 hover:text-gray-300"
                }`}
              >
                <Grid3X3 className="w-4 h-4" />
              </button>
              <button
                onClick={() => setViewMode("list")}
                className={`p-2 rounded transition-colors ${
                  viewMode === "list" ? "text-white bg-godot-dark-card" : "text-gray-500 hover:text-gray-300"
                }`}
              >
                <List className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>

        {/* Asset Grid */}
        <div className="flex-1 overflow-auto scrollbar-thin p-4">
          <AssetGrid filter={filter} viewMode={viewMode} searchQuery={searchQuery} assets={generatedAssets} />
        </div>
      </div>

      {/* Generation Panel */}
      <div className="w-80 border-l border-godot-dark-border bg-godot-dark-surface flex flex-col shrink-0">
        <div className="p-4 border-b border-godot-dark-border">
          <h3 className="text-sm font-semibold text-white flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-godot-accent" />
            AI Asset Generator
          </h3>
        </div>

        <div className="p-4 space-y-4 flex-1">
          {/* Generation Type */}
          <div>
            <label className="text-xs font-medium text-gray-400 mb-2 block">Asset Type</label>
            <div className="grid grid-cols-3 gap-2">
              {[
                { value: "sprite" as const, label: "Sprite", icon: Image },
                { value: "3d" as const, label: "3D Model", icon: Box },
                { value: "audio" as const, label: "Audio", icon: Music },
              ].map((type) => {
                const Icon = type.icon;
                return (
                  <button
                    key={type.value}
                    onClick={() => setGenerateType(type.value)}
                    className={`flex flex-col items-center gap-1 p-3 rounded-lg border text-xs transition-colors ${
                      generateType === type.value
                        ? "border-godot-accent bg-godot-accent/10 text-godot-accent"
                        : "border-godot-dark-border text-gray-400 hover:border-gray-500"
                    }`}
                  >
                    <Icon className="w-5 h-5" />
                    {type.label}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Prompt */}
          <div>
            <label className="text-xs font-medium text-gray-400 mb-2 block">Description</label>
            <textarea
              value={generatePrompt}
              onChange={(e) => setGeneratePrompt(e.target.value)}
              placeholder={
                generateType === "sprite"
                  ? "A pixel art hero character with sword and shield, 32x32..."
                  : generateType === "3d"
                    ? "A low-poly treasure chest with gold trim..."
                    : "Fantasy RPG battle music, orchestral, epic..."
              }
              className="input-field text-sm resize-none h-28"
            />
          </div>

          {/* Style Options */}
          {generateType === "sprite" && (
            <div>
              <label className="text-xs font-medium text-gray-400 mb-2 block">Style</label>
              <select className="input-field text-sm">
                <option>Pixel Art (16x16)</option>
                <option>Pixel Art (32x32)</option>
                <option>Pixel Art (64x64)</option>
                <option>Hand-drawn</option>
                <option>Flat Vector</option>
                <option>Realistic</option>
              </select>
            </div>
          )}

          {/* Generate Button */}
          <button
            onClick={handleGenerate}
            disabled={isGenerating || !generatePrompt.trim()}
            className="btn-primary w-full flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isGenerating ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Generating...
              </>
            ) : (
              <>
                <Wand2 className="w-4 h-4" />
                Generate Asset
              </>
            )}
          </button>

          {/* Error Display */}
          {generateError && (
            <div className="p-3 rounded-lg bg-godot-error/10 border border-godot-error/30 flex items-start gap-2">
              <AlertCircle className="w-4 h-4 text-godot-error shrink-0 mt-0.5" />
              <p className="text-xs text-godot-error">{generateError}</p>
            </div>
          )}

          {/* Generation History */}
          <div>
            <label className="text-xs font-medium text-gray-400 mb-2 block">Recent Generations</label>
            <div className="space-y-2">
              {generatedAssets.length === 0 ? (
                <p className="text-xs text-gray-600 px-2">No assets generated yet. Use the form above to create new assets.</p>
              ) : (
                generatedAssets.slice(0, 10).map((asset) => {
                  const TypeIcon = asset.type === "sprites" ? Image : asset.type === "models" ? Box : Music;
                  return (
                    <div
                      key={asset.id}
                      className="flex items-center gap-3 p-2 rounded-lg bg-godot-dark-bg hover:bg-godot-dark-card transition-colors cursor-pointer"
                    >
                      <div className="w-10 h-10 rounded bg-godot-dark-card flex items-center justify-center">
                        <TypeIcon className="w-5 h-5 text-gray-500" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-xs text-gray-300 truncate">{asset.name}</p>
                        <p className="text-xs text-gray-600">{asset.type} - {asset.createdAt}</p>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
