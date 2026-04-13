const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8100";

interface ApiError {
  message: string;
  status: number;
  details?: unknown;
}

class ApiClient {
  private baseUrl: string;
  private authToken: string | null = null;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  setAuthToken(token: string | null) {
    this.authToken = token;
    if (typeof window !== "undefined") {
      if (token) localStorage.setItem("auth_token", token);
      else localStorage.removeItem("auth_token");
    }
  }

  getAuthToken(): string | null {
    if (!this.authToken && typeof window !== "undefined") {
      this.authToken = localStorage.getItem("auth_token");
    }
    return this.authToken;
  }

  private buildUrl(path: string, params?: Record<string, string>): string {
    const url = new URL(path, this.baseUrl);
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        url.searchParams.set(key, value);
      });
    }
    return url.toString();
  }

  private getHeaders(json = true): Record<string, string> {
    const headers: Record<string, string> = {};
    if (json) headers["Content-Type"] = "application/json";
    const token = this.getAuthToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;
    return headers;
  }

  private async handleResponse<T>(response: Response): Promise<T> {
    if (!response.ok) {
      const errorBody = await response.text();
      let details: unknown;
      try { details = JSON.parse(errorBody); } catch { details = errorBody; }
      const error: ApiError = {
        message: `API request failed with status ${response.status}`,
        status: response.status,
        details,
      };
      throw error;
    }
    if (response.status === 204) return undefined as T;
    return response.json();
  }

  async get<T>(path: string, params?: Record<string, string>): Promise<T> {
    const response = await fetch(this.buildUrl(path, params), {
      method: "GET", headers: this.getHeaders(),
    });
    return this.handleResponse<T>(response);
  }

  async post<T>(path: string, body?: unknown, timeoutMs = 120000): Promise<T> {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    try {
      const response = await fetch(this.buildUrl(path), {
        method: "POST", headers: this.getHeaders(),
        body: body ? JSON.stringify(body) : undefined,
        signal: controller.signal,
      });
      return this.handleResponse<T>(response);
    } finally {
      clearTimeout(timer);
    }
  }

  async put<T>(path: string, body?: unknown): Promise<T> {
    const response = await fetch(this.buildUrl(path), {
      method: "PUT", headers: this.getHeaders(),
      body: body ? JSON.stringify(body) : undefined,
    });
    return this.handleResponse<T>(response);
  }

  async delete<T>(path: string): Promise<T> {
    const response = await fetch(this.buildUrl(path), {
      method: "DELETE", headers: this.getHeaders(),
    });
    return this.handleResponse<T>(response);
  }

  async upload<T>(path: string, formData: FormData): Promise<T> {
    const response = await fetch(this.buildUrl(path), {
      method: "POST", headers: this.getHeaders(false), body: formData,
    });
    return this.handleResponse<T>(response);
  }
}

export const api = new ApiClient(BASE_URL);

// ---- Types ----

export interface Project {
  id: string;
  name: string;
  description: string;
  template: string;
  created_at: string;
  path: string;
  status?: "active" | "building" | "archived";
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  mode: string;
  timestamp: string;
  files?: { path: string; content: string }[];
}

export interface Asset {
  id: string;
  name: string;
  type: string;
  path: string;
  size: number;
  metadata: Record<string, unknown>;
}

export interface CodeGenResult {
  code: string;
  explanation: string;
  files: { path: string; content: string }[];
}

export interface BuildResult {
  success: boolean;
  platform: string;
  output_path?: string;
  size_bytes?: number;
  download_url?: string;
  error?: string;
}

// ---- Auth endpoints ----
export const authApi = {
  register: (data: { email: string; username: string; password: string }) =>
    api.post<{ access_token: string; user: unknown }>("/api/v1/users/register", data),
  login: (username: string, password: string) => {
    const formData = new URLSearchParams();
    formData.set("username", username);
    formData.set("password", password);
    return fetch(`${BASE_URL}/api/v1/users/login`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: formData,
    }).then(r => r.json()) as Promise<{ access_token: string; token_type: string }>;
  },
  me: () => api.get<{ id: string; username: string; email: string }>("/api/v1/users/me"),
};

// ---- Project endpoints ----
export const projectApi = {
  list: () => api.get<Project[]>("/api/v1/projects"),
  get: (id: string) => api.get<Project>(`/api/v1/projects/${id}`),
  create: (data: { name: string; template?: string; description?: string }) =>
    api.post<Project>("/api/v1/projects", data),
  delete: (id: string) => api.delete(`/api/v1/projects/${id}`),
  files: (id: string, action: string, path?: string, content?: string) =>
    api.post<unknown>(`/api/v1/projects/${id}/files`, { action, path, content }),
};

// ---- Code generation endpoints ----
export const codegenApi = {
  generate: (prompt: string, context?: {
    scene_tree?: string;
    existing_scripts?: string[];
    godot_version?: string;
  }) => api.post<CodeGenResult>("/api/v1/codegen/generate", {
    prompt,
    godot_version: "4.4",
    ...context,
  }),
  fix: (errors: string[], scriptContent: string) =>
    api.post<CodeGenResult>("/api/v1/codegen/fix", { errors, script_content: scriptContent }),
};

// ---- Image generation endpoints ----
export const imagegenApi = {
  generate: (prompt: string, options?: {
    style?: string; width?: number; height?: number;
    transparent_bg?: boolean; sprite_sheet?: boolean;
  }) => api.post<{ image_base64: string; image_path: string; metadata: unknown }>(
    "/api/v1/imagegen/generate", { prompt, ...options }
  ),
  spriteSheet: (character: string, animations: string[], frameCount?: number) =>
    api.post<unknown>("/api/v1/imagegen/sprite-sheet", {
      character_description: character, animations, frame_count: frameCount ?? 4,
    }),
};

// ---- Audio generation endpoints ----
export const audiogenApi = {
  sfx: (description: string, duration?: number) =>
    api.post<{ audio_base64: string; filename: string }>(
      "/api/v1/audiogen/sfx", { description, duration: duration ?? 1.0, format: "wav" }
    ),
  bgm: (description: string, duration?: number, loop?: boolean) =>
    api.post<{ audio_base64: string; filename: string }>(
      "/api/v1/audiogen/bgm", { description, duration: duration ?? 30, loop: loop ?? true }
    ),
};

// ---- 3D model endpoints ----
export const modelgenApi = {
  generate: (prompt: string, provider?: string) =>
    api.post<{ model_path: string; format: string }>(
      "/api/v1/modelgen/generate", { prompt, provider: provider ?? "hunyuan3d" }
    ),
};

// ---- Build endpoints ----
export const buildApi = {
  export: (projectId: string, platform: string) =>
    api.post<BuildResult>("/api/v1/build/export", {
      project_id: projectId, platform,
    }),
  downloadUrl: (projectId: string, platform: string) =>
    `${BASE_URL}/api/v1/build/download/${projectId}/${platform}`,
};

// ---- Health ----
export const healthApi = {
  check: () => api.get<{ status: string; version: string }>("/health"),
};

export default api;
