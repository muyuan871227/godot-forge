import { create } from "zustand";

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

interface ProjectState {
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
  currentProject: null,
  isLoading: false,
  error: null,
  files: [],
  openFiles: [],
  activeFile: null,
  isGameRunning: false,
  gameOutput: [],
  buildStatuses: [],
};

export const useProjectStore = create<ProjectState>((set, get) => ({
  ...initialState,

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
