import { useState } from "react";
import { useApp } from "../context/AppContext";
import { OverviewTab } from "../tabs/OverviewTab";
import { ImageViewerTab } from "../tabs/ImageViewerTab";
import { ConfigTab } from "../tabs/ConfigTab";

const TABS = ["Overview", "Image viewer", "Configuration"] as const;

export function MainView({ onChangeWorkspace }: { onChangeWorkspace: () => void }) {
  const { workspaceFolder, imageFiles } = useApp();
  const [activeTab, setActiveTab] = useState(0);

  const folderName = workspaceFolder?.split(/[\\/]/).pop() ?? "";

  return (
    <div className="flex flex-col h-screen">
      {/* Header */}
      <div className="px-4 pt-3 pb-2 border-b bg-white">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-lg font-semibold">{folderName}</p>
            <p className="text-xs text-gray-400">{workspaceFolder}</p>
            <p className="text-xs text-gray-500">{imageFiles.length} images</p>
          </div>
          <button
            className="text-sm px-3 py-1 border rounded hover:bg-gray-50"
            onClick={onChangeWorkspace}
          >
            Change workspace
          </button>
        </div>
      </div>

      {/* Tab bar */}
      <div className="flex border-b bg-white">
        {TABS.map((tab, i) => (
          <button
            key={tab}
            className={`px-5 py-2 text-sm font-medium border-b-2 transition-colors ${
              activeTab === i
                ? "border-green-600 text-green-700"
                : "border-transparent text-gray-600 hover:text-gray-900"
            }`}
            onClick={() => setActiveTab(i)}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="flex-1 overflow-hidden">
        {activeTab === 0 && <OverviewTab />}
        {activeTab === 1 && <ImageViewerTab />}
        {activeTab === 2 && <ConfigTab />}
      </div>
    </div>
  );
}
