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
  } = useApp();

  function handleChangeWorkspace() {
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
