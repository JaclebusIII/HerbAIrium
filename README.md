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

## Pack as a desktop app (optional)

Flet can produce standalone executables for Windows and macOS:

```bash
flet pack HerbAIrium/flet_app.py
```

See [Flet packaging docs](https://flet.dev/docs/publish/packaging/) for code signing and platform-specific options.
