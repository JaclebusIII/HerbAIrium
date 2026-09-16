import { app } from "electron";
import { ChildProcess, spawn } from "child_process";
import * as net from "net";
import * as path from "path";
import * as http from "http";

let sidecarProcess: ChildProcess | null = null;
let sidecarPort: number | null = null;
const SIDECAR_STARTUP_TIMEOUT_MS = 30000;

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

function waitForHealth(
  process: ChildProcess,
  port: number,
  getStderr: () => string,
  timeoutMs = SIDECAR_STARTUP_TIMEOUT_MS,
): Promise<void> {
  return new Promise((resolve, reject) => {
    const start = Date.now();
    let timer: NodeJS.Timeout | null = null;
    let request: http.ClientRequest | null = null;
    let settled = false;

    const finish = (error?: Error) => {
      if (settled) return;
      settled = true;
      if (timer) clearTimeout(timer);
      request?.destroy();
      process.off("error", onProcessError);
      process.off("exit", onProcessExit);
      if (error) reject(error);
      else resolve();
    };

    const failureDetails = () => {
      const stderr = getStderr().trim();
      return stderr ? `\n\n${stderr}` : "";
    };

    const onProcessError = (error: Error) => {
      finish(new Error(`Could not launch the sidecar: ${error.message}`));
    };

    const onProcessExit = (code: number | null, signal: NodeJS.Signals | null) => {
      const reason = signal ? `signal ${signal}` : `code ${code ?? "unknown"}`;
      finish(new Error(`The sidecar exited during startup with ${reason}.${failureDetails()}`));
    };

    const scheduleNextAttempt = () => {
      if (!settled) timer = setTimeout(check, 300);
    };

    const check = () => {
      if (Date.now() - start > timeoutMs) {
        finish(new Error(
          `The sidecar did not become healthy within ${timeoutMs / 1000} seconds.${failureDetails()}`,
        ));
        return;
      }

      request = http.get(`http://127.0.0.1:${port}/health`, (res) => {
        res.resume();
        if (res.statusCode === 200) {
          finish();
        } else {
          scheduleNextAttempt();
        }
      });
      request.setTimeout(1000, () => request?.destroy());
      request.on("error", scheduleNextAttempt);
    };

    process.once("error", onProcessError);
    process.once("exit", onProcessExit);
    check();
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
    windowsHide: true,
  });

  let startupStderr = "";
  sidecarProcess.stdout?.on("data", (d) => process.stdout.write(`[sidecar] ${d}`));
  sidecarProcess.stderr?.on("data", (d) => {
    const output = String(d);
    startupStderr = `${startupStderr}${output}`.slice(-4000);
    process.stderr.write(`[sidecar] ${output}`);
  });

  sidecarProcess.on("exit", (code) => {
    console.log(`[sidecar] exited with code ${code}`);
  });

  try {
    await waitForHealth(sidecarProcess, port, () => startupStderr);
  } catch (error) {
    sidecarPort = null;
    throw error;
  }
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
