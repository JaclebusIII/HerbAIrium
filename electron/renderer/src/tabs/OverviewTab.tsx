import { useState } from "react";
import { batchProcessStream } from "../api";
import { useApp } from "../context/AppContext";

interface Summary {
  ocr_ok: number;
  ocr_fail: number;
  llm_ok: number;
  llm_fail: number;
}

export function OverviewTab() {
  const { imageFiles, config } = useApp();
  const [running, setRunning] = useState(false);
  const [progress, setProgress] = useState(0);
  const [statusLine, setStatusLine] = useState("");
  const [summary, setSummary] = useState<Summary | null>(null);

  async function handleBatch() {
    if (!config?.deepinfra_api_key) {
      setStatusLine("Add API key in Configuration, then try again.");
      return;
    }
    setRunning(true);
    setProgress(0);
    setStatusLine("");
    setSummary(null);

    try {
      let ocrDone = 0, ocrTotal = imageFiles.length;
      let llmDone = 0, llmTotal = 0;

      for await (const event of batchProcessStream()) {
        if (event.stage === "done") {
          setSummary({
            ocr_ok: event.ocr_ok ?? 0,
            ocr_fail: event.ocr_fail ?? 0,
            llm_ok: event.llm_ok ?? 0,
            llm_fail: event.llm_fail ?? 0,
          });
          setProgress(1);
          setStatusLine("Done.");
        } else if (event.stage === "ocr") {
          ocrDone = event.current ?? ocrDone;
          ocrTotal = event.total ?? ocrTotal;
          setProgress(ocrDone / (ocrTotal * 2));
          setStatusLine(`OCR ${ocrDone}/${ocrTotal}: ${event.filename ?? ""}`);
        } else if (event.stage === "llm") {
          llmDone = event.current ?? llmDone;
          llmTotal = event.total ?? llmTotal;
          setProgress(0.5 + (llmTotal > 0 ? llmDone / (llmTotal * 2) : 0));
          setStatusLine(`LLM ${llmDone}/${llmTotal}: ${event.filename ?? ""}`);
        }
      }
    } catch (err) {
      setStatusLine(err instanceof Error ? err.message : String(err));
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="p-4">
      <h2 className="text-xl font-semibold mb-4">Overview</h2>
      <p className="text-sm text-gray-600 mb-4">
        {imageFiles.length} image{imageFiles.length !== 1 ? "s" : ""} in workspace.
      </p>

      <button
        className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700 disabled:opacity-50"
        onClick={handleBatch}
        disabled={running || imageFiles.length === 0}
      >
        {running ? "Processing…" : "Parse all images (OCR + LLM)"}
      </button>

      {running && (
        <div className="mt-4">
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className="bg-green-600 h-2 rounded-full transition-all"
              style={{ width: `${Math.round(progress * 100)}%` }}
            />
          </div>
          <p className="text-sm text-gray-600 mt-1">{statusLine}</p>
        </div>
      )}

      {!running && statusLine && <p className="mt-3 text-sm text-gray-600">{statusLine}</p>}

      {summary && (
        <div className="mt-4 bg-gray-50 border rounded-lg p-4 text-sm space-y-1">
          <p>
            <span className="font-medium">OCR:</span> {summary.ocr_ok} ok, {summary.ocr_fail} failed
          </p>
          <p>
            <span className="font-medium">LLM:</span> {summary.llm_ok} ok, {summary.llm_fail} failed
          </p>
        </div>
      )}
    </div>
  );
}
