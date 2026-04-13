import { create } from "zustand";
import { projectApi, type Project } from "@/lib/api";
import { ensureAuth } from "@/lib/auth";

export interface ProjectFile {
  path: string;
  name: string;
  type: "file" | "folder";
  content?: string;
  children?: ProjectFile[];
  modified?: boolean;
}

export interface ProjectInfo {
  id: string;
  name: string;
  description: string;
  template: string;
  godotVersion: string;
  status: "active" | "building" | "archived";
  createdAt: string;
  updatedAt: string;
}

export interface BuildStatus {
  platform: string;
  status: "idle" | "building" | "success" | "error";
  progress?: number;
  outputPath?: string;
  error?: string;
}

function apiProjectToInfo(p: Project): ProjectInfo {
  return {
    id: p.id,
    name: p.name,
    description: p.description,
    template: p.template,
    godotVersion: "4.4",
    status: p.status ?? "active",
    createdAt: p.created_at,
    updatedAt: p.created_at,
  };
}

interface ProjectState {
  // Project list
  projects: ProjectInfo[];
  projectsLoading: boolean;
  projectsError: string | null;

  // Current project
  currentProject: ProjectInfo | null;
  isLoading: boolean;
  error: string | null;

  // File tree
  files: ProjectFile[];
  openFiles: string[];
  activeFile: string | null;

  // Game preview
  isGameRunning: boolean;
  gameOutput: string[];

  // Build
  buildStatuses: BuildStatus[];

  // Async actions
  fetchProjects: () => Promise<void>;
  fetchProject: (id: string) => Promise<void>;
  createProject: (data: { name: string; template?: string; description?: string }) => Promise<ProjectInfo>;
  deleteProject: (id: string) => Promise<void>;

  // Actions
  setProject: (project: ProjectInfo | null) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;

  setFiles: (files: ProjectFile[]) => void;
  openFile: (path: string) => void;
  closeFile: (path: string) => void;
  setActiveFile: (path: string | null) => void;
  updateFileContent: (path: string, content: string) => void;

  setGameRunning: (running: boolean) => void;
  addGameOutput: (line: string) => void;
  clearGameOutput: () => void;

  setBuildStatuses: (statuses: BuildStatus[]) => void;
  updateBuildStatus: (platform: string, status: Partial<BuildStatus>) => void;

  reset: () => void;
}

const initialState = {
  projects: [] as ProjectInfo[],
  projectsLoading: false,
  projectsError: null as string | null,
  currentProject: null as ProjectInfo | null,
  isLoading: false,
  error: null as string | null,
  files: [] as ProjectFile[],
  openFiles: [] as string[],
  activeFile: null as string | null,
  isGameRunning: false,
  gameOutput: [] as string[],
  buildStatuses: [] as BuildStatus[],
};

export const useProjectStore = create<ProjectState>((set, get) => ({
  ...initialState,

  // Async actions
  fetchProjects: async () => {
    set({ projectsLoading: true, projectsError: null });
    try {
      await ensureAuth();
      const data = await projectApi.list();
      const list = Array.isArray(data) ? data : (data as any).projects ?? [];
      set({ projects: list.map(apiProjectToInfo), projectsLoading: false });
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to load projects";
      set({ projectsError: message, projectsLoading: false });
    }
  },

  fetchProject: async (id: string) => {
    set({ isLoading: true, error: null });
    try {
      await ensureAuth();
      const data = await projectApi.get(id);
      set({ currentProject: apiProjectToInfo(data), isLoading: false });
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to load project";
      set({ error: message, isLoading: false });
    }
  },

  createProject: async (data) => {
    set({ projectsLoading: true, projectsError: null });
    try {
      await ensureAuth();
      const created = await projectApi.create(data);
      const info = apiProjectToInfo(created);
      set((state) => ({
        projects: [...state.projects, info],
        projectsLoading: false,
      }));
      return info;
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to create project";
      set({ projectsError: message, projectsLoading: false });
      throw new Error(message);
    }
  },

  deleteProject: async (id: string) => {
    try {
      await projectApi.delete(id);
      set((state) => ({
        projects: state.projects.filter((p) => p.id !== id),
      }));
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to delete project";
      set({ projectsError: message });
      throw new Error(message);
    }
  },

  setProject: (project) => set({ currentProject: project, error: null }),
  setLoading: (isLoading) => set({ isLoading }),
  setError: (error) => set({ error }),

  setFiles: (files) => set({ files }),

  openFile: (path) => {
    const { openFiles } = get();
    if (!openFiles.includes(path)) {
      set({ openFiles: [...openFiles, path], activeFile: path });
    } else {
      set({ activeFile: path });
    }
  },

  closeFile: (path) => {
    const { openFiles, activeFile } = get();
    const updated = openFiles.filter((f) => f !== path);
    const newActive =
      activeFile === path
        ? updated.length > 0
          ? updated[updated.length - 1]
          : null
        : activeFile;
    set({ openFiles: updated, activeFile: newActive });
  },

  setActiveFile: (activeFile) => set({ activeFile }),

  updateFileContent: (path, content) => {
    const updateInTree = (files: ProjectFile[]): ProjectFile[] =>
      files.map((f) => {
        if (f.path === path) {
          return { ...f, content, modified: true };
        }
        if (f.children) {
          return { ...f, children: updateInTree(f.children) };
        }
        return f;
      });

    set((state) => ({ files: updateInTree(state.files) }));
  },

  setGameRunning: (isGameRunning) => set({ isGameRunning }),
  addGameOutput: (line) =>
    set((state) => ({ gameOutput: [...state.gameOutput, line] })),
  clearGameOutput: () => set({ gameOutput: [] }),

  setBuildStatuses: (buildStatuses) => set({ buildStatuses }),
  updateBuildStatus: (platform, status) =>
    set((state) => ({
      buildStatuses: state.buildStatuses.map((b) =>
        b.platform === platform ? { ...b, ...status } : b
      ),
    })),

  reset: () => set(initialState),
}));

export default useProjectStore;
