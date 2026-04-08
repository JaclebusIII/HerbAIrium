import { app, BrowserWindow, dialog } from "electron";
import * as path from "path";
import { startSidecar, killSidecar } from "./sidecar";
import { registerIpc } from "./ipc";

let mainWindow: BrowserWindow | null = null;

async function createWindow(): Promise<void> {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 900,
    minHeight: 640,
    show: false,
    title: "HerbAIrium",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  registerIpc(mainWindow);

  if (app.isPackaged) {
    try {
      await mainWindow.loadFile(path.join(__dirname, "../../renderer/dist/index.html"));
    } catch (err) {
      dialog.showErrorBox("HerbAIrium", `Failed to load app: ${err instanceof Error ? err.message : String(err)}`);
      app.quit();
      return;
    }
  } else {
    await mainWindow.loadURL("http://localhost:5173");
    mainWindow.webContents.openDevTools();
  }

  mainWindow.once("ready-to-show", () => {
    mainWindow?.show();
  });

  mainWindow.on("closed", () => {
    mainWindow = null;
  });
}

app.whenReady().then(async () => {
  try {
    await startSidecar();
  } catch (err) {
    dialog.showErrorBox(
      "HerbAIrium — Startup Error",
      `The background process failed to start:\n\n${err instanceof Error ? err.message : String(err)}\n\nPlease restart the app.`
    );
    app.quit();
    return;
  }
  await createWindow();
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});

app.on("activate", async () => {
  if (mainWindow === null) await createWindow();
});

app.on("before-quit", async (event) => {
  event.preventDefault();
  await killSidecar();
  app.exit(0);
});
