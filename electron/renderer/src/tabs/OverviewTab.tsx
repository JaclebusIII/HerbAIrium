import { useState } from "react";
import { clearWorkspaceResults, exportDarwinCore } from "../api";
import { useApp } from "../context/AppContext";

export function OverviewTab() {
  const [exporting, setExporting] = useState(false);
  const [clearing, setClearing] = useState(false);
  const [exportStatus, setExportStatus] = useState("");
  const [clearStatus, setClearStatus] = useState("");
  const {
    imageFiles,
    imageSummaries,
    setImageSummaries,
    setCurrentIndex,
    batchRunning,
    batchProgress,
    batchStatusLine,
    batchSummary,
    startBatch,
    resetBatchState,
  } = useApp();
  const transcribedCount = imageSummaries.filter((image) => image.ocr_complete).length;
  const parsedCount = imageSummaries.filter((image) => image.parse_complete).length;

  async function downloadDarwinCore() {
    setExporting(true);
    setExportStatus("");
    try {
      const blob = await exportDarwinCore();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "darwin-core.csv";
      document.body.appendChild(link);
      link.click();
      link.remove();
      setTimeout(() => URL.revokeObjectURL(url), 0);
      setExportStatus(`Exported ${imageFiles.length} records.`);
    } catch (err) {
      setExportStatus(err instanceof Error ? err.message : String(err));
    } finally {
      setExporting(false);
    }
  }

  async function clearAllResults() {
    const confirmed = window.confirm(
      "Clear all OCR transcriptions and parsed metadata for this workspace? This cannot be undone.",
    );
    if (!confirmed) return;

    setClearing(true);
    setClearStatus("");
    try {
      const result = await clearWorkspaceResults();
      setImageSummaries((images) => images.map((image) => ({
        ...image,
        ocr_complete: false,
        parse_complete: false,
        status_error: null,
      })));
      setCurrentIndex(null);
      resetBatchState();
      setClearStatus(`Cleared OCR and parse data for ${result.cleared} images.`);
    } catch (err) {
      setClearStatus(err instanceof Error ? err.message : String(err));
    } finally {
      setClearing(false);
    }
  }

  return (
    <div className="p-4 overflow-y-auto h-full">
      <h2 className="text-xl font-semibold mb-4">Overview</h2>

      <div className="grid grid-cols-3 gap-3 mb-5">
        <Metric label="Photos" value={imageFiles.length} />
        <Metric label="Transcribed" value={transcribedCount} />
        <Metric label="Parsed" value={parsedCount} />
      </div>

      <div className="flex flex-wrap gap-3">
        <button
          className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700 disabled:opacity-50"
          onClick={() => void startBatch()}
          disabled={batchRunning || imageFiles.length === 0}
        >
          {batchRunning ? "Processing..." : "Parse all images (OCR + LLM)"}
        </button>
        <button
          className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
          onClick={() => void downloadDarwinCore()}
          disabled={batchRunning || exporting || clearing || imageFiles.length === 0}
        >
          {exporting ? "Exporting..." : "Export Darwin Core CSV"}
        </button>
        <button
          className="px-4 py-2 bg-red-600 text-white rounded-lg text-sm font-medium hover:bg-red-700 disabled:opacity-50"
          onClick={() => void clearAllResults()}
          disabled={batchRunning || clearing || exporting || imageFiles.length === 0}
        >
          {clearing ? "Clearing..." : "Clear all OCR and parse data"}
        </button>
      </div>

      {exportStatus && (
        <p className="mt-3 text-sm text-gray-600">{exportStatus}</p>
      )}

      {clearStatus && (
        <p className="mt-3 text-sm text-gray-600">{clearStatus}</p>
      )}

      {batchRunning && (
        <div className="mt-4">
          <div className="relative w-full bg-gray-200 rounded-full h-5 overflow-hidden">
            <div
              className="bg-green-600 h-full rounded-full transition-all"
              style={{ width: `${Math.round(batchProgress * 100)}%` }}
            />
            <span className="absolute inset-0 flex items-center justify-center text-xs font-medium text-gray-900">
              {Math.round(batchProgress * 100)}%
            </span>
          </div>
          <p className="text-sm text-gray-600 mt-1">{batchStatusLine}</p>
        </div>
      )}

      {!batchRunning && batchStatusLine && (
        <p className="mt-3 text-sm text-gray-600">{batchStatusLine}</p>
      )}

      {batchSummary && (
        <div className="mt-4 bg-gray-50 border rounded-lg p-4 text-sm space-y-1">
          <p>
            <span className="font-medium">OCR:</span> {batchSummary.ocr_ok} ok, {batchSummary.ocr_fail} failed
          </p>
          <p>
            <span className="font-medium">LLM:</span> {batchSummary.llm_ok} ok, {batchSummary.llm_fail} failed
          </p>
        </div>
      )}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-lg border bg-gray-50 p-4">
      <p className="text-2xl font-semibold text-gray-900">{value}</p>
      <p className="text-sm text-gray-600">{label}</p>
    </div>
  );
}
