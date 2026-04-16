import { app } from "electron";
import { ChildProcess, spawn } from "child_process";
import * as net from "net";
import * as path from "path";
import * as http from "http";

let sidecarProcess: ChildProcess | null = null;
let sidecarPort: number | null = null;

function findFreePort(): Promise<number> {
  return new Promise((resolve, reject) => {
    const server = net.createServer();
    server.listen(0, "127.0.0.1", () => {
      const address = server.address();
      if (!address || typeof address === "string") {
        reject(new Error("Could not get server address"));
        return;
      }
      const port = address.port;
      server.close(() => resolve(port));
    });
    server.on("error", reject);
  });
}

function pollHealth(port: number, timeoutMs = 10000): Promise<void> {
  return new Promise((resolve, reject) => {
    const start = Date.now();
    const interval = setInterval(() => {
      if (Date.now() - start > timeoutMs) {
        clearInterval(interval);
        reject(new Error(`Sidecar did not become healthy within ${timeoutMs}ms`));
        return;
      }
      const req = http.get(`http://127.0.0.1:${port}/health`, (res) => {
        if (res.statusCode === 200) {
          clearInterval(interval);
          resolve();
        }
      });
      req.on("error", () => {
        /* still starting up */
      });
      req.end();
    }, 300);
  });
}

export async function startSidecar(): Promise<number> {
  const port = await findFreePort();
  sidecarPort = port;

  let command: string;
  let args: string[];

  if (app.isPackaged) {
    const ext = process.platform === "win32" ? ".exe" : "";
    const binary = path.join(
      process.resourcesPath,
      "sidecar",
      `herbairium-sidecar${ext}`
    );
    command = binary;
    args = ["--port", String(port)];
  } else {
    // Dev: run Python directly from repo root
    const repoRoot = path.resolve(__dirname, "../../..");
    const serverScript = path.join(repoRoot, "HerbAIrium", "sidecar", "server.py");
    const venvPython = path.join(repoRoot, ".venv", "bin", "python");
    command = venvPython;
    args = [serverScript, "--port", String(port), "--dev"];
  }

  sidecarProcess = spawn(command, args, {
    detached: false,
    stdio: "pipe",
  });

  sidecarProcess.stdout?.on("data", (d) => process.stdout.write(`[sidecar] ${d}`));
  sidecarProcess.stderr?.on("data", (d) => process.stderr.write(`[sidecar] ${d}`));

  sidecarProcess.on("exit", (code) => {
    console.log(`[sidecar] exited with code ${code}`);
  });

  await pollHealth(port);
  return port;
}

export function getSidecarPort(): number {
  if (sidecarPort === null) throw new Error("Sidecar not started");
  return sidecarPort;
}

export function killSidecar(): Promise<void> {
  return new Promise((resolve) => {
    if (!sidecarProcess) {
      resolve();
      return;
    }
    const proc = sidecarProcess;
    const timer = setTimeout(() => {
      proc.kill("SIGKILL");
      resolve();
    }, 2000);
    proc.on("exit", () => {
      clearTimeout(timer);
      resolve();
    });
    proc.kill("SIGTERM");
  });
}
