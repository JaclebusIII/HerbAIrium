import { contextBridge, ipcRenderer } from "electron";

contextBridge.exposeInMainWorld("electronAPI", {
  getSidecarPort: (): Promise<number> => ipcRenderer.invoke("get-sidecar-port"),
  openFolderDialog: (): Promise<string | null> => ipcRenderer.invoke("open-folder-dialog"),
  confirmUnsavedConfiguration: (): Promise<"save" | "discard" | "cancel"> =>
    ipcRenderer.invoke("confirm-unsaved-configuration"),
});
