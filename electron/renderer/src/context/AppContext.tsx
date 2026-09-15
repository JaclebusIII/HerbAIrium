import React, { createContext, useContext, useRef, useState } from "react";
import { batchProcessStream } from "../api";
import type { BatchSummary, Configuration, ImageSummary } from "../types";

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
  batchRunning: boolean;
  batchProgress: number;
  batchWaiting: boolean;
  batchStatusLine: string;
  batchSummary: BatchSummary | null;
  startBatch: (mode?: "realtime" | "provider") => Promise<void>;
  cancelBatch: () => void;
  resetBatchState: () => void;
}

const AppContext = createContext<AppContextValue | null>(null);

export function AppProvider({ children }: { children: React.ReactNode }) {
  const [workspaceFolder, setWorkspaceFolder] = useState<string | null>(null);
  const [config, setConfig] = useState<Configuration | null>(null);
  const [imageFiles, setImageFiles] = useState<string[]>([]);
  const [imageSummaries, setImageSummaries] = useState<ImageSummary[]>([]);
  const [currentIndex, setCurrentIndex] = useState<number | null>(null);
  const [batchRunning, setBatchRunning] = useState(false);
  const [batchProgress, setBatchProgress] = useState(0);
  const [batchWaiting, setBatchWaiting] = useState(false);
  const [batchStatusLine, setBatchStatusLine] = useState("");
  const [batchSummary, setBatchSummary] = useState<BatchSummary | null>(null);
  const batchControllerRef = useRef<AbortController | null>(null);
  const batchRunIdRef = useRef(0);

  function updateImageSummary(
    filename: string,
    update: Partial<Pick<ImageSummary, "ocr_complete" | "parse_complete" | "status_error">>,
  ) {
    setImageSummaries((images) => images.map((image) => (
      image.filename === filename ? { ...image, ...update } : image
    )));
  }

  function cancelBatch() {
    batchRunIdRef.current += 1;
    batchControllerRef.current?.abort();
    batchControllerRef.current = null;
    setBatchRunning(false);
    setBatchWaiting(false);
    setBatchStatusLine("Batch cancelled.");
  }

  function resetBatchState() {
    batchRunIdRef.current += 1;
    batchControllerRef.current?.abort();
    batchControllerRef.current = null;
    setBatchRunning(false);
    setBatchProgress(0);
    setBatchWaiting(false);
    setBatchStatusLine("");
    setBatchSummary(null);
  }

  async function startBatch(mode: "realtime" | "provider" = "realtime") {
    if (batchRunning) return;
    if (!config?.deepinfra_api_key) {
      setBatchStatusLine("Add API key in Configuration, then try again.");
      return;
    }
    if (imageFiles.length === 0) return;

    const runId = ++batchRunIdRef.current;
    const controller = new AbortController();
    batchControllerRef.current = controller;
    setBatchRunning(true);
    setBatchProgress(0);
    setBatchWaiting(mode === "provider");
    setBatchStatusLine(
      mode === "realtime"
        ? "Starting fast processing..."
        : "Starting economy batch...",
    );
    setBatchSummary(null);

    const activeFiles: Record<"ocr" | "llm", string[]> = { ocr: [], llm: [] };

    try {
      for await (const event of batchProcessStream(mode, controller.signal)) {
        if (batchRunIdRef.current !== runId) return;

        if (event.stage === "done") {
          setBatchSummary({
            ocr_ok: event.ocr_ok ?? 0,
            ocr_fail: event.ocr_fail ?? 0,
            ocr_skipped: event.ocr_skipped ?? 0,
            llm_ok: event.llm_ok ?? 0,
            llm_fail: event.llm_fail ?? 0,
            llm_skipped: event.llm_skipped ?? 0,
            llm_blocked: event.llm_blocked ?? 0,
            metadata_fail: event.metadata_fail ?? 0,
            elapsed_seconds: event.elapsed_seconds ?? 0,
            ocr_elapsed_seconds: event.ocr_elapsed_seconds ?? 0,
            llm_elapsed_seconds: event.llm_elapsed_seconds ?? 0,
            ocr_throughput: event.ocr_throughput ?? 0,
            llm_throughput: event.llm_throughput ?? 0,
          });
          setBatchProgress(1);
          setBatchWaiting(false);
          setBatchStatusLine("Done.");
          continue;
        }

        const stage = event.stage;
        const stageLabel = stage === "ocr" ? "OCR" : "LLM parse";
        const filename = event.filename ?? "";

        if (event.status === "running") {
          if (filename) {
            activeFiles[stage] = [
              ...activeFiles[stage].filter((name) => name !== filename),
              filename,
            ];
          }
          const completedOperations = event.completed_operations ?? 0;
          const totalOperations = event.total_operations ?? 0;
          setBatchProgress(
            totalOperations > 0 ? completedOperations / totalOperations : 0,
          );
          setBatchWaiting(mode === "provider" && completedOperations === 0);
          setBatchStatusLine(
            event.message ?? `Running ${stageLabel}: ${filename}`,
          );
          continue;
        }

        activeFiles[stage] = activeFiles[stage].filter((name) => name !== filename);
        const current = event.current ?? 0;
        const total = event.total ?? 0;
        const completedOperations = event.completed_operations ?? 0;
        const totalOperations = event.total_operations ?? 0;
        setBatchProgress(totalOperations > 0 ? completedOperations / totalOperations : 1);
        setBatchWaiting(false);

        if (filename && event.status === "ok") {
          updateImageSummary(filename, stage === "ocr"
            ? { ocr_complete: true, status_error: null }
            : { ocr_complete: true, parse_complete: true, status_error: null });
        } else if (filename && event.status === "error") {
          updateImageSummary(filename, { status_error: event.error ?? `${stageLabel} failed.` });
        }

        const activeFilename = activeFiles[stage][activeFiles[stage].length - 1];
        const elapsedSeconds = Math.floor(event.elapsed_seconds ?? 0);
        setBatchStatusLine(activeFilename
          ? `Running ${stageLabel}: ${activeFilename} (${current}/${total} complete; ${elapsedSeconds}s)`
          : `${stageLabel}: ${current}/${total} complete; ${elapsedSeconds}s`);
      }
    } catch (err) {
      if (batchRunIdRef.current !== runId) return;
      if (err instanceof DOMException && err.name === "AbortError") {
        setBatchStatusLine("Batch cancelled.");
      } else {
        setBatchStatusLine(err instanceof Error ? err.message : String(err));
      }
    } finally {
      if (batchRunIdRef.current === runId) {
        batchControllerRef.current = null;
        setBatchRunning(false);
        setBatchWaiting(false);
      }
    }
  }

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
        batchRunning,
        batchProgress,
        batchWaiting,
        batchStatusLine,
        batchSummary,
        startBatch,
        cancelBatch,
        resetBatchState,
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
