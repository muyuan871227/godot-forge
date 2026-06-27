import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/lib/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        godot: {
          blue: "#478CBF",
          "blue-dark": "#25598C",
          "dark-bg": "#1a1a2e",
          "dark-surface": "#16213e",
          "dark-card": "#1e2a47",
          "dark-border": "#2a3a5c",
          accent: "#6c63ff",
          "accent-hover": "#5a52d5",
          success: "#4ade80",
          warning: "#fbbf24",
          error: "#f87171",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "Fira Code", "monospace"],
      },
    },
  },
  plugins: [],
};

export default config;
