import React, { createContext, useContext, useState } from "react";
import type { Configuration } from "../types";

interface AppContextValue {
  workspaceFolder: string | null;
  setWorkspaceFolder: (folder: string | null) => void;
  config: Configuration | null;
  setConfig: (config: Configuration | null) => void;
  imageFiles: string[];
  setImageFiles: (files: string[]) => void;
  currentIndex: number;
  setCurrentIndex: (index: number) => void;
}

const AppContext = createContext<AppContextValue | null>(null);

export function AppProvider({ children }: { children: React.ReactNode }) {
  const [workspaceFolder, setWorkspaceFolder] = useState<string | null>(null);
  const [config, setConfig] = useState<Configuration | null>(null);
  const [imageFiles, setImageFiles] = useState<string[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);

  return (
    <AppContext.Provider
      value={{
        workspaceFolder,
        setWorkspaceFolder,
        config,
        setConfig,
        imageFiles,
        setImageFiles,
        currentIndex,
        setCurrentIndex,
      }}
    >
      {children}
    </AppContext.Provider>
  );
}

export function useApp(): AppContextValue {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error("useApp must be used within AppProvider");
  return ctx;
}
