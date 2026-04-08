import { useApp } from "./context/AppContext";
import { WorkspaceView } from "./views/WorkspaceView";
import { MainView } from "./views/MainView";

export function App() {
  const { workspaceFolder, setWorkspaceFolder, setConfig, setImageFiles, setCurrentIndex } = useApp();

  function handleChangeWorkspace() {
    setWorkspaceFolder(null);
    setConfig(null);
    setImageFiles([]);
    setCurrentIndex(0);
  }

  if (!workspaceFolder) {
    return <WorkspaceView />;
  }

  return <MainView onChangeWorkspace={handleChangeWorkspace} />;
}
