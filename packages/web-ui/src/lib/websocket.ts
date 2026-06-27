import { io, Socket } from "socket.io-client";

const WS_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:3001";

export type ConnectionStatus = "disconnected" | "connecting" | "connected" | "error";

export interface WSMessage {
  type: string;
  payload: unknown;
  timestamp: number;
}

type EventHandler = (data: unknown) => void;
type StatusHandler = (status: ConnectionStatus) => void;

class WebSocketManager {
  private socket: Socket | null = null;
  private status: ConnectionStatus = "disconnected";
  private statusListeners: Set<StatusHandler> = new Set();
  private eventHandlers: Map<string, Set<EventHandler>> = new Map();
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 10;

  connect(projectId?: string): void {
    if (this.socket?.connected) {
      return;
    }

    this.setStatus("connecting");

    this.socket = io(WS_URL, {
      path: "/ws",
      transports: ["websocket", "polling"],
      reconnection: true,
      reconnectionAttempts: this.maxReconnectAttempts,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 10000,
      query: projectId ? { projectId } : undefined,
    });

    this.socket.on("connect", () => {
      this.reconnectAttempts = 0;
      this.setStatus("connected");
      console.log("[WS] Connected to server");

      if (projectId) {
        this.socket?.emit("join:project", { projectId });
      }
    });

    this.socket.on("disconnect", (reason) => {
      this.setStatus("disconnected");
      console.log("[WS] Disconnected:", reason);
    });

    this.socket.on("connect_error", (error) => {
      this.reconnectAttempts++;
      if (this.reconnectAttempts >= this.maxReconnectAttempts) {
        this.setStatus("error");
      }
      console.error("[WS] Connection error:", error.message);
    });

    // Game events
    this.socket.on("game:output", (data) => this.emit("game:output", data));
    this.socket.on("game:screenshot", (data) => this.emit("game:screenshot", data));
    this.socket.on("game:error", (data) => this.emit("game:error", data));
    this.socket.on("game:stopped", (data) => this.emit("game:stopped", data));

    // Build events
    this.socket.on("build:progress", (data) => this.emit("build:progress", data));
    this.socket.on("build:complete", (data) => this.emit("build:complete", data));
    this.socket.on("build:error", (data) => this.emit("build:error", data));

    // AI events
    this.socket.on("ai:stream", (data) => this.emit("ai:stream", data));
    this.socket.on("ai:complete", (data) => this.emit("ai:complete", data));
    this.socket.on("ai:error", (data) => this.emit("ai:error", data));

    // Asset events
    this.socket.on("asset:generated", (data) => this.emit("asset:generated", data));
    this.socket.on("asset:progress", (data) => this.emit("asset:progress", data));

    // File events
    this.socket.on("file:changed", (data) => this.emit("file:changed", data));
    this.socket.on("file:created", (data) => this.emit("file:created", data));
    this.socket.on("file:deleted", (data) => this.emit("file:deleted", data));
  }

  disconnect(): void {
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
    }
    this.setStatus("disconnected");
  }

  getStatus(): ConnectionStatus {
    return this.status;
  }

  private setStatus(status: ConnectionStatus): void {
    this.status = status;
    this.statusListeners.forEach((handler) => handler(status));
  }

  onStatusChange(handler: StatusHandler): () => void {
    this.statusListeners.add(handler);
    return () => {
      this.statusListeners.delete(handler);
    };
  }

  on(event: string, handler: EventHandler): () => void {
    if (!this.eventHandlers.has(event)) {
      this.eventHandlers.set(event, new Set());
    }
    this.eventHandlers.get(event)!.add(handler);

    return () => {
      this.eventHandlers.get(event)?.delete(handler);
    };
  }

  off(event: string, handler: EventHandler): void {
    this.eventHandlers.get(event)?.delete(handler);
  }

  private emit(event: string, data: unknown): void {
    this.eventHandlers.get(event)?.forEach((handler) => {
      try {
        handler(data);
      } catch (error) {
        console.error(`[WS] Error in handler for ${event}:`, error);
      }
    });
  }

  // Send messages to server
  send(event: string, data: unknown): void {
    if (!this.socket?.connected) {
      console.warn("[WS] Not connected. Message not sent:", event);
      return;
    }
    this.socket.emit(event, data);
  }

  // Game control methods
  runGame(projectId: string): void {
    this.send("game:run", { projectId });
  }

  stopGame(projectId: string): void {
    this.send("game:stop", { projectId });
  }

  sendInput(projectId: string, input: Record<string, unknown>): void {
    this.send("game:input", { projectId, input });
  }

  // Chat methods
  sendChatMessage(
    projectId: string,
    content: string,
    mode: string
  ): void {
    this.send("chat:message", { projectId, content, mode });
  }
}

// Singleton instance
export const ws = new WebSocketManager();

export default ws;
