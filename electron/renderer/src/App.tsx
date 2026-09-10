import { useApp } from "./context/AppContext";
import { WorkspaceView } from "./views/WorkspaceView";
import { MainView } from "./views/MainView";

export function App() {
  const {
    workspaceFolder,
    setWorkspaceFolder,
    setConfig,
    setImageFiles,
    setImageSummaries,
    setCurrentIndex,
    batchRunning,
    cancelBatch,
    resetBatchState,
  } = useApp();

  function handleChangeWorkspace() {
    if (batchRunning) {
      const confirmed = window.confirm(
        "A bulk parse is still running. Change workspace and cancel the remaining work?",
      );
      if (!confirmed) return;
      cancelBatch();
    }
    resetBatchState();
    setWorkspaceFolder(null);
    setConfig(null);
    setImageFiles([]);
    setImageSummaries([]);
    setCurrentIndex(null);
  }

  if (!workspaceFolder) {
    return <WorkspaceView />;
  }

  return <MainView onChangeWorkspace={handleChangeWorkspace} />;
}
