# HerbAIrium

A desktop app for processing herbarium specimen images with AI — OCR to extract label text, followed by structured metadata parsing via DeepInfra.

## Download

Grab the latest release from the [Releases](../../releases) page:
- **macOS**: `HerbAIrium-x.x.x-arm64.dmg`
- **Windows**: `HerbAIrium Setup x.x.x.exe`

Double-click the installer. No Python or Node.js required.

> **macOS note:** The app is not yet notarized. On first launch, right-click → Open to bypass Gatekeeper.

---

## Development

### Requirements
- Python 3.10
- Node.js 18+
- DeepInfra API key

### Setup

```bash
# Python dependencies (for the sidecar)
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Node dependencies (for Electron + React)
cd electron && npm install
cd renderer && npm install
```

### Run in dev mode

```bash
cd electron
npm run dev
```

This starts the Vite dev server, compiles the Electron main process, and launches the app. The Python sidecar is spawned automatically on a free port.

---

## Building a release

### 1. Build the Python sidecar binary

Run this on the target platform (macOS for `.dmg`, Windows for `.exe`):

```bash
source .venv/bin/activate
pip install pyinstaller
pyinstaller HerbAIrium/sidecar/sidecar.spec \
  --distpath HerbAIrium/sidecar/dist \
  --workpath HerbAIrium/sidecar/build
```

Output: `HerbAIrium/sidecar/dist/herbairium-sidecar` (or `.exe` on Windows)

### 2. Package the Electron app

```bash
cd electron

# macOS
npm run package:mac    # → dist/HerbAIrium-x.x.x-arm64.dmg

# Windows (run on a Windows machine)
npm run package:win    # → dist/HerbAIrium Setup x.x.x.exe
```

---

## Architecture

HerbAIrium uses an **Electron + React** frontend backed by a **Python FastAPI sidecar**:

```
electron/
  main/          Electron main process — spawns sidecar, native folder dialog
  renderer/      React + Tailwind UI (Vite)
  build/         electron-builder config, app icons, macOS entitlements

HerbAIrium/
  sidecar/       FastAPI server wrapping all AI processing logic
  clients/       DeepInfra HTTP client
  models/        Pydantic models for configuration and per-image metadata
  utils.py       OCR + LLM orchestration
```

On startup, Electron finds a free port, spawns `herbairium-sidecar`, and health-polls it before showing the window. All AI calls go through the sidecar's REST API. Results are saved as `.json` sidecar files next to each image.
