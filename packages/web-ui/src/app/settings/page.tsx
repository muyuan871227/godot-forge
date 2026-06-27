"use client";

import { useState } from "react";
import {
  Settings,
  Server,
  Key,
  Palette,
  Save,
  CheckCircle2,
  Globe,
  Cpu,
  Shield,
} from "lucide-react";

interface SettingsState {
  apiUrl: string;
  apiKey: string;
  theme: "dark" | "light" | "system";
  godotPath: string;
  aiProvider: string;
  autoSave: boolean;
  telemetry: boolean;
}

export default function SettingsPage() {
  const [settings, setSettings] = useState<SettingsState>({
    apiUrl: "http://localhost:3001",
    apiKey: "",
    theme: "dark",
    godotPath: "/usr/local/bin/godot",
    aiProvider: "anthropic",
    autoSave: true,
    telemetry: false,
  });
  const [saved, setSaved] = useState(false);

  const handleSave = () => {
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const updateSetting = <K extends keyof SettingsState>(
    key: K,
    value: SettingsState[K]
  ) => {
    setSettings((prev) => ({ ...prev, [key]: value }));
  };

  return (
    <div className="p-8 max-w-3xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-white flex items-center gap-3">
          <Settings className="w-7 h-7 text-godot-accent" />
          Platform Settings
        </h1>
        <p className="text-gray-400 mt-1">
          Configure your GodotForge development environment
        </p>
      </div>

      <div className="space-y-6">
        {/* API Connection */}
        <div className="card">
          <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
            <Server className="w-4 h-4 text-godot-accent" />
            API Connection
          </h3>
          <div className="space-y-4">
            <div>
              <label className="text-xs font-medium text-gray-400 mb-1.5 block">
                API Server URL
              </label>
              <input
                type="text"
                value={settings.apiUrl}
                onChange={(e) => updateSetting("apiUrl", e.target.value)}
                className="input-field text-sm"
                placeholder="http://localhost:3001"
              />
              <p className="text-xs text-gray-600 mt-1">
                The URL of the GodotForge MCP server
              </p>
            </div>
            <div>
              <label className="text-xs font-medium text-gray-400 mb-1.5 block">
                Godot Executable Path
              </label>
              <input
                type="text"
                value={settings.godotPath}
                onChange={(e) => updateSetting("godotPath", e.target.value)}
                className="input-field text-sm"
                placeholder="/usr/local/bin/godot"
              />
            </div>
          </div>
        </div>

        {/* AI Configuration */}
        <div className="card">
          <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
            <Cpu className="w-4 h-4 text-godot-accent" />
            AI Configuration
          </h3>
          <div className="space-y-4">
            <div>
              <label className="text-xs font-medium text-gray-400 mb-1.5 block">
                AI Provider
              </label>
              <select
                value={settings.aiProvider}
                onChange={(e) => updateSetting("aiProvider", e.target.value)}
                className="input-field text-sm"
              >
                <option value="anthropic">Anthropic (Claude)</option>
                <option value="openai">OpenAI (GPT-4)</option>
                <option value="ollama">Ollama (Local)</option>
              </select>
            </div>
            <div>
              <label className="text-xs font-medium text-gray-400 mb-1.5 block">
                API Key
              </label>
              <div className="relative">
                <Key className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
                <input
                  type="password"
                  value={settings.apiKey}
                  onChange={(e) => updateSetting("apiKey", e.target.value)}
                  className="input-field text-sm pl-10"
                  placeholder="sk-..."
                />
              </div>
              <p className="text-xs text-gray-600 mt-1">
                Your API key for the selected AI provider
              </p>
            </div>
          </div>
        </div>

        {/* Appearance */}
        <div className="card">
          <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
            <Palette className="w-4 h-4 text-godot-accent" />
            Appearance
          </h3>
          <div>
            <label className="text-xs font-medium text-gray-400 mb-2 block">
              Theme
            </label>
            <div className="grid grid-cols-3 gap-3">
              {(["dark", "light", "system"] as const).map((theme) => (
                <button
                  key={theme}
                  onClick={() => updateSetting("theme", theme)}
                  className={`py-3 rounded-lg text-sm font-medium capitalize transition-colors border ${
                    settings.theme === theme
                      ? "border-godot-accent bg-godot-accent/10 text-godot-accent"
                      : "border-godot-dark-border text-gray-400 hover:border-gray-500"
                  }`}
                >
                  {theme}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Privacy */}
        <div className="card">
          <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
            <Shield className="w-4 h-4 text-godot-accent" />
            Privacy & Data
          </h3>
          <div className="space-y-4">
            <label className="flex items-center justify-between cursor-pointer">
              <div>
                <p className="text-sm text-gray-300">Auto-save projects</p>
                <p className="text-xs text-gray-600">
                  Automatically save changes every 30 seconds
                </p>
              </div>
              <button
                onClick={() => updateSetting("autoSave", !settings.autoSave)}
                className={`w-10 h-6 rounded-full transition-colors relative ${
                  settings.autoSave ? "bg-godot-accent" : "bg-godot-dark-border"
                }`}
              >
                <div
                  className={`w-4 h-4 bg-white rounded-full absolute top-1 transition-transform ${
                    settings.autoSave ? "translate-x-5" : "translate-x-1"
                  }`}
                />
              </button>
            </label>
            <label className="flex items-center justify-between cursor-pointer">
              <div>
                <p className="text-sm text-gray-300">Usage telemetry</p>
                <p className="text-xs text-gray-600">
                  Send anonymous usage data to improve GodotForge
                </p>
              </div>
              <button
                onClick={() => updateSetting("telemetry", !settings.telemetry)}
                className={`w-10 h-6 rounded-full transition-colors relative ${
                  settings.telemetry ? "bg-godot-accent" : "bg-godot-dark-border"
                }`}
              >
                <div
                  className={`w-4 h-4 bg-white rounded-full absolute top-1 transition-transform ${
                    settings.telemetry ? "translate-x-5" : "translate-x-1"
                  }`}
                />
              </button>
            </label>
          </div>
        </div>

        {/* Save Button */}
        <div className="flex justify-end">
          <button
            onClick={handleSave}
            className="btn-primary flex items-center gap-2 px-6"
          >
            {saved ? (
              <>
                <CheckCircle2 className="w-5 h-5" />
                Saved!
              </>
            ) : (
              <>
                <Save className="w-5 h-5" />
                Save Settings
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
