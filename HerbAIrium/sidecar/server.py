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
import csv
import json
import signal
import sys
from collections.abc import Callable
from io import BytesIO, StringIO
from pathlib import Path

# Ensure the HerbAIrium package root is on sys.path when run as a script
# or from a PyInstaller bundle.
_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from PIL import Image as PILImage
from pydantic import BaseModel, ValidationError

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
        allow_private_network=True,
    )

_cfg: Configuration | None = None

DARWIN_CORE_FIELDS = (
    "catalogNumber",
    "recordNumber",
    "family",
    "scientificName",
    "scientificNameAuthorship",
    "eventDate",
    "country",
    "stateProvince",
    "county",
    "locality",
    "decimalLatitude",
    "decimalLongitude",
    "recordedBy",
    "minimumElevationInMeters",
)


def _require_workspace() -> Configuration:
    if _cfg is None:
        raise HTTPException(status_code=409, detail="No workspace open. Call POST /workspace/open first.")
    return _cfg


def _image_path(cfg: Configuration, index: int) -> str:
    """Return the image path for index, or raise 404."""
    if index < 0 or index >= len(cfg.image_files):
        raise HTTPException(status_code=404, detail="Image index out of range.")
    return cfg.image_files[index]


def _image_summaries(cfg: Configuration) -> list[dict]:
    summaries = []
    for index, path in enumerate(cfg.image_files):
        try:
            metadata = Metadata(image_path=path)
            ocr_complete = bool(metadata.ocr_result)
            parse_complete = bool(metadata.ai_result)
            status_error = None
        except (OSError, json.JSONDecodeError, ValidationError) as exc:
            ocr_complete = False
            parse_complete = False
            status_error = str(exc)
        summaries.append({
            "index": index,
            "path": path,
            "filename": Path(path).name,
            "ocr_complete": ocr_complete,
            "parse_complete": parse_complete,
            "status_error": status_error,
        })
    return summaries


def _darwin_core_csv(cfg: Configuration) -> str:
    output = StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=DARWIN_CORE_FIELDS)
    writer.writeheader()

    for path in cfg.image_files:
        metadata = Metadata(image_path=path)
        collectors = [metadata.recordedBy, *(metadata.associatedCollectors or [])]
        row = {
            "catalogNumber": metadata.catalogNumber,
            "recordNumber": metadata.recordNumber,
            "family": metadata.family,
            "scientificName": metadata.scientificName,
            "scientificNameAuthorship": metadata.scientificNameAuthorship,
            "eventDate": metadata.eventDate,
            "country": metadata.country,
            "stateProvince": metadata.stateProvince,
            "county": metadata.County,
            "locality": metadata.Locality,
            "decimalLatitude": metadata.decimalLatitude,
            "decimalLongitude": metadata.decimalLongitude,
            "recordedBy": "|".join(collector for collector in collectors if collector),
            "minimumElevationInMeters": metadata.minimumElevationInMeters,
        }
        writer.writerow({key: "" if value is None else value for key, value in row.items()})

    return output.getvalue()


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
        "images": _image_summaries(_cfg),
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
    return {
        "image_files": cfg.image_files,
        "images": _image_summaries(cfg),
        "count": len(cfg.image_files),
    }


@app.get("/export/darwin-core")
def export_darwin_core():
    cfg = _require_workspace()
    try:
        csv_content = _darwin_core_csv(cfg)
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        raise HTTPException(status_code=500, detail=f"Failed to export workspace metadata: {exc}")
    return Response(
        content=csv_content.encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="darwin-core.csv"'},
    )


@app.post("/workspace/clear-results")
def clear_workspace_results():
    cfg = _require_workspace()
    cleared = 0
    failures = []

    for image_path in cfg.image_files:
        metadata_path = Path(image_path).with_suffix(".json")
        try:
            metadata_path.unlink(missing_ok=True)
            cleared += 1
        except OSError as exc:
            failures.append(f"{metadata_path.name}: {exc}")

    if failures:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to clear {len(failures)} metadata files: {'; '.join(failures)}",
        )
    return {"cleared": cleared}


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
    events: asyncio.Queue[dict],
    results: list[tuple[str, bool, str | None]],
) -> None:
    async with sem:
        await events.put({
            "stage": stage,
            "current": done_counter[0],
            "total": total,
            "filename": Path(path).name,
            "status": "running",
            "error": None,
        })
        try:
            await asyncio.to_thread(func, path, cfg)
            ok, err = True, None
        except Exception as exc:
            ok, err = False, str(exc)
    async with lock:
        done_counter[0] += 1
        results.append((path, ok, err))
        await events.put({
            "stage": stage,
            "current": done_counter[0],
            "total": total,
            "filename": Path(path).name,
            "status": "ok" if ok else "error",
            "error": err,
        })


def _sse_event(event: dict) -> str:
    return f"data: {json.dumps(event)}\n\n"


async def _stream_stage(
    stage: str,
    func: Callable,
    files: list[str],
    cfg: Configuration,
    sem: asyncio.Semaphore,
    results: list[tuple[str, bool, str | None]],
):
    total = len(files)
    if total == 0:
        return

    events: asyncio.Queue[dict] = asyncio.Queue()
    lock = asyncio.Lock()
    done_counter = [0]
    tasks = [
        asyncio.create_task(
            _collect(stage, func, path, cfg, sem, lock, done_counter, total, events, results)
        )
        for path in files
    ]

    try:
        completed = 0
        while completed < total:
            event = await events.get()
            yield _sse_event(event)
            if event["status"] in ("ok", "error"):
                completed += 1
        await asyncio.gather(*tasks)
    finally:
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


async def _batch_stream(cfg: Configuration):
    files = list(cfg.image_files)
    sem = asyncio.Semaphore(5)
    ocr_results: list[tuple[str, bool, str | None]] = []

    ocr_ok: list[str] = []
    ocr_fail = 0
    async for event in _stream_stage(
        "ocr",
        process_ocr_and_save_results,
        files,
        cfg,
        sem,
        ocr_results,
    ):
        yield event
    for path, ok, _err in ocr_results:
        if ok:
            ocr_ok.append(path)
        else:
            ocr_fail += 1

    llm_results: list[tuple[str, bool, str | None]] = []
    llm_ok = 0
    llm_fail = 0

    async for event in _stream_stage(
        "llm",
        llm_parse_transcription_and_save_results,
        ocr_ok,
        cfg,
        sem,
        llm_results,
    ):
        yield event
    for _path, ok, _err in llm_results:
        if ok:
            llm_ok += 1
        else:
            llm_fail += 1

    yield _sse_event({
        "stage": "done",
        "ocr_ok": len(ocr_ok),
        "ocr_fail": ocr_fail,
        "llm_ok": llm_ok,
        "llm_fail": llm_fail,
    })


def _handle_sigterm(*_):
    sys.exit(0)


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, _handle_sigterm)
    uvicorn.run(app, host="127.0.0.1", port=args.port, loop="asyncio", log_level="warning")
