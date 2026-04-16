import { useState } from "react";
import { openWorkspace } from "../api";
import { useApp } from "../context/AppContext";
import "../types";

export function WorkspaceView() {
  const { setWorkspaceFolder, setConfig, setImageFiles, setCurrentIndex } = useApp();
  const [pathInput, setPathInput] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleOpen(folderPath: string) {
    if (!folderPath.trim()) {
      setError("Enter a folder path.");
      return;
    }
    setError("");
    setLoading(true);
    try {
      const result = await openWorkspace(folderPath.trim());
      if (result.image_count === 0) {
        setError("No images found in that folder (jpg, png, tif, tiff).");
        return;
      }
      setWorkspaceFolder(result.folder_path);
      setConfig(result.config);
      setImageFiles(result.image_files);
      setCurrentIndex(0);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  async function handleBrowse() {
    const chosen = await window.electronAPI.openFolderDialog();
    if (chosen) {
      setPathInput(chosen);
      await handleOpen(chosen);
    }
  }

  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-50">
      <div className="bg-white rounded-xl shadow-md p-8 w-full max-w-lg">
        <h1 className="text-3xl font-bold mb-2">HerbAIrium</h1>
        <p className="text-gray-600 mb-6">Open a folder of herbarium specimen images.</p>

        <div className="flex gap-2 mb-3">
          <input
            className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-green-500"
            placeholder="/path/to/herbarium/images"
            value={pathInput}
            onChange={(e) => setPathInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleOpen(pathInput)}
          />
          <button
            className="px-4 py-2 bg-gray-100 border border-gray-300 rounded-lg text-sm hover:bg-gray-200"
            onClick={handleBrowse}
          >
            Browse…
          </button>
        </div>

        <button
          className="w-full py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700 disabled:opacity-50"
          onClick={() => handleOpen(pathInput)}
          disabled={loading}
        >
          {loading ? "Opening…" : "Open folder"}
        </button>

        {error && <p className="mt-3 text-red-600 text-sm">{error}</p>}
      </div>
    </div>
  );
}
