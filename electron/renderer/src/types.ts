export interface Configuration {
  image_files: string[];
  llm_base_url: string;
  deepinfra_api_key: string;
  olm_model: string;
  olm_temperature: number;
  olm_max_tokens: number;
  ocr_concurrency: number;
  olm_prompt: string;
  llm_parse_model: string;
  llm_parse_temperature: number;
  llm_parse_max_tokens: number;
  parse_concurrency: number;
  llm_parse_prompt: string;
}

export interface Metadata {
  image_path: string;
  ocr_result: string | null;
  ai_result: string | null;
  catalogNumber: string | null;
  recordNumber: string | number | null;
  family: string | null;
  scientificName: string | null;
  scientificNameAuthorship: string | null;
  eventDate: string | null;
  country: string | null;
  stateProvince: string | null;
  County: string | null;
  Locality: string | null;
  decimalLatitude: number | null;
  decimalLongitude: number | null;
  recordedBy: string | null;
  associatedCollectors: string[] | null;
  minimumElevationInMeters: number | null;
}

export interface ThumbnailResponse {
  index: number;
  data_uri: string;
  filename: string;
}

export interface ImageSummary {
  index: number;
  path: string;
  filename: string;
  ocr_complete: boolean;
  parse_complete: boolean;
  status_error: string | null;
}

export interface WorkspaceOpenResponse {
  folder_path: string;
  image_count: number;
  image_files: string[];
  images?: ImageSummary[];
  config: Configuration;
}

export interface ImagesResponse {
  image_files: string[];
  images: ImageSummary[];
  count: number;
}

declare global {
  interface Window {
    electronAPI: {
      getSidecarPort: () => Promise<number>;
      openFolderDialog: () => Promise<string | null>;
      confirmUnsavedConfiguration: () => Promise<"save" | "discard" | "cancel">;
    };
  }
}

export interface BatchProgressEvent {
  stage: "ocr" | "llm" | "done";
  current?: number;
  total?: number;
  filename?: string;
  status?: "running" | "ok" | "error" | "skipped";
  error?: string | null;
  message?: string;
  provider_status?: string;
  completed_operations?: number;
  total_operations?: number;
  elapsed_seconds?: number;
  ocr_ok?: number;
  ocr_fail?: number;
  ocr_skipped?: number;
  llm_ok?: number;
  llm_fail?: number;
  llm_skipped?: number;
  llm_blocked?: number;
  metadata_fail?: number;
  ocr_elapsed_seconds?: number;
  llm_elapsed_seconds?: number;
  ocr_throughput?: number;
  llm_throughput?: number;
}

export interface BatchSummary {
  ocr_ok: number;
  ocr_fail: number;
  ocr_skipped: number;
  llm_ok: number;
  llm_fail: number;
  llm_skipped: number;
  llm_blocked: number;
  metadata_fail: number;
  elapsed_seconds: number;
  ocr_elapsed_seconds: number;
  llm_elapsed_seconds: number;
  ocr_throughput: number;
  llm_throughput: number;
}
