import React, { createContext, useContext, useState } from "react";
import type { Configuration, ImageSummary } from "../types";

interface AppContextValue {
  workspaceFolder: string | null;
  setWorkspaceFolder: React.Dispatch<React.SetStateAction<string | null>>;
  config: Configuration | null;
  setConfig: React.Dispatch<React.SetStateAction<Configuration | null>>;
  imageFiles: string[];
  setImageFiles: React.Dispatch<React.SetStateAction<string[]>>;
  imageSummaries: ImageSummary[];
  setImageSummaries: React.Dispatch<React.SetStateAction<ImageSummary[]>>;
  currentIndex: number | null;
  setCurrentIndex: React.Dispatch<React.SetStateAction<number | null>>;
}

const AppContext = createContext<AppContextValue | null>(null);

export function AppProvider({ children }: { children: React.ReactNode }) {
  const [workspaceFolder, setWorkspaceFolder] = useState<string | null>(null);
  const [config, setConfig] = useState<Configuration | null>(null);
  const [imageFiles, setImageFiles] = useState<string[]>([]);
  const [imageSummaries, setImageSummaries] = useState<ImageSummary[]>([]);
  const [currentIndex, setCurrentIndex] = useState<number | null>(null);

  return (
    <AppContext.Provider
      value={{
        workspaceFolder,
        setWorkspaceFolder,
        config,
        setConfig,
        imageFiles,
        setImageFiles,
        imageSummaries,
        setImageSummaries,
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
