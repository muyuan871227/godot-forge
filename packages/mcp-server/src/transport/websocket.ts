import WebSocket from "ws";

export interface GodotConnectionOptions {
  host?: string;
  port: number;
  reconnect?: boolean;
  maxRetries?: number;
}

export class GodotConnection {
  private ws: WebSocket | null = null;
  private options: Required<GodotConnectionOptions>;
  private retryCount = 0;
  private pendingRequests = new Map<number, {
    resolve: (value: any) => void;
    reject: (reason: any) => void;
    timeout: NodeJS.Timeout;
  }>();
  private requestId = 0;
  private connected = false;

  constructor(options: GodotConnectionOptions) {
    this.options = {
      host: options.host || "127.0.0.1",
      port: options.port,
      reconnect: options.reconnect ?? true,
      maxRetries: options.maxRetries ?? 10,
    };
  }

  async connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      const url = `ws://${this.options.host}:${this.options.port}`;
      this.ws = new WebSocket(url);

      this.ws.on("open", () => {
        this.connected = true;
        this.retryCount = 0;
        console.error(`Connected to Godot at ${url}`);
        resolve();
      });

      this.ws.on("message", (data) => {
        try {
          const msg = JSON.parse(data.toString());
          if (msg.id && this.pendingRequests.has(msg.id)) {
            const pending = this.pendingRequests.get(msg.id)!;
            clearTimeout(pending.timeout);
            this.pendingRequests.delete(msg.id);
            if (msg.error) {
              pending.reject(new Error(msg.error.message || "Godot error"));
            } else {
              pending.resolve(msg.result);
            }
          }
        } catch (e) {
          console.error("Failed to parse Godot message:", e);
        }
      });

      this.ws.on("close", () => {
        this.connected = false;
        if (this.options.reconnect && this.retryCount < this.options.maxRetries) {
          const delay = Math.min(1000 * Math.pow(2, this.retryCount), 60000);
          this.retryCount++;
          console.error(`Reconnecting in ${delay}ms (attempt ${this.retryCount})...`);
          setTimeout(() => this.connect().catch(() => {}), delay);
        }
      });

      this.ws.on("error", (err) => {
        if (!this.connected) reject(err);
      });
    });
  }

  async send(method: string, params: Record<string, any> = {}): Promise<any> {
    if (!this.ws || !this.connected) {
      await this.connect();
    }

    return new Promise((resolve, reject) => {
      const id = ++this.requestId;
      const timeout = setTimeout(() => {
        this.pendingRequests.delete(id);
        reject(new Error(`Request ${method} timed out`));
      }, 30000);

      this.pendingRequests.set(id, { resolve, reject, timeout });

      const message = JSON.stringify({
        jsonrpc: "2.0",
        id,
        method,
        params,
      });

      this.ws!.send(message);
    });
  }

  get isConnected(): boolean {
    return this.connected;
  }

  disconnect(): void {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
      this.connected = false;
    }
  }
}
