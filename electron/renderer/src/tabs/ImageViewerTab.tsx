import { useEffect, useRef, useState } from "react";
import { getImage, getMetadata, getThumbnail, runOcr, runParse } from "../api";
import { MetadataPanel } from "../components/MetadataPanel";
import { WorkspaceExplorer } from "../components/WorkspaceExplorer";
import { useApp } from "../context/AppContext";
import type { Metadata } from "../types";

const INITIAL_ZOOM = 2;
const MIN_ZOOM = 1.5;
const MAX_ZOOM = 5;
const ZOOM_STEP = 0.5;
const LENS_SIZE = 320;

interface MagnifierPosition {
  left: number;
  top: number;
  imageX: number;
  imageY: number;
  imageWidth: number;
  imageHeight: number;
}

export function ImageViewerTab() {
  const {
    imageFiles,
    imageSummaries,
    setImageSummaries,
    currentIndex,
    setCurrentIndex,
    config,
  } = useApp();
  const total = imageFiles.length;

  const [thumbnailUri, setThumbnailUri] = useState<string | null>(null);
  const [detailImageUri, setDetailImageUri] = useState<string | null>(null);
  const [metadata, setMetadata] = useState<Metadata | null>(null);
  const [busy, setBusy] = useState<"ocr" | "parse" | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const [zoom, setZoom] = useState(INITIAL_ZOOM);
  const [imageHovered, setImageHovered] = useState(false);
  const [magnifierPosition, setMagnifierPosition] = useState<MagnifierPosition | null>(null);
  const toastTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const loadRequestId = useRef(0);
  const imageContainerRef = useRef<HTMLDivElement | null>(null);
  const currentIndexRef = useRef(currentIndex);
  currentIndexRef.current = currentIndex;

  function showToast(msg: string) {
    if (toastTimer.current) clearTimeout(toastTimer.current);
    setToast(msg);
    toastTimer.current = setTimeout(() => setToast(null), 3000);
  }

  useEffect(() => () => { if (toastTimer.current) clearTimeout(toastTimer.current); }, []);

  useEffect(() => {
    if (currentIndex === null) return;
    const requestId = ++loadRequestId.current;
    const controller = new AbortController();
    let objectUrl: string | null = null;
    setThumbnailUri(null);
    setDetailImageUri(null);
    setMetadata(null);
    setZoom(INITIAL_ZOOM);
    setImageHovered(false);
    setMagnifierPosition(null);

    Promise.all([
      getThumbnail(currentIndex),
      getMetadata(currentIndex, controller.signal),
    ])
      .then(([thumbnail, meta]) => {
        if (loadRequestId.current !== requestId) return;
        setThumbnailUri(thumbnail.data_uri);
        setMetadata(meta);
      })
      .catch((err) => {
        if (err instanceof DOMException && err.name === "AbortError") return;
        if (loadRequestId.current === requestId) {
          showToast(err instanceof Error ? err.message : String(err));
        }
      });

    getImage(currentIndex, controller.signal)
      .then((image) => {
        objectUrl = URL.createObjectURL(image);
        if (loadRequestId.current !== requestId) {
          URL.revokeObjectURL(objectUrl);
          return;
        }
        setDetailImageUri(objectUrl);
      })
      .catch((err) => {
        if (err instanceof DOMException && err.name === "AbortError") return;
        if (loadRequestId.current === requestId) {
          showToast(`Detailed image unavailable: ${err instanceof Error ? err.message : String(err)}`);
        }
      });

    return () => {
      controller.abort();
      loadRequestId.current += 1;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [currentIndex]);

  useEffect(() => {
    if (!imageHovered) return;

    function handleZoomKey(event: KeyboardEvent) {
      if (event.key === "+" || event.key === "=") {
        event.preventDefault();
        setZoom((value) => Math.min(MAX_ZOOM, value + ZOOM_STEP));
      } else if (event.key === "-" || event.key === "_") {
        event.preventDefault();
        setZoom((value) => Math.max(MIN_ZOOM, value - ZOOM_STEP));
      }
    }

    window.addEventListener("keydown", handleZoomKey);
    return () => window.removeEventListener("keydown", handleZoomKey);
  }, [imageHovered]);

  function handleImageMouseMove(event: React.MouseEvent<HTMLImageElement>) {
    const container = imageContainerRef.current;
    if (!container) return;

    const imageRect = event.currentTarget.getBoundingClientRect();
    const containerRect = container.getBoundingClientRect();
    const imageX = event.clientX - imageRect.left;
    const imageY = event.clientY - imageRect.top;

    setMagnifierPosition({
      left: imageRect.left - containerRect.left + imageX - LENS_SIZE / 2,
      top: imageRect.top - containerRect.top + imageY - LENS_SIZE / 2,
      imageX,
      imageY,
      imageWidth: imageRect.width,
      imageHeight: imageRect.height,
    });
  }

  function updateSummary(index: number, meta: Metadata) {
    setImageSummaries((images) => images.map((image) => (
      image.index === index
        ? {
            ...image,
            ocr_complete: Boolean(meta.ocr_result),
            parse_complete: Boolean(meta.ai_result),
            status_error: null,
          }
        : image
    )));
  }

  async function handleOcr() {
    if (currentIndex === null) return;
    if (!config?.deepinfra_api_key) {
      showToast("Add API key in Configuration, then try again.");
      return;
    }
    setBusy("ocr");
    const operationIndex = currentIndex;
    try {
      await runOcr(operationIndex);
      const meta = await getMetadata(operationIndex);
      updateSummary(operationIndex, meta);
      if (currentIndexRef.current === operationIndex) {
        setMetadata(meta);
        showToast("OCR complete.");
      }
    } catch (err) {
      if (currentIndexRef.current === operationIndex) {
        showToast(err instanceof Error ? err.message : String(err));
      }
    } finally {
      setBusy(null);
    }
  }

  async function handleParse() {
    if (currentIndex === null) return;
    if (!config?.deepinfra_api_key) {
      showToast("Add API key in Configuration, then try again.");
      return;
    }
    setBusy("parse");
    const operationIndex = currentIndex;
    try {
      const meta = await runParse(operationIndex);
      updateSummary(operationIndex, meta);
      if (currentIndexRef.current === operationIndex) {
        setMetadata(meta);
        showToast("LLM parse complete.");
      }
    } catch (err) {
      if (currentIndexRef.current === operationIndex) {
        showToast(err instanceof Error ? err.message : String(err));
      }
    } finally {
      setBusy(null);
    }
  }

  if (total === 0) return <div className="p-4 text-gray-500">No images in workspace.</div>;
  if (currentIndex === null) {
    return <WorkspaceExplorer images={imageSummaries} onSelect={setCurrentIndex} />;
  }

  const filename = imageFiles[currentIndex]?.split(/[\\/]/).pop() ?? "";
  const imageUri = detailImageUri ?? thumbnailUri;

  return (
    <div className="p-4 overflow-y-auto h-full relative">
      {/* Navigation */}
      <div className="flex items-center gap-2 mb-4">
        <button
          type="button"
          onClick={() => setCurrentIndex(null)}
          className="px-3 py-1 border rounded text-sm hover:bg-gray-100 mr-2"
        >
          Back to images
        </button>
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
        <div className="w-[48%] min-w-[420px] max-w-[700px] shrink-0">
          <div
            ref={imageContainerRef}
            className="relative w-full h-[min(65vh,700px)] min-h-[500px] bg-gray-100 rounded-lg flex items-center justify-center overflow-hidden"
          >
            {imageUri ? (
              <>
                <img
                  src={imageUri}
                  alt={filename}
                  className="block max-w-full max-h-full object-contain cursor-zoom-in"
                  onMouseEnter={() => setImageHovered(true)}
                  onMouseMove={handleImageMouseMove}
                  onMouseLeave={() => {
                    setImageHovered(false);
                    setMagnifierPosition(null);
                  }}
                />
                {imageHovered && magnifierPosition && (
                  <div
                    className="absolute rounded-full border-2 border-white shadow-xl pointer-events-none"
                    style={{
                      width: LENS_SIZE,
                      height: LENS_SIZE,
                      left: magnifierPosition.left,
                      top: magnifierPosition.top,
                      backgroundImage: `url("${imageUri}")`,
                      backgroundRepeat: "no-repeat",
                      backgroundSize: `${magnifierPosition.imageWidth * zoom}px ${magnifierPosition.imageHeight * zoom}px`,
                      backgroundPosition: `${LENS_SIZE / 2 - magnifierPosition.imageX * zoom}px ${LENS_SIZE / 2 - magnifierPosition.imageY * zoom}px`,
                    }}
                  />
                )}
              </>
            ) : (
              <span className="text-gray-400 text-sm">Loading…</span>
            )}
          </div>
          <p className="mt-2 text-xs text-gray-500">
            Hover over the image to magnify. While hovering, press + or - to adjust zoom ({zoom.toFixed(1)}x).
          </p>
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
