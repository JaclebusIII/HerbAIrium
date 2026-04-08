import type {
  BatchProgressEvent,
  Configuration,
  Metadata,
  ThumbnailResponse,
  WorkspaceOpenResponse,
} from "./types";

let baseUrl = "";

export function initApi(port: number): void {
  baseUrl = `http://127.0.0.1:${port}`;
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${baseUrl}${path}`, options);
  if (!res.ok) {
    const detail = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(detail.detail ?? res.statusText);
  }
  return res.json() as Promise<T>;
}

export function openWorkspace(folderPath: string): Promise<WorkspaceOpenResponse> {
  return request("/workspace/open", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ folder_path: folderPath }),
  });
}

export function getConfig(): Promise<Configuration> {
  return request("/config");
}

export function saveConfig(config: Partial<Configuration>): Promise<{ saved: boolean }> {
  return request("/config/save", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(config),
  });
}

export function getImages(): Promise<{ image_files: string[]; count: number }> {
  return request("/images");
}

export function getThumbnail(index: number): Promise<ThumbnailResponse> {
  return request(`/images/${index}/thumbnail`);
}

export function getMetadata(index: number): Promise<Metadata> {
  return request(`/images/${index}/metadata`);
}

export function runOcr(index: number): Promise<{ ocr_result: string; image_path: string }> {
  return request(`/images/${index}/ocr`, { method: "POST" });
}

export function runParse(index: number): Promise<Metadata> {
  return request(`/images/${index}/parse`, { method: "POST" });
}

// EventSource only supports GET; the batch endpoint is POST, so we read SSE via fetch.
export async function* batchProcessStream(): AsyncGenerator<BatchProgressEvent> {
  const res = await fetch(`${baseUrl}/batch/process`, { method: "POST" });
  if (!res.ok || !res.body) throw new Error("Batch process failed to start");
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n\n");
    buffer = lines.pop() ?? "";
    for (const chunk of lines) {
      const dataLine = chunk.split("\n").find((l) => l.startsWith("data: "));
      if (dataLine) {
        yield JSON.parse(dataLine.slice(6)) as BatchProgressEvent;
      }
    }
  }
}
