import { BrowserWindow, dialog, ipcMain } from "electron";
import { getSidecarPort } from "./sidecar";

export function registerIpc(win: BrowserWindow): void {
  ipcMain.handle("get-sidecar-port", () => {
    return getSidecarPort();
  });

  ipcMain.handle("open-folder-dialog", async () => {
    const result = await dialog.showOpenDialog({
      properties: ["openDirectory"],
      title: "Select workspace folder",
    });
    return result.canceled ? null : (result.filePaths[0] ?? null);
  });

  ipcMain.handle("confirm-unsaved-configuration", async () => {
    const result = await dialog.showMessageBox(win, {
      type: "warning",
      title: "Unsaved configuration",
      message: "Save changes to Configuration before leaving?",
      detail: "Your unsaved configuration changes will be lost if you discard them.",
      buttons: ["Save", "Discard", "Cancel"],
      defaultId: 0,
      cancelId: 2,
      noLink: true,
    });

    return (["save", "discard", "cancel"] as const)[result.response] ?? "cancel";
  });
}
