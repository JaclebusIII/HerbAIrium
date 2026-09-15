import { useCallback, useRef, useState } from "react";
import { useApp } from "../context/AppContext";
import { OverviewTab } from "../tabs/OverviewTab";
import { ImageViewerTab } from "../tabs/ImageViewerTab";
import { ConfigTab, type ConfigTabHandle } from "../tabs/ConfigTab";

const TABS = ["Overview", "Image viewer", "Configuration"] as const;

export function MainView({ onChangeWorkspace }: { onChangeWorkspace: () => boolean }) {
  const { workspaceFolder, imageFiles, batchRunning } = useApp();
  const [activeTab, setActiveTab] = useState(1);
  const [configDirty, setConfigDirty] = useState(false);
  const [configSaving, setConfigSaving] = useState(false);
  const [navigationPending, setNavigationPending] = useState(false);
  const configTabRef = useRef<ConfigTabHandle>(null);
  const navigationPendingRef = useRef(false);

  const folderName = workspaceFolder?.split(/[\\/]/).pop() ?? "";

  const handleConfigDirtyChange = useCallback((dirty: boolean) => {
    setConfigDirty(dirty);
  }, []);

  const handleConfigSavingChange = useCallback((saving: boolean) => {
    setConfigSaving(saving);
  }, []);

  async function leaveConfiguration(action: () => boolean) {
    if (navigationPendingRef.current || configTabRef.current?.isSaving()) return;

    if (activeTab !== 2 || !configDirty) {
      action();
      return;
    }

    navigationPendingRef.current = true;
    setNavigationPending(true);
    try {
      const decision = await window.electronAPI.confirmUnsavedConfiguration();
      if (decision === "cancel") return;

      if (decision === "save") {
        const saved = await configTabRef.current?.save();
        if (!saved) return;
      }

      const navigated = action();
      if (navigated) setConfigDirty(false);
    } catch (err) {
      window.alert(
        `Unable to confirm unsaved configuration changes: ${
          err instanceof Error ? err.message : String(err)
        }`,
      );
    } finally {
      navigationPendingRef.current = false;
      setNavigationPending(false);
    }
  }

  function handleTabChange(index: number) {
    if (index === activeTab) return;
    void leaveConfiguration(() => {
      setActiveTab(index);
      return true;
    });
  }

  function handleChangeWorkspace() {
    void leaveConfiguration(onChangeWorkspace);
  }

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
            onClick={handleChangeWorkspace}
            disabled={navigationPending || configSaving}
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
            } disabled:opacity-50`}
            onClick={() => handleTabChange(i)}
            disabled={navigationPending || configSaving}
          >
            {tab}
            {i === 0 && batchRunning && (
              <span className="ml-2 text-xs text-green-600">Running</span>
            )}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="flex-1 overflow-hidden">
        {activeTab === 0 && <OverviewTab />}
        {activeTab === 1 && <ImageViewerTab />}
        {activeTab === 2 && (
          <ConfigTab
            ref={configTabRef}
            onDirtyChange={handleConfigDirtyChange}
            onSavingChange={handleConfigSavingChange}
          />
        )}
      </div>
    </div>
  );
}
