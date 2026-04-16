# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Python sidecar setup
python -m venv .venv
source .venv/bin/activate
pip install -r HerbAIrium/sidecar/requirements.txt

# Run sidecar in dev mode (enables CORS for Vite)
python HerbAIrium/sidecar/server.py --port 8765 --dev

# Build sidecar binary (macOS/Linux)
cd HerbAIrium/sidecar
pyinstaller sidecar.spec

# Electron app setup
cd electron
npm install

# Run Electron app in dev mode (starts Vite + Electron)
npm run dev

# Build Electron distributable
npm run build
```

Python version: 3.10.16 (see `.python-version`). No test framework or linter is configured.

## Architecture

HerbAIrium is an Electron + React desktop app backed by a FastAPI Python sidecar. It processes herbarium specimen images using AI: OCR via a Vision LLM, followed by structured metadata extraction via an LLM — both served through DeepInfra.

### Data flow

1. User selects a workspace folder → sidecar `POST /workspace/open` scans for images and loads/creates `.herbairium_configuration.json`
2. Per image: OCR (vision model) → raw transcription → LLM parsing → structured metadata → saved as `.json` alongside the image
3. Batch mode: `POST /batch/process` streams SSE events; up to 5 concurrent OCR tasks, then 5 concurrent LLM tasks

### Module responsibilities

**Python sidecar (`HerbAIrium/`)**

| Module | Role |
|---|---|
| `sidecar/server.py` | FastAPI app; all HTTP endpoints and batch SSE streaming |
| `utils.py` | Core processing: `process_ocr_and_save_results`, `llm_parse_transcription_and_save_results` |
| `models/configuration.py` | Pydantic-settings `Configuration` class; persists workspace settings to JSON |
| `models/metadata.py` | Pydantic `Metadata` class; persists OCR text + parsed herbarium fields to JSON |
| `clients/deepinfra_client.py` | HTTP wrapper for DeepInfra vision and chat completion APIs |

**Electron frontend (`electron/`)**

| Module | Role |
|---|---|
| `main/src/` | Electron main process; spawns/manages the sidecar binary |
| `renderer/src/App.tsx` | Root component; workspace vs. main view routing |
| `renderer/src/api.ts` | Typed fetch wrappers for every sidecar endpoint |
| `renderer/src/views/WorkspaceView.tsx` | Folder selection screen |
| `renderer/src/views/MainView.tsx` | 3-tab shell (Overview, Image Viewer, Configuration) |
| `renderer/src/tabs/OverviewTab.tsx` | Batch processing UI with SSE progress stream |
| `renderer/src/tabs/ImageViewerTab.tsx` | Single-image viewer with per-image OCR/parse buttons |
| `renderer/src/tabs/ConfigTab.tsx` | Edits and saves configuration fields |

### Key design patterns

- **Sidecar pattern** — Electron main process spawns the PyInstaller-bundled `herbairium-sidecar` binary on startup and kills it on exit. The renderer communicates with it via `localhost:8765`.
- **Configuration and Metadata are file-backed Pydantic models** — each workspace has one `.herbairium_configuration.json`; each image has a paired `.json` metadata file.
- **All AI calls go through `DeepinfraClient`** — OCR uses a vision model (base64-encoded image), LLM parsing uses a chat model with the transcription as context.
- **`test_images/`** contains real herbarium specimens for manual end-to-end testing. Point the app at that folder to test without a full dataset.
