import { useEffect, useMemo, useState } from "react";
import type { ImageSummary } from "../types";

const PAGE_SIZE = 100;

interface WorkspaceExplorerProps {
  images: ImageSummary[];
  onSelect: (index: number) => void;
}

export function WorkspaceExplorer({ images, onSelect }: WorkspaceExplorerProps) {
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(0);
  const filteredImages = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    if (!normalizedQuery) return images;
    return images.filter((image) => image.filename.toLowerCase().includes(normalizedQuery));
  }, [images, query]);
  const pageCount = Math.max(1, Math.ceil(filteredImages.length / PAGE_SIZE));
  const visibleImages = filteredImages.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);

  useEffect(() => {
    setPage(0);
  }, [query]);

  useEffect(() => {
    if (page >= pageCount) setPage(pageCount - 1);
  }, [page, pageCount]);

  return (
    <div className="p-4 h-full flex flex-col">
      <div className="mb-4">
        <h2 className="text-lg font-semibold">Images</h2>
        <p className="text-sm text-gray-500">Select an image to view and process it.</p>
      </div>

      <label className="mb-3">
        <span className="sr-only">Search images by filename</span>
        <input
          type="search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search by filename"
          className="w-full max-w-xl border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-green-500"
        />
      </label>

      <div className="text-xs text-gray-500 mb-2">
        {filteredImages.length} of {images.length} images
      </div>

      <div className="border rounded-lg overflow-y-auto flex-1 min-h-0">
        {filteredImages.length > 0 ? (
          visibleImages.map((image) => (
            <button
              key={image.path}
              type="button"
              onClick={() => onSelect(image.index)}
              className="w-full flex items-center justify-between gap-4 px-4 py-3 text-left border-b last:border-b-0 hover:bg-gray-50 focus:outline-none focus:bg-green-50"
            >
              <span className="text-sm font-medium truncate" title={image.filename}>
                {image.filename}
              </span>
              <StatusBadge image={image} />
            </button>
          ))
        ) : (
          <p className="px-4 py-8 text-center text-sm text-gray-500">
            No filenames match "{query}".
          </p>
        )}
      </div>

      {pageCount > 1 && (
        <div className="flex items-center justify-between mt-3">
          <button
            type="button"
            onClick={() => setPage((current) => current - 1)}
            disabled={page === 0}
            className="px-3 py-1 border rounded text-sm disabled:opacity-30 hover:bg-gray-100"
          >
            Previous
          </button>
          <span className="text-xs text-gray-500">
            Page {page + 1} of {pageCount}
          </span>
          <button
            type="button"
            onClick={() => setPage((current) => current + 1)}
            disabled={page === pageCount - 1}
            className="px-3 py-1 border rounded text-sm disabled:opacity-30 hover:bg-gray-100"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}

function StatusBadge({ image }: { image: ImageSummary }) {
  if (image.status_error) {
    return (
      <span
        className="shrink-0 text-xs px-2 py-1 rounded-full bg-red-100 text-red-700"
        title={image.status_error}
      >
        Metadata error
      </span>
    );
  }
  if (image.parse_complete) {
    return <span className="shrink-0 text-xs px-2 py-1 rounded-full bg-green-100 text-green-700">Parsed</span>;
  }
  if (image.ocr_complete) {
    return <span className="shrink-0 text-xs px-2 py-1 rounded-full bg-blue-100 text-blue-700">OCR complete</span>;
  }
  return <span className="shrink-0 text-xs px-2 py-1 rounded-full bg-gray-100 text-gray-600">Not started</span>;
}
