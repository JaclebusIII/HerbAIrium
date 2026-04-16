import { useEffect, useRef, useState } from "react";
import { getMetadata, getThumbnail, runOcr, runParse } from "../api";
import { MetadataPanel } from "../components/MetadataPanel";
import { useApp } from "../context/AppContext";
import type { Metadata } from "../types";

export function ImageViewerTab() {
  const { imageFiles, currentIndex, setCurrentIndex, config } = useApp();
  const total = imageFiles.length;

  const [thumbnailUri, setThumbnailUri] = useState<string | null>(null);
  const [metadata, setMetadata] = useState<Metadata | null>(null);
  const [busy, setBusy] = useState<"ocr" | "parse" | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const toastTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  function showToast(msg: string) {
    if (toastTimer.current) clearTimeout(toastTimer.current);
    setToast(msg);
    toastTimer.current = setTimeout(() => setToast(null), 3000);
  }

  useEffect(() => () => { if (toastTimer.current) clearTimeout(toastTimer.current); }, []);

  async function load(index: number) {
    setThumbnailUri(null);
    setMetadata(null);
    try {
      const [thumb, meta] = await Promise.all([getThumbnail(index), getMetadata(index)]);
      setThumbnailUri(thumb.data_uri);
      setMetadata(meta);
    } catch (err) {
      showToast(err instanceof Error ? err.message : String(err));
    }
  }

  useEffect(() => {
    load(currentIndex);
  }, [currentIndex]);

  async function handleOcr() {
    if (!config?.deepinfra_api_key) {
      showToast("Add API key in Configuration, then try again.");
      return;
    }
    setBusy("ocr");
    try {
      await runOcr(currentIndex);
      const meta = await getMetadata(currentIndex);
      setMetadata(meta);
      showToast("OCR complete.");
    } catch (err) {
      showToast(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(null);
    }
  }

  async function handleParse() {
    if (!config?.deepinfra_api_key) {
      showToast("Add API key in Configuration, then try again.");
      return;
    }
    setBusy("parse");
    try {
      const meta = await runParse(currentIndex);
      setMetadata(meta);
      showToast("LLM parse complete.");
    } catch (err) {
      showToast(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(null);
    }
  }

  if (total === 0) return <div className="p-4 text-gray-500">No images in workspace.</div>;

  const filename = imageFiles[currentIndex]?.split(/[\\/]/).pop() ?? "";

  return (
    <div className="p-4 overflow-y-auto h-full relative">
      {/* Navigation */}
      <div className="flex items-center gap-2 mb-4">
        <NavButton onClick={() => setCurrentIndex(0)} disabled={currentIndex === 0}>⏮</NavButton>
        <NavButton onClick={() => setCurrentIndex(currentIndex - 1)} disabled={currentIndex === 0}>‹</NavButton>
        <span className="text-sm text-gray-600 mx-2">
          {currentIndex + 1} / {total}
        </span>
        <NavButton onClick={() => setCurrentIndex(currentIndex + 1)} disabled={currentIndex === total - 1}>›</NavButton>
        <NavButton onClick={() => setCurrentIndex(total - 1)} disabled={currentIndex === total - 1}>⏭</NavButton>
        <span className="text-sm text-gray-400 ml-2">{filename}</span>
      </div>

      <div className="flex gap-6">
        {/* Image */}
        <div className="shrink-0">
          <div className="w-[400px] h-[400px] bg-gray-100 rounded-lg flex items-center justify-center overflow-hidden">
            {thumbnailUri ? (
              <img src={thumbnailUri} alt={filename} className="max-w-full max-h-full object-contain" />
            ) : (
              <span className="text-gray-400 text-sm">Loading…</span>
            )}
          </div>
          <div className="flex gap-2 mt-3">
            <ActionButton onClick={handleOcr} disabled={busy !== null} loading={busy === "ocr"}>
              Run OCR
            </ActionButton>
            <ActionButton onClick={handleParse} disabled={busy !== null || !metadata?.ocr_result} loading={busy === "parse"}>
              Parse with LLM
            </ActionButton>
          </div>
        </div>

        {/* Metadata */}
        <div className="flex-1 min-w-0">
          <h3 className="font-semibold text-sm mb-2">Metadata</h3>
          <MetadataPanel metadata={metadata} />

          {metadata?.ocr_result && (
            <details className="mt-4">
              <summary className="text-sm font-medium text-gray-600 cursor-pointer">OCR transcription</summary>
              <pre className="mt-2 text-xs bg-gray-50 border rounded p-2 whitespace-pre-wrap">{metadata.ocr_result}</pre>
            </details>
          )}

          {metadata?.ai_result && (
            <details className="mt-2">
              <summary className="text-sm font-medium text-gray-600 cursor-pointer">Raw LLM result</summary>
              <pre className="mt-2 text-xs bg-gray-50 border rounded p-2 whitespace-pre-wrap">{metadata.ai_result}</pre>
            </details>
          )}
        </div>
      </div>

      {/* Toast */}
      {toast && (
        <div className="fixed bottom-4 left-1/2 -translate-x-1/2 bg-gray-800 text-white text-sm px-4 py-2 rounded-lg shadow-lg">
          {toast}
        </div>
      )}
    </div>
  );
}

function NavButton({ children, onClick, disabled }: { children: React.ReactNode; onClick: () => void; disabled: boolean }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className="px-3 py-1 border rounded text-sm disabled:opacity-30 hover:bg-gray-100"
    >
      {children}
    </button>
  );
}

function ActionButton({ children, onClick, disabled, loading }: {
  children: React.ReactNode;
  onClick: () => void;
  disabled: boolean;
  loading: boolean;
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700 disabled:opacity-50"
    >
      {loading ? "Running…" : children}
    </button>
  );
}
