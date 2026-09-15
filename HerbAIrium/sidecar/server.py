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
import tempfile
from io import BytesIO, StringIO
from pathlib import Path
from time import perf_counter
from typing import Literal

# Ensure the HerbAIrium package root is on sys.path when run as a script
# or from a PyInstaller bundle.
_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

import uvicorn
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from PIL import Image as PILImage
from pydantic import BaseModel, Field, ValidationError

from clients.deepinfra_client import DeepinfraBatchClient, DeepinfraClient
from models.configuration import Configuration
from models.metadata import Metadata
from utils import (
    llm_parse_transcription_and_save_results,
    process_ocr_and_save_results,
    save_llm_parse_result,
    save_ocr_result,
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
_batch_lock = asyncio.Lock()
BATCH_POLL_SECONDS = 5
BATCH_CANCEL_POLL_SECONDS = 0.5
BATCH_CANCEL_POLL_ATTEMPTS = 20
MAX_BATCH_FILE_BYTES = 190 * 1024 * 1024
MAX_BATCH_REQUESTS = 50_000


def _economy_batch_limits(workspace_size: int) -> tuple[int, int]:
    if workspace_size <= 100:
        return 25 * 1024 * 1024, min(1_000, MAX_BATCH_REQUESTS)
    if workspace_size <= 500:
        return 50 * 1024 * 1024, min(5_000, MAX_BATCH_REQUESTS)
    if workspace_size <= 2_000:
        return 100 * 1024 * 1024, min(20_000, MAX_BATCH_REQUESTS)
    return MAX_BATCH_FILE_BYTES, MAX_BATCH_REQUESTS

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
    ocr_concurrency: int | None = Field(default=None, ge=1, le=200)
    olm_prompt: str | None = None
    llm_parse_model: str | None = None
    llm_parse_temperature: float | None = None
    llm_parse_max_tokens: int | None = None
    parse_concurrency: int | None = Field(default=None, ge=1, le=200)
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


@app.get("/images/{index}/image")
def get_image(index: int):
    cfg = _require_workspace()
    path = Path(_image_path(cfg, index))
    media_types = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
    }

    try:
        media_type = media_types.get(path.suffix.lower())
        if media_type is not None:
            return Response(content=path.read_bytes(), media_type=media_type)

        with PILImage.open(path) as im:
            im.load()
            buf = BytesIO()
            im.convert("RGB").save(buf, format="JPEG", quality=95)
        return Response(content=buf.getvalue(), media_type="image/jpeg")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


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
async def batch_process(mode: Literal["realtime", "provider"] = "realtime"):
    cfg = _require_workspace()
    return StreamingResponse(
        _batch_stream(cfg, mode),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _sse_event(event: dict) -> str:
    return f"data: {json.dumps(event)}\n\n"


async def _batch_stream(
    cfg: Configuration,
    mode: Literal["realtime", "provider"] = "realtime",
):
    async with _batch_lock:
        stream = (
            _run_realtime_batch_stream(cfg)
            if mode == "realtime"
            else _run_provider_batch_stream(cfg)
        )
        try:
            async for event in stream:
                yield event
        finally:
            await stream.aclose()


async def _run_realtime_batch_stream(cfg: Configuration):
    started_at = perf_counter()
    events: asyncio.Queue[dict | None] = asyncio.Queue()
    lock = asyncio.Lock()
    ocr_sem = asyncio.Semaphore(cfg.ocr_concurrency)
    parse_sem = asyncio.Semaphore(cfg.parse_concurrency)
    max_connections = cfg.ocr_concurrency + cfg.parse_concurrency
    http_client = httpx.AsyncClient(
        timeout=httpx.Timeout(300, connect=15),
        limits=httpx.Limits(
            max_connections=max_connections,
            max_keepalive_connections=max_connections,
        ),
    )

    work: list[tuple[str, bool]] = []
    counts = {
        "ocr_ok": 0,
        "ocr_fail": 0,
        "ocr_skipped": 0,
        "llm_ok": 0,
        "llm_fail": 0,
        "llm_skipped": 0,
        "llm_blocked": 0,
        "metadata_fail": 0,
    }
    stage_totals = {"ocr": 0, "llm": 0}
    stage_done = {"ocr": 0, "llm": 0}
    stage_started: dict[str, float | None] = {"ocr": None, "llm": None}
    stage_finished: dict[str, float | None] = {"ocr": None, "llm": None}

    for path in cfg.image_files:
        try:
            metadata = Metadata(image_path=path)
        except (OSError, json.JSONDecodeError, ValidationError) as exc:
            counts["metadata_fail"] += 1
            await events.put({
                "stage": "ocr",
                "filename": Path(path).name,
                "status": "error",
                "error": f"Could not read existing metadata: {exc}",
            })
            continue

        needs_ocr = not bool(metadata.ocr_result)
        needs_parse = not bool(metadata.ai_result)
        if not needs_parse:
            counts["ocr_skipped"] += 1
            counts["llm_skipped"] += 1
            continue

        work.append((path, needs_ocr))
        stage_totals["llm"] += 1
        if needs_ocr:
            stage_totals["ocr"] += 1
        else:
            counts["ocr_skipped"] += 1

    total_operations = stage_totals["ocr"] + stage_totals["llm"]
    completed_operations = 0
    ocr_client = DeepinfraClient(
        base_url=cfg.llm_base_url,
        api_key=cfg.deepinfra_api_key,
        model=cfg.olm_model,
        prompt=cfg.olm_prompt,
        max_tokens=cfg.olm_max_tokens,
    )
    parse_client = DeepinfraClient(
        base_url=cfg.llm_base_url,
        api_key=cfg.deepinfra_api_key,
        model=cfg.llm_parse_model,
        prompt=cfg.llm_parse_prompt,
        max_tokens=cfg.llm_parse_max_tokens,
    )

    async def run_stage(stage: str, path: str) -> bool:
        nonlocal completed_operations
        semaphore = ocr_sem if stage == "ocr" else parse_sem
        inference_client = ocr_client if stage == "ocr" else parse_client

        async with semaphore:
            async with lock:
                if stage_started[stage] is None:
                    stage_started[stage] = perf_counter()
                await events.put({
                    "stage": stage,
                    "current": stage_done[stage],
                    "total": stage_totals[stage],
                    "completed_operations": completed_operations,
                    "total_operations": total_operations,
                    "filename": Path(path).name,
                    "status": "running",
                    "message": (
                        f"Running {'OCR' if stage == 'ocr' else 'LLM parse'}: "
                        f"{Path(path).name}"
                    ),
                })

            try:
                if stage == "ocr":
                    content = await inference_client.async_inference(
                        http_client,
                        temperature=cfg.olm_temperature,
                        pdf_path=path,
                    )
                    await asyncio.to_thread(save_ocr_result, path, content)
                else:
                    transcription = Metadata(image_path=path).ocr_result
                    if not transcription:
                        raise ValueError(
                            f"No OCR result found for {Path(path).name}."
                        )
                    content = await inference_client.async_inference(
                        http_client,
                        temperature=cfg.llm_parse_temperature,
                        text=transcription,
                    )
                    await asyncio.to_thread(
                        save_llm_parse_result,
                        path,
                        content,
                    )
                ok, error = True, None
            except Exception as exc:
                ok, error = False, str(exc)

        async with lock:
            stage_done[stage] += 1
            completed_operations += 1
            stage_finished[stage] = perf_counter()
            counts[
                ("ocr_ok" if ok else "ocr_fail")
                if stage == "ocr"
                else ("llm_ok" if ok else "llm_fail")
            ] += 1
            await events.put({
                "stage": stage,
                "current": stage_done[stage],
                "total": stage_totals[stage],
                "completed_operations": completed_operations,
                "total_operations": total_operations,
                "filename": Path(path).name,
                "status": "ok" if ok else "error",
                "error": error,
                "elapsed_seconds": perf_counter() - started_at,
            })
        return ok

    async def process_image(path: str, needs_ocr: bool) -> None:
        nonlocal completed_operations
        if needs_ocr and not await run_stage("ocr", path):
            async with lock:
                counts["llm_blocked"] += 1
                stage_done["llm"] += 1
                completed_operations += 1
                await events.put({
                    "stage": "llm",
                    "current": stage_done["llm"],
                    "total": stage_totals["llm"],
                    "completed_operations": completed_operations,
                    "total_operations": total_operations,
                    "filename": Path(path).name,
                    "status": "skipped",
                    "error": "Parsing skipped because OCR failed.",
                })
            return
        await run_stage("llm", path)

    async def run_all() -> None:
        try:
            await asyncio.gather(
                *(process_image(path, needs_ocr) for path, needs_ocr in work)
            )
        finally:
            await events.put(None)

    runner = asyncio.create_task(run_all())
    try:
        while True:
            event = await events.get()
            if event is None:
                break
            yield _sse_event(event)
        await runner
    finally:
        if not runner.done():
            runner.cancel()
        await asyncio.gather(runner, return_exceptions=True)
        await http_client.aclose()

    elapsed_seconds = perf_counter() - started_at

    def stage_elapsed(stage: str) -> float:
        start = stage_started[stage]
        end = stage_finished[stage]
        return 0.0 if start is None or end is None else end - start

    ocr_elapsed = stage_elapsed("ocr")
    llm_elapsed = stage_elapsed("llm")
    yield _sse_event({
        "stage": "done",
        **counts,
        "elapsed_seconds": elapsed_seconds,
        "ocr_elapsed_seconds": ocr_elapsed,
        "llm_elapsed_seconds": llm_elapsed,
        "ocr_throughput": (
            (counts["ocr_ok"] + counts["ocr_fail"]) / ocr_elapsed
            if ocr_elapsed
            else 0
        ),
        "llm_throughput": (
            (counts["llm_ok"] + counts["llm_fail"]) / llm_elapsed
            if llm_elapsed
            else 0
        ),
    })


async def _run_provider_batch_stream(cfg: Configuration):
    started_at = perf_counter()
    events: asyncio.Queue[dict | None] = asyncio.Queue()
    active_batches: set[str] = set()
    provider_files: set[str] = set()
    ocr_paths: list[str] = []
    parse_paths: list[str] = []
    counts = {
        "ocr_ok": 0,
        "ocr_fail": 0,
        "ocr_skipped": 0,
        "llm_ok": 0,
        "llm_fail": 0,
        "llm_skipped": 0,
        "llm_blocked": 0,
        "metadata_fail": 0,
    }

    for path in cfg.image_files:
        try:
            metadata = Metadata(image_path=path)
        except (OSError, json.JSONDecodeError, ValidationError) as exc:
            counts["metadata_fail"] += 1
            await events.put({
                    "stage": "ocr",
                    "filename": Path(path).name,
                    "status": "error",
                    "error": f"Could not read existing metadata: {exc}",
            })
            continue

        needs_ocr = not bool(metadata.ocr_result)
        needs_parse = not bool(metadata.ai_result)
        if not needs_parse:
            counts["ocr_skipped"] += 1
            counts["llm_skipped"] += 1
            continue
        if needs_ocr:
            ocr_paths.append(path)
        else:
            counts["ocr_skipped"] += 1
            parse_paths.append(path)

    stage_totals = {
        "ocr": len(ocr_paths),
        "llm": len(parse_paths) + len(ocr_paths),
    }
    total_operations = stage_totals["ocr"] + stage_totals["llm"]
    completed_operations = 0
    stage_elapsed = {"ocr": 0.0, "llm": 0.0}

    ocr_client = DeepinfraClient(
        base_url=cfg.llm_base_url,
        api_key=cfg.deepinfra_api_key,
        model=cfg.olm_model,
        prompt=cfg.olm_prompt,
        max_tokens=cfg.olm_max_tokens,
    )
    parse_client = DeepinfraClient(
        base_url=cfg.llm_base_url,
        api_key=cfg.deepinfra_api_key,
        model=cfg.llm_parse_model,
        prompt=cfg.llm_parse_prompt,
        max_tokens=cfg.llm_parse_max_tokens,
    )
    batch_client = DeepinfraBatchClient(cfg.llm_base_url, cfg.deepinfra_api_key)

    async def thread_call(func, *args):
        task = asyncio.create_task(asyncio.to_thread(func, *args))
        try:
            return await asyncio.shield(task)
        except asyncio.CancelledError:
            await asyncio.gather(task, return_exceptions=True)
            raise

    async def create_batch_tracked(input_file_id: str) -> dict:
        task = asyncio.create_task(
            asyncio.to_thread(batch_client.create_batch, input_file_id)
        )
        try:
            batch = await asyncio.shield(task)
        except asyncio.CancelledError:
            result = await asyncio.gather(task, return_exceptions=True)
            if result and isinstance(result[0], dict) and result[0].get("id"):
                active_batches.add(result[0]["id"])
            raise
        active_batches.add(batch["id"])
        return batch

    async def upload_file_tracked(input_path: str) -> str:
        task = asyncio.create_task(
            asyncio.to_thread(batch_client.upload_file, input_path)
        )
        try:
            file_id = await asyncio.shield(task)
        except asyncio.CancelledError:
            result = await asyncio.gather(task, return_exceptions=True)
            if result and isinstance(result[0], str):
                provider_files.add(result[0])
            raise
        provider_files.add(file_id)
        return file_id

    async def write_batch_inputs_tracked(
        stage: str,
        paths: list[str],
        inference_client: DeepinfraClient,
    ) -> list[tuple[str, dict[str, str]]]:
        task = asyncio.create_task(
            asyncio.to_thread(
                write_batch_inputs,
                stage,
                paths,
                inference_client,
            )
        )
        try:
            return await asyncio.shield(task)
        except asyncio.CancelledError:
            result = await asyncio.gather(task, return_exceptions=True)
            if result and isinstance(result[0], list):
                for input_path, _ in result[0]:
                    Path(input_path).unlink(missing_ok=True)
            raise

    async def delete_provider_file(file_id: str | None) -> None:
        if not file_id:
            return
        try:
            await thread_call(batch_client.delete_file, file_id)
        except Exception as exc:
            print(
                f"Failed to delete DeepInfra batch file {file_id}: {exc}",
                file=sys.stderr,
            )
        else:
            provider_files.discard(file_id)

    def write_batch_inputs(
        stage: str,
        paths: list[str],
        inference_client: DeepinfraClient,
    ) -> list[tuple[str, dict[str, str]]]:
        target_file_bytes, target_requests = _economy_batch_limits(
            len(cfg.image_files)
        )
        output_files: list[tuple[str, dict[str, str]]] = []
        batch_file = None
        custom_ids: dict[str, str] = {}
        current_size = 0

        def open_batch_file():
            return tempfile.NamedTemporaryFile(
                mode="wb",
                suffix=".jsonl",
                delete=False,
            )

        def finish_batch_file() -> None:
            nonlocal batch_file, custom_ids, current_size
            if batch_file is None:
                return
            batch_file.close()
            output_files.append((batch_file.name, custom_ids))
            batch_file = None
            custom_ids = {}
            current_size = 0

        try:
            for index, path in enumerate(paths):
                custom_id = f"{stage}-{index}"
                if stage == "ocr":
                    body = inference_client.request_body(
                        temperature=cfg.olm_temperature,
                        pdf_path=path,
                    )
                else:
                    transcription = Metadata(image_path=path).ocr_result
                    if not transcription:
                        raise ValueError(f"No OCR result found for {Path(path).name}.")
                    body = inference_client.request_body(
                        temperature=cfg.llm_parse_temperature,
                        text=transcription,
                    )
                line = (
                    json.dumps({
                        "custom_id": custom_id,
                        "method": "POST",
                        "url": "/v1/chat/completions",
                        "body": body,
                    }) + "\n"
                ).encode("utf-8")
                if len(line) > MAX_BATCH_FILE_BYTES:
                    raise ValueError(
                        f"{Path(path).name} exceeds the provider batch file limit."
                    )
                if custom_ids and (
                    len(custom_ids) >= target_requests
                    or current_size + len(line) > target_file_bytes
                ):
                    finish_batch_file()
                if batch_file is None:
                    batch_file = open_batch_file()
                batch_file.write(line)
                custom_ids[custom_id] = path
                current_size += len(line)
            finish_batch_file()
            return output_files
        except Exception:
            if batch_file is not None:
                batch_file.close()
                Path(batch_file.name).unlink(missing_ok=True)
            for output_path, _ in output_files:
                Path(output_path).unlink(missing_ok=True)
            raise

    def output_content(result: dict) -> str:
        if result.get("error"):
            raise RuntimeError(str(result["error"]))
        response = result["response"]
        if response.get("status_code") != 200:
            raise RuntimeError(
                    f"Batch request failed with status {response.get('status_code')}."
            )
        content = response["body"]["choices"][0]["message"]["content"]
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError("Batch completion content is empty.")
        return content

    async def run_provider_stage(
        stage: str,
        paths: list[str],
        inference_client: DeepinfraClient,
    ) -> list[str]:
        nonlocal completed_operations
        if not paths:
            return []

        stage_started_at = perf_counter()
        input_files: list[tuple[str, dict[str, str]]] = []
        successful_paths: list[str] = []
        try:
            await events.put({
                "stage": stage,
                "current": 0,
                "total": len(paths),
                "completed_operations": completed_operations,
                "total_operations": total_operations,
                "status": "running",
                "provider_status": "preparing",
                "elapsed_seconds": perf_counter() - started_at,
                "message": f"Preparing DeepInfra {stage.upper()} batch input...",
            })
            input_files = await write_batch_inputs_tracked(
                stage,
                paths,
                inference_client,
            )

            stage_completed = 0
            for chunk_index, (input_path, custom_ids) in enumerate(input_files, start=1):
                batch_id = None
                batch_terminal = False
                input_file_id = None
                output_file_id = None
                error_file_id = None
                chunk_successes: set[str] = set()
                try:
                    await events.put({
                        "stage": stage,
                        "current": stage_completed,
                        "total": len(paths),
                        "completed_operations": completed_operations,
                        "total_operations": total_operations,
                        "status": "running",
                        "provider_status": "uploading",
                        "elapsed_seconds": perf_counter() - started_at,
                        "message": (
                            f"Uploading DeepInfra {stage.upper()} batch "
                            f"{chunk_index}/{len(input_files)}..."
                        ),
                    })
                    input_file_id = await upload_file_tracked(
                        input_path,
                    )
                    batch = await create_batch_tracked(input_file_id)
                    batch_id = batch["id"]

                    while batch.get("status") not in batch_client.TERMINAL_STATUSES:
                        request_counts = batch.get("request_counts") or {}
                        provider_finished = min(
                            len(custom_ids),
                            int(request_counts.get("completed") or 0)
                            + int(request_counts.get("failed") or 0),
                        )
                        await events.put({
                            "stage": stage,
                            "current": stage_completed + provider_finished,
                            "total": len(paths),
                            "completed_operations": completed_operations,
                            "total_operations": total_operations,
                            "status": "running",
                            "provider_status": batch.get("status"),
                            "elapsed_seconds": perf_counter() - started_at,
                            "message": (
                                f"DeepInfra {stage.upper()} batch "
                                f"({batch.get('status', 'queued')}): "
                                f"{stage_completed + provider_finished}/"
                                f"{len(paths)} complete; waiting "
                                f"{int(perf_counter() - stage_started_at)}s"
                            ),
                        })
                        await asyncio.sleep(BATCH_POLL_SECONDS)
                        batch = await thread_call(
                            batch_client.retrieve_batch,
                            batch_id,
                        )

                    batch_terminal = True
                    active_batches.discard(batch_id)
                    output_file_id = batch.get("output_file_id")
                    error_file_id = batch.get("error_file_id")
                    if output_file_id:
                        provider_files.add(output_file_id)
                    if error_file_id:
                        provider_files.add(error_file_id)
                    if batch.get("status") != "completed":
                        raise RuntimeError(
                            f"DeepInfra {stage.upper()} batch ended with "
                            f"status {batch.get('status')}."
                        )

                    if not output_file_id:
                        raise RuntimeError(
                            "DeepInfra batch completed without an output file."
                        )
                    output_text = await thread_call(
                        batch_client.download_file,
                        output_file_id,
                    )
                    results = {}
                    for line in output_text.splitlines():
                        if line.strip():
                            result = json.loads(line)
                            results[result["custom_id"]] = result

                    for custom_id, path in custom_ids.items():
                        try:
                            content = output_content(results[custom_id])
                            if stage == "ocr":
                                save_ocr_result(path, content)
                            else:
                                save_llm_parse_result(path, content)
                            counts["ocr_ok" if stage == "ocr" else "llm_ok"] += 1
                            successful_paths.append(path)
                            chunk_successes.add(path)
                            status, error = "ok", None
                        except Exception as exc:
                            counts[
                                "ocr_fail" if stage == "ocr" else "llm_fail"
                            ] += 1
                            status, error = "error", str(exc)

                        stage_completed += 1
                        completed_operations += 1
                        await events.put({
                            "stage": stage,
                            "current": stage_completed,
                            "total": len(paths),
                            "completed_operations": completed_operations,
                            "total_operations": total_operations,
                            "filename": Path(path).name,
                            "status": status,
                            "error": error,
                            "elapsed_seconds": perf_counter() - started_at,
                        })
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    for path in custom_ids.values():
                        if path in chunk_successes:
                            continue
                        counts[
                            "ocr_fail" if stage == "ocr" else "llm_fail"
                        ] += 1
                        stage_completed += 1
                        completed_operations += 1
                        await events.put({
                            "stage": stage,
                            "current": stage_completed,
                            "total": len(paths),
                            "completed_operations": completed_operations,
                            "total_operations": total_operations,
                            "filename": Path(path).name,
                            "status": "error",
                            "error": str(exc),
                            "elapsed_seconds": perf_counter() - started_at,
                        })
                finally:
                    if batch_id and batch_terminal:
                        active_batches.discard(batch_id)
                    if batch_terminal:
                        await delete_provider_file(output_file_id)
                        await delete_provider_file(error_file_id)
                        await delete_provider_file(input_file_id)
                    Path(input_path).unlink(missing_ok=True)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            for path in paths:
                if path in successful_paths:
                    continue
                counts["ocr_fail" if stage == "ocr" else "llm_fail"] += 1
                completed_operations += 1
                await events.put({
                    "stage": stage,
                    "current": completed_operations,
                    "total": len(paths),
                    "completed_operations": completed_operations,
                    "total_operations": total_operations,
                    "filename": Path(path).name,
                    "status": "error",
                    "error": str(exc),
                    "elapsed_seconds": perf_counter() - started_at,
                })
        finally:
            for input_path, _ in input_files:
                Path(input_path).unlink(missing_ok=True)
            stage_elapsed[stage] = perf_counter() - stage_started_at

        return successful_paths

    async def run_all() -> None:
        nonlocal completed_operations
        try:
            ocr_successes = await run_provider_stage(
                "ocr",
                ocr_paths,
                ocr_client,
            )
            blocked_paths = set(ocr_paths) - set(ocr_successes)
            for path in blocked_paths:
                counts["llm_blocked"] += 1
                completed_operations += 1
                await events.put({
                    "stage": "llm",
                    "current": counts["llm_blocked"],
                    "total": stage_totals["llm"],
                    "completed_operations": completed_operations,
                    "total_operations": total_operations,
                    "filename": Path(path).name,
                    "status": "skipped",
                    "error": "Parsing skipped because OCR failed.",
                })

            await run_provider_stage(
                "llm",
                [*parse_paths, *ocr_successes],
                parse_client,
            )
        finally:
            await events.put(None)

    runner = asyncio.create_task(run_all())
    try:
        while True:
            event = await events.get()
            if event is None:
                break
            yield _sse_event(event)
        await runner
    finally:
        if not runner.done():
            runner.cancel()
        await asyncio.gather(runner, return_exceptions=True)
        for batch_id in list(active_batches):
            batch = None
            try:
                await thread_call(batch_client.cancel_batch, batch_id)
            except Exception as exc:
                print(
                    f"Failed to request cancellation for DeepInfra batch "
                    f"{batch_id}: {exc}",
                    file=sys.stderr,
                )
            try:
                batch = None
                for _ in range(BATCH_CANCEL_POLL_ATTEMPTS):
                    batch = await thread_call(
                        batch_client.retrieve_batch,
                        batch_id,
                    )
                    if batch.get("status") in batch_client.TERMINAL_STATUSES:
                        break
                    await asyncio.sleep(BATCH_CANCEL_POLL_SECONDS)
            except Exception as exc:
                print(
                    f"Failed to retrieve DeepInfra batch {batch_id}: {exc}",
                    file=sys.stderr,
                )
            if batch:
                await delete_provider_file(batch.get("output_file_id"))
                await delete_provider_file(batch.get("error_file_id"))
        for file_id in list(provider_files):
            await delete_provider_file(file_id)

    elapsed_seconds = perf_counter() - started_at
    ocr_elapsed = stage_elapsed["ocr"]
    llm_elapsed = stage_elapsed["llm"]
    yield _sse_event({
        "stage": "done",
        **counts,
        "elapsed_seconds": elapsed_seconds,
        "ocr_elapsed_seconds": ocr_elapsed,
        "llm_elapsed_seconds": llm_elapsed,
        "ocr_throughput": (
            (counts["ocr_ok"] + counts["ocr_fail"]) / ocr_elapsed
            if ocr_elapsed
            else 0
        ),
        "llm_throughput": (
            (counts["llm_ok"] + counts["llm_fail"]) / llm_elapsed
            if llm_elapsed
            else 0
        ),
    })


def _handle_sigterm(*_):
    sys.exit(0)


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, _handle_sigterm)
    uvicorn.run(app, host="127.0.0.1", port=args.port, loop="asyncio", log_level="warning")
