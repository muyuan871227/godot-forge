import { create } from "zustand";
import {
  codegenApi,
  imagegenApi,
  modelgenApi,
  audiogenApi,
} from "@/lib/api";

export type ChatMode = "code" | "2d" | "3d" | "audio";

export interface ChatFile {
  name: string;
  content: string;
  language: string;
  applied?: boolean;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  mode: ChatMode;
  timestamp: Date;
  files?: ChatFile[];
  isStreaming?: boolean;
}

interface ChatState {
  // Messages
  messages: ChatMessage[];
  isLoading: boolean;

  // Current input
  mode: ChatMode;
  inputValue: string;

  // Streaming state
  streamingMessageId: string | null;

  // Actions
  setMode: (mode: ChatMode) => void;
  setInputValue: (value: string) => void;

  addMessage: (message: ChatMessage) => void;
  updateMessage: (id: string, updates: Partial<ChatMessage>) => void;
  removeMessage: (id: string) => void;
  clearMessages: () => void;

  setLoading: (loading: boolean) => void;

  // Async action
  sendMessage: (projectId: string, content: string, mode: ChatMode) => Promise<void>;

  // Streaming
  startStreaming: (messageId: string) => void;
  appendToStream: (messageId: string, content: string) => void;
  finishStreaming: (messageId: string, files?: ChatFile[]) => void;

  // File operations
  markFileApplied: (messageId: string, fileName: string) => void;

  // Conversation management
  loadHistory: (messages: ChatMessage[]) => void;
}

export const useChatStore = create<ChatState>((set, get) => ({
  messages: [],
  isLoading: false,
  mode: "code",
  inputValue: "",
  streamingMessageId: null,

  setMode: (mode) => set({ mode }),
  setInputValue: (inputValue) => set({ inputValue }),

  addMessage: (message) =>
    set((state) => ({
      messages: [...state.messages, message],
    })),

  updateMessage: (id, updates) =>
    set((state) => ({
      messages: state.messages.map((m) =>
        m.id === id ? { ...m, ...updates } : m
      ),
    })),

  removeMessage: (id) =>
    set((state) => ({
      messages: state.messages.filter((m) => m.id !== id),
    })),

  clearMessages: () => set({ messages: [], streamingMessageId: null }),

  setLoading: (isLoading) => set({ isLoading }),

  sendMessage: async (projectId: string, content: string, mode: ChatMode) => {
    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      role: "user",
      content,
      mode,
      timestamp: new Date(),
    };

    set((state) => ({
      messages: [...state.messages, userMessage],
      isLoading: true,
    }));

    try {
      let assistantContent = "";
      let files: ChatFile[] | undefined;

      if (mode === "code") {
        const result = await codegenApi.generate(content);
        assistantContent = result.explanation || "Code generated successfully.";
        if (result.files && result.files.length > 0) {
          files = result.files.map((f) => ({
            name: f.path.split("/").pop() || f.path,
            content: f.content,
            language: f.path.endsWith(".gd") ? "gdscript" : "text",
          }));
        } else if (result.code) {
          files = [
            {
              name: "generated.gd",
              content: result.code,
              language: "gdscript",
            },
          ];
        }
      } else if (mode === "2d") {
        const result = await imagegenApi.generate(content, { style: "pixel_art" });
        assistantContent = `Image generated successfully.\n\n**Saved to:** \`${result.image_path}\`\n\nThe asset has been added to your project.`;
      } else if (mode === "3d") {
        const result = await modelgenApi.generate(content);
        assistantContent = `3D model generated successfully.\n\n**Format:** ${result.format}\n**Saved to:** \`${result.model_path}\`\n\nImport it into your Godot scene as a \`MeshInstance3D\`.`;
      } else if (mode === "audio") {
        const result = await audiogenApi.sfx(content);
        assistantContent = `Audio generated successfully.\n\n**File:** \`${result.filename}\`\n\nAdd it to an \`AudioStreamPlayer\` node to use it in your game.`;
      }

      const assistantMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: assistantContent,
        mode,
        timestamp: new Date(),
        files,
      };

      set((state) => ({
        messages: [...state.messages, assistantMessage],
        isLoading: false,
      }));
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Failed to generate response. Please try again.";
      const errorMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: `Error: ${message}`,
        mode,
        timestamp: new Date(),
      };

      set((state) => ({
        messages: [...state.messages, errorMessage],
        isLoading: false,
      }));
    }
  },

  startStreaming: (messageId) => {
    const { mode } = get();
    const streamingMessage: ChatMessage = {
      id: messageId,
      role: "assistant",
      content: "",
      mode,
      timestamp: new Date(),
      isStreaming: true,
    };
    set((state) => ({
      messages: [...state.messages, streamingMessage],
      streamingMessageId: messageId,
      isLoading: true,
    }));
  },

  appendToStream: (messageId, content) =>
    set((state) => ({
      messages: state.messages.map((m) =>
        m.id === messageId
          ? { ...m, content: m.content + content }
          : m
      ),
    })),

  finishStreaming: (messageId, files) =>
    set((state) => ({
      messages: state.messages.map((m) =>
        m.id === messageId
          ? { ...m, isStreaming: false, files }
          : m
      ),
      streamingMessageId: null,
      isLoading: false,
    })),

  markFileApplied: (messageId, fileName) =>
    set((state) => ({
      messages: state.messages.map((m) =>
        m.id === messageId
          ? {
              ...m,
              files: m.files?.map((f) =>
                f.name === fileName ? { ...f, applied: true } : f
              ),
            }
          : m
      ),
    })),

  loadHistory: (messages) =>
    set({
      messages: messages.map((m) => ({
        ...m,
        timestamp: new Date(m.timestamp),
      })),
    }),
}));

export default useChatStore;
