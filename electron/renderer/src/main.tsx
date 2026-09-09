import React from "react";
import ReactDOM from "react-dom/client";
import { App } from "./App";
import { AppProvider } from "./context/AppContext";
import { initApi } from "./api";
import "./index.css";

async function bootstrap() {
  const portParam = new URLSearchParams(window.location.search).get("sidecarPort");
  const portFromUrl = portParam === null ? null : Number(portParam);

  // Dev mode passes the dynamic sidecar port in the renderer URL. Packaged
  // builds use the preload bridge, while standalone browser testing uses 8765.
  let port = 8765;
  if (portFromUrl !== null && Number.isInteger(portFromUrl) && portFromUrl > 0) {
    port = portFromUrl;
  } else if (window.electronAPI) {
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
