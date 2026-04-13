import { create } from "zustand";

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
