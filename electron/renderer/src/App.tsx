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

  function handleChangeWorkspace(): boolean {
    if (batchRunning) {
      const confirmed = window.confirm(
        "A bulk parse is still running. Change workspace and cancel the remaining work?",
      );
      if (!confirmed) return false;
      cancelBatch();
    }
    resetBatchState();
    setWorkspaceFolder(null);
    setConfig(null);
    setImageFiles([]);
    setImageSummaries([]);
    setCurrentIndex(null);
    return true;
  }

  if (!workspaceFolder) {
    return <WorkspaceView />;
  }

  return <MainView onChangeWorkspace={handleChangeWorkspace} />;
}
