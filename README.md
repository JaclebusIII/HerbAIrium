# HerbAIrium

A tool to view a herbarium project and process images with AI (OCR + structured parsing via DeepInfra).

## Requirements

- Python 3.10+
- DeepInfra API key

## Setup

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Run the app (Flet)

From the repository root:

```bash
flet run HerbAIrium/flet_app.py
```

Or:

```bash
python HerbAIrium/flet_app.py
```

Use **Browse…** or paste a folder path, then open a workspace that contains your specimen images (jpg, png, tiff, etc.).

## Build a Windows desktop app

Build on a **Windows 10/11** machine (or a Windows VM / CI runner). You generally cannot produce a Windows `.exe` only from macOS.

1. Install Python 3.10+ (enable “Add Python to PATH”).
2. From the repo root:
   ```bat
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   pip install "flet[all]"
   ```
3. Package with PyInstaller (typical output under `dist\`):
   ```bat
   flet pack HerbAIrium\flet_app.py -n HerbAIrium --product-name HerbAIrium
   ```
   Optional icon (`.ico`):
   ```bat
   flet pack HerbAIrium\flet_app.py -n HerbAIrium -i path\to\icon.ico
   ```
4. If the executable fails on startup with missing modules, add hidden imports for the `flet_ui` package:
   ```bat
   flet pack HerbAIrium\flet_app.py -n HerbAIrium --hidden-import flet_ui --hidden-import flet_ui.batch --hidden-import flet_ui.helpers --hidden-import flet_ui.main_view --hidden-import flet_ui.state --hidden-import flet_ui.tab_config --hidden-import flet_ui.tab_image --hidden-import flet_ui.tab_overview --hidden-import flet_ui.workspace
   ```

Alternative (Flutter-based installer; may need extra tooling — run `flet doctor`):

```bat
flet build windows HerbAIrium
```

More options: [Flet packaging](https://flet.dev/docs/publish/packaging/).

## Pack on macOS / Linux

From the repo root (same `flet pack` / `flet build` idea; use paths appropriate for your OS):

```bash
pip install "flet[all]"
flet pack HerbAIrium/flet_app.py -n HerbAIrium --product-name HerbAIrium
```
