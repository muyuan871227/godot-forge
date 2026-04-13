const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:3001";

interface RequestOptions extends Omit<RequestInit, "body"> {
  body?: unknown;
  params?: Record<string, string>;
}

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

  private getHeaders(): Record<string, string> {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };
    if (this.authToken) {
      headers["Authorization"] = `Bearer ${this.authToken}`;
    }
    return headers;
  }

  private async handleResponse<T>(response: Response): Promise<T> {
    if (!response.ok) {
      const errorBody = await response.text();
      let details: unknown;
      try {
        details = JSON.parse(errorBody);
      } catch {
        details = errorBody;
      }

      const error: ApiError = {
        message: `API request failed with status ${response.status}`,
        status: response.status,
        details,
      };
      throw error;
    }

    if (response.status === 204) {
      return undefined as T;
    }

    return response.json();
  }

  async get<T>(path: string, params?: Record<string, string>): Promise<T> {
    const url = this.buildUrl(path, params);
    const response = await fetch(url, {
      method: "GET",
      headers: this.getHeaders(),
    });
    return this.handleResponse<T>(response);
  }

  async post<T>(path: string, body?: unknown): Promise<T> {
    const url = this.buildUrl(path);
    const response = await fetch(url, {
      method: "POST",
      headers: this.getHeaders(),
      body: body ? JSON.stringify(body) : undefined,
    });
    return this.handleResponse<T>(response);
  }

  async put<T>(path: string, body?: unknown): Promise<T> {
    const url = this.buildUrl(path);
    const response = await fetch(url, {
      method: "PUT",
      headers: this.getHeaders(),
      body: body ? JSON.stringify(body) : undefined,
    });
    return this.handleResponse<T>(response);
  }

  async patch<T>(path: string, body?: unknown): Promise<T> {
    const url = this.buildUrl(path);
    const response = await fetch(url, {
      method: "PATCH",
      headers: this.getHeaders(),
      body: body ? JSON.stringify(body) : undefined,
    });
    return this.handleResponse<T>(response);
  }

  async delete<T>(path: string): Promise<T> {
    const url = this.buildUrl(path);
    const response = await fetch(url, {
      method: "DELETE",
      headers: this.getHeaders(),
    });
    return this.handleResponse<T>(response);
  }

  async upload<T>(path: string, formData: FormData): Promise<T> {
    const url = this.buildUrl(path);
    const headers: Record<string, string> = {};
    if (this.authToken) {
      headers["Authorization"] = `Bearer ${this.authToken}`;
    }
    // Do not set Content-Type - let browser set it with boundary
    const response = await fetch(url, {
      method: "POST",
      headers,
      body: formData,
    });
    return this.handleResponse<T>(response);
  }
}

// Singleton API client instance
export const api = new ApiClient(BASE_URL);

// ---- Typed API Methods ----

export interface Project {
  id: string;
  name: string;
  description: string;
  template: string;
  godotVersion: string;
  createdAt: string;
  updatedAt: string;
  status: "active" | "building" | "archived";
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  mode: string;
  timestamp: string;
  files?: { name: string; content: string; language: string }[];
}

export interface Asset {
  id: string;
  name: string;
  type: string;
  path: string;
  size: number;
  metadata: Record<string, unknown>;
  createdAt: string;
}

export interface BuildConfig {
  projectId: string;
  platforms: string[];
  mode: "debug" | "release";
}

export interface BuildResult {
  id: string;
  platform: string;
  status: "pending" | "building" | "success" | "error";
  outputPath?: string;
  error?: string;
}

// Project endpoints
export const projectApi = {
  list: () => api.get<Project[]>("/api/projects"),
  get: (id: string) => api.get<Project>(`/api/projects/${id}`),
  create: (data: Partial<Project>) => api.post<Project>("/api/projects", data),
  update: (id: string, data: Partial<Project>) =>
    api.patch<Project>(`/api/projects/${id}`, data),
  delete: (id: string) => api.delete(`/api/projects/${id}`),
};

// Chat endpoints
export const chatApi = {
  send: (projectId: string, message: { content: string; mode: string }) =>
    api.post<ChatMessage>(`/api/projects/${projectId}/chat`, message),
  history: (projectId: string) =>
    api.get<ChatMessage[]>(`/api/projects/${projectId}/chat`),
};

// Asset endpoints
export const assetApi = {
  list: (projectId: string) =>
    api.get<Asset[]>(`/api/projects/${projectId}/assets`),
  generate: (
    projectId: string,
    data: { type: string; prompt: string; options?: Record<string, unknown> }
  ) => api.post<Asset>(`/api/projects/${projectId}/assets/generate`, data),
  upload: (projectId: string, formData: FormData) =>
    api.upload<Asset>(`/api/projects/${projectId}/assets/upload`, formData),
  delete: (projectId: string, assetId: string) =>
    api.delete(`/api/projects/${projectId}/assets/${assetId}`),
};

// Build endpoints
export const buildApi = {
  start: (config: BuildConfig) =>
    api.post<BuildResult[]>("/api/build", config),
  status: (buildId: string) =>
    api.get<BuildResult>(`/api/build/${buildId}`),
  download: (buildId: string) =>
    `${BASE_URL}/api/build/${buildId}/download`,
};

export default api;
