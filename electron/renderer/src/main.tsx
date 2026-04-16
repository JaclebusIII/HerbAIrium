import React from "react";
import ReactDOM from "react-dom/client";
import { App } from "./App";
import { AppProvider } from "./context/AppContext";
import { initApi } from "./api";
import "./index.css";

async function bootstrap() {
  // In Electron the preload script exposes electronAPI; in a browser dev server
  // we fall back to a hard-coded port for convenient testing.
  let port = 8765;
  if (typeof window !== "undefined" && window.electronAPI) {
    port = await window.electronAPI.getSidecarPort();
  }
  initApi(port);

  ReactDOM.createRoot(document.getElementById("root")!).render(
    <React.StrictMode>
      <AppProvider>
        <App />
      </AppProvider>
    </React.StrictMode>
  );
}

bootstrap();
