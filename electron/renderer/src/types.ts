export interface Configuration {
  image_files: string[];
  llm_base_url: string;
  deepinfra_api_key: string;
  olm_model: string;
  olm_temperature: number;
  olm_max_tokens: number;
  olm_prompt: string;
  llm_parse_model: string;
  llm_parse_temperature: number;
  llm_parse_max_tokens: number;
  llm_parse_prompt: string;
}

export interface Metadata {
  image_path: string;
  ocr_result: string | null;
  ai_result: string | null;
  catalogNumber: string | null;
  recordNumber: number | null;
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

export interface WorkspaceOpenResponse {
  folder_path: string;
  image_count: number;
  image_files: string[];
  config: Configuration;
}

declare global {
  interface Window {
    electronAPI: {
      getSidecarPort: () => Promise<number>;
      openFolderDialog: () => Promise<string | null>;
    };
  }
}

export interface BatchProgressEvent {
  stage: "ocr" | "llm" | "done";
  current?: number;
  total?: number;
  filename?: string;
  status?: "ok" | "error";
  error?: string | null;
  ocr_ok?: number;
  ocr_fail?: number;
  llm_ok?: number;
  llm_fail?: number;
}
