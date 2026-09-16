import { app, BrowserWindow, dialog } from "electron";
import * as path from "path";
import { startSidecar, killSidecar, getSidecarPort } from "./sidecar";
import { registerIpc } from "./ipc";

let mainWindow: BrowserWindow | null = null;

function createWindow(): BrowserWindow {
  const win = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 900,
    minHeight: 640,
    show: true,
    backgroundColor: "#f4f7f1",
    title: "HerbAIrium",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  win.on("closed", () => {
    if (mainWindow === win) mainWindow = null;
  });
  mainWindow = win;
  return win;
}

async function loadApplication(win: BrowserWindow): Promise<void> {
  if (app.isPackaged) {
    await win.loadFile(path.join(__dirname, "../../renderer/dist/index.html"));
  } else {
    await win.loadURL(`http://localhost:5173/?sidecarPort=${getSidecarPort()}`);
    win.webContents.openDevTools();
  }
  win.show();
  win.focus();
}

app.whenReady().then(async () => {
  const win = createWindow();
  registerIpc(win);
  await win.loadURL(
    `data:text/html;charset=utf-8,${encodeURIComponent(
      '<!doctype html><html><head><meta charset="utf-8"><title>HerbAIrium</title>' +
      '<style>body{margin:0;background:#f4f7f1;color:#263328;font:16px system-ui;display:grid;' +
      'place-items:center;height:100vh}main{text-align:center}h1{font-size:28px;margin:0 0 12px}' +
      'p{margin:0;color:#5b685d}</style></head><body><main><h1>HerbAIrium</h1>' +
      '<p>Starting background services...</p></main></body></html>',
    )}`,
  );

  try {
    await startSidecar();
    await loadApplication(win);
  } catch (err) {
    await dialog.showMessageBox(win, {
      type: "error",
      title: "HerbAIrium - Startup Error",
      message: "HerbAIrium could not start.",
      detail: `${err instanceof Error ? err.message : String(err)}\n\nPlease restart the app.`,
    });
    app.quit();
  }
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});

app.on("activate", async () => {
  if (mainWindow === null) {
    const win = createWindow();
    await loadApplication(win);
  }
});

app.on("before-quit", async (event) => {
  event.preventDefault();
  await killSidecar();
  app.exit(0);
});
