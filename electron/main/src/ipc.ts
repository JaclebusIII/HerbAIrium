import { BrowserWindow, dialog, ipcMain } from "electron";
import { getSidecarPort } from "./sidecar";

export function registerIpc(_win: BrowserWindow): void {
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
}
