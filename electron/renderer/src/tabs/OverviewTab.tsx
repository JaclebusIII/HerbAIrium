import { useApp } from "../context/AppContext";

export function OverviewTab() {
  const {
    imageFiles,
    imageSummaries,
    batchRunning,
    batchProgress,
    batchStatusLine,
    batchSummary,
    startBatch,
  } = useApp();
  const transcribedCount = imageSummaries.filter((image) => image.ocr_complete).length;
  const parsedCount = imageSummaries.filter((image) => image.parse_complete).length;

  return (
    <div className="p-4 overflow-y-auto h-full">
      <h2 className="text-xl font-semibold mb-4">Overview</h2>

      <div className="grid grid-cols-3 gap-3 mb-5">
        <Metric label="Photos" value={imageFiles.length} />
        <Metric label="Transcribed" value={transcribedCount} />
        <Metric label="Parsed" value={parsedCount} />
      </div>

      <button
        className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700 disabled:opacity-50"
        onClick={() => void startBatch()}
        disabled={batchRunning || imageFiles.length === 0}
      >
        {batchRunning ? "Processing..." : "Parse all images (OCR + LLM)"}
      </button>

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
