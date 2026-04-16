"""
HerbAIrium FastAPI sidecar.

Usage:
    python server.py --port 8765 [--dev]

The --dev flag enables CORS for the Vite dev server at http://localhost:5173.
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import json
import signal
import sys
from collections.abc import Callable
from io import BytesIO
from pathlib import Path

# Ensure the HerbAIrium package root is on sys.path when run as a script
# or from a PyInstaller bundle.
_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from PIL import Image as PILImage
from pydantic import BaseModel

from models.configuration import Configuration
from models.metadata import Metadata
from utils import (
    llm_parse_transcription_and_save_results,
    process_ocr_and_save_results,
)

parser = argparse.ArgumentParser(description="HerbAIrium sidecar server")
parser.add_argument("--port", type=int, default=8765)
parser.add_argument("--dev", action="store_true", help="Enable CORS for Vite dev server")
args, _ = parser.parse_known_args()

app = FastAPI(title="HerbAIrium Sidecar")

if args.dev:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

_cfg: Configuration | None = None


def _require_workspace() -> Configuration:
    if _cfg is None:
        raise HTTPException(status_code=409, detail="No workspace open. Call POST /workspace/open first.")
    return _cfg


def _image_path(cfg: Configuration, index: int) -> str:
    """Return the image path for index, or raise 404."""
    if index < 0 or index >= len(cfg.image_files):
        raise HTTPException(status_code=404, detail="Image index out of range.")
    return cfg.image_files[index]


class WorkspaceOpenRequest(BaseModel):
    folder_path: str


class ConfigSaveRequest(BaseModel):
    llm_base_url: str | None = None
    deepinfra_api_key: str | None = None
    olm_model: str | None = None
    olm_temperature: float | None = None
    olm_max_tokens: int | None = None
    olm_prompt: str | None = None
    llm_parse_model: str | None = None
    llm_parse_temperature: float | None = None
    llm_parse_max_tokens: int | None = None
    llm_parse_prompt: str | None = None


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/workspace/open")
def workspace_open(req: WorkspaceOpenRequest):
    global _cfg
    folder = Path(req.folder_path)
    if not folder.exists():
        raise HTTPException(status_code=400, detail=f"Path does not exist: {req.folder_path}")
    if not folder.is_dir():
        raise HTTPException(status_code=400, detail=f"Not a directory: {req.folder_path}")
    _cfg = Configuration(workspace_folder=str(folder))
    return {
        "folder_path": str(folder),
        "image_count": len(_cfg.image_files),
        "image_files": _cfg.image_files,
        "config": _cfg.model_dump(),
    }


@app.get("/config")
def get_config():
    return _require_workspace().model_dump()


@app.post("/config/save")
def save_config(req: ConfigSaveRequest):
    cfg = _require_workspace()
    for key, value in req.model_dump(exclude_none=True).items():
        setattr(cfg, key, value)
    if not cfg.save():
        raise HTTPException(status_code=500, detail="Failed to save configuration.")
    return {"saved": True}


@app.get("/images")
def get_images():
    cfg = _require_workspace()
    return {"image_files": cfg.image_files, "count": len(cfg.image_files)}


def _thumbnail_data_uri(image_path: str, size: int = 256) -> str:
    with PILImage.open(image_path) as im:
        im.load()
        im = im.copy()
        im.thumbnail((size, size), PILImage.Resampling.LANCZOS)
        buf = BytesIO()
        if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
            im.convert("RGBA").save(buf, format="PNG", optimize=True)
            mime = "image/png"
        else:
            im.convert("RGB").save(buf, format="JPEG", quality=85, optimize=True)
            mime = "image/jpeg"
    return f"data:{mime};base64,{base64.b64encode(buf.getvalue()).decode()}"


@app.get("/images/{index}/thumbnail")
def get_thumbnail(index: int):
    cfg = _require_workspace()
    path = _image_path(cfg, index)
    try:
        data_uri = _thumbnail_data_uri(path)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return {"index": index, "data_uri": data_uri, "filename": Path(path).name}


@app.get("/images/{index}/metadata")
def get_metadata(index: int):
    cfg = _require_workspace()
    return Metadata(image_path=_image_path(cfg, index)).model_dump()


@app.post("/images/{index}/ocr")
async def run_ocr(index: int):
    cfg = _require_workspace()
    path = _image_path(cfg, index)
    try:
        await asyncio.to_thread(process_ocr_and_save_results, path, cfg)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return {"ocr_result": Metadata(image_path=path).ocr_result, "image_path": path}


@app.post("/images/{index}/parse")
async def run_parse(index: int):
    cfg = _require_workspace()
    path = _image_path(cfg, index)
    md = Metadata(image_path=path)
    if not md.ocr_result:
        raise HTTPException(status_code=400, detail="No OCR result found. Run OCR first.")
    try:
        await asyncio.to_thread(llm_parse_transcription_and_save_results, path, cfg)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return Metadata(image_path=path).model_dump()


@app.post("/batch/process")
async def batch_process():
    cfg = _require_workspace()
    return StreamingResponse(
        _batch_stream(cfg),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


async def _collect(
    stage: str,
    func: Callable,
    path: str,
    cfg: Configuration,
    sem: asyncio.Semaphore,
    lock: asyncio.Lock,
    done_counter: list[int],
    total: int,
) -> tuple[str, bool, str | None, str]:
    async with sem:
        try:
            await asyncio.to_thread(func, path, cfg)
            ok, err = True, None
        except Exception as exc:
            ok, err = False, str(exc)
    async with lock:
        done_counter[0] += 1
        event = json.dumps({
            "stage": stage,
            "current": done_counter[0],
            "total": total,
            "filename": Path(path).name,
            "status": "ok" if ok else "error",
            "error": err,
        })
        event = f"data: {event}\n\n"
    return (path, ok, err, event)


async def _batch_stream(cfg: Configuration):
    files = cfg.image_files
    n = len(files)
    sem = asyncio.Semaphore(5)
    lock = asyncio.Lock()
    ocr_done = [0]

    ocr_results = await asyncio.gather(
        *[_collect("ocr", process_ocr_and_save_results, f, cfg, sem, lock, ocr_done, n) for f in files]
    )

    ocr_ok: list[str] = []
    ocr_fail = 0
    for path, ok, _err, event in ocr_results:
        yield event
        if ok:
            ocr_ok.append(path)
        else:
            ocr_fail += 1

    llm_done = [0]
    llm_ok = 0
    llm_fail = 0

    if ocr_ok:
        llm_results = await asyncio.gather(
            *[_collect("llm", llm_parse_transcription_and_save_results, f, cfg, sem, lock, llm_done, len(ocr_ok)) for f in ocr_ok]
        )
        for _path, ok, _err, event in llm_results:
            yield event
            if ok:
                llm_ok += 1
            else:
                llm_fail += 1

    yield f'data: {{"stage":"done","ocr_ok":{len(ocr_ok)},"ocr_fail":{ocr_fail},"llm_ok":{llm_ok},"llm_fail":{llm_fail}}}\n\n'


def _handle_sigterm(*_):
    sys.exit(0)


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, _handle_sigterm)
    uvicorn.run(app, host="127.0.0.1", port=args.port, loop="asyncio", log_level="warning")
