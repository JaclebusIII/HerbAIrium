import asyncio
from pathlib import Path

import flet as ft

from models.metadata import Metadata
from utils import format_file_size, llm_parse_transcription_and_save_results, process_ocr

from .helpers import api_key_set, image_bytes_for_viewer, toast
from .state import AppState

_METADATA_KEYS = (
    "catalogNumber",
    "recordNumber",
    "family",
    "scientificName",
    "scientificNameAuthorship",
    "eventDate",
    "country",
    "stateProvince",
    "County",
    "Locality",
    "decimalLatitude",
    "decimalLongitude",
    "recordedBy",
    "associatedCollectors",
    "minimumElevationInMeters",
)


def build_image_tab(page: ft.Page, state: AppState) -> ft.Control:
    cfg = state.configuration
    assert cfg is not None
    paths = cfg.image_files
    if not paths:
        return ft.Container(ft.Text("No images in workspace."), padding=16)

    img_ctrl = ft.Image(
        src=image_bytes_for_viewer(paths[state.current_image_index]),
        fit=ft.BoxFit.CONTAIN,
        width=520,
        height=520,
        border_radius=8,
    )
    img_frame = ft.Container(
        width=520,
        height=520,
        bgcolor=ft.Colors.SURFACE_CONTAINER_LOW,
        alignment=ft.Alignment.CENTER,
        content=img_ctrl,
        border_radius=8,
    )
    meta_list = ft.Column(spacing=4, scroll=ft.ScrollMode.AUTO, width=380)
    ocr_tf = ft.TextField(
        label="OCR transcription",
        multiline=True,
        min_lines=8,
        max_lines=16,
        read_only=True,
        expand=True,
    )
    llm_tf = ft.TextField(
        label="LLM parse result",
        multiline=True,
        min_lines=8,
        max_lines=16,
        read_only=True,
        expand=True,
    )
    busy = ft.ProgressRing(visible=False)
    idx_text = ft.Text()

    def cur() -> str:
        return paths[state.current_image_index]

    def sync_nav(fi, pr, ne, la):
        i, last = state.current_image_index, len(paths) - 1
        fi.disabled = pr.disabled = i <= 0
        ne.disabled = la.disabled = i >= last

    def refresh(fi, pr, ne, la):
        p = cur()
        try:
            img_ctrl.src = image_bytes_for_viewer(p)
            img_ctrl.error_content = None
        except OSError:
            img_ctrl.src = b""
            img_ctrl.error_content = ft.Text(f"Could not load: {Path(p).name}")

        md = Metadata(image_path=p)
        meta_list.controls.clear()
        fp = Path(p)
        try:
            sz = format_file_size(fp.stat().st_size)
        except OSError:
            sz = "?"
        meta_list.controls.extend(
            [ft.Text(f"File: {fp.name}", weight=ft.FontWeight.W_500), ft.Text(f"Size: {sz}")]
        )
        for k in _METADATA_KEYS:
            v = getattr(md, k)
            if k == "associatedCollectors":
                v = ", ".join(v or [])
            meta_list.controls.append(ft.Text(f"{k}: {v}", size=13))
        ocr_tf.value = md.ocr_result or ""
        llm_tf.value = md.ai_result or ""
        idx_text.value = f"Image {state.current_image_index + 1} of {len(paths)}"
        sync_nav(fi, pr, ne, la)
        page.update()

    fi = ft.Button(content="First", icon=ft.Icons.FIRST_PAGE)
    pr = ft.Button(content="Previous", icon=ft.Icons.CHEVRON_LEFT)
    ne = ft.Button(content="Next", icon=ft.Icons.CHEVRON_RIGHT)
    la = ft.Button(content="Last", icon=ft.Icons.LAST_PAGE)

    def go(i: int):
        state.current_image_index = i
        refresh(fi, pr, ne, la)

    fi.on_click = lambda _: go(0)
    pr.on_click = lambda _: go(max(0, state.current_image_index - 1))
    ne.on_click = lambda _: go(min(len(paths) - 1, state.current_image_index + 1))
    la.on_click = lambda _: go(len(paths) - 1)

    key_msg = "Add API key in Configuration, Save, then try again."

    async def run_ocr(_):
        if not api_key_set(cfg):
            toast(page, key_msg)
            page.update()
            return
        busy.visible = True
        page.update()
        try:
            loop = asyncio.get_event_loop()
            text = await loop.run_in_executor(None, process_ocr, cur(), cfg)
            md = Metadata(image_path=cur())
            md.ocr_result = text
            md.save()
            ocr_tf.value = text or ""
            toast(page, "OCR complete.")
        except Exception as ex:
            toast(page, str(ex))
        finally:
            busy.visible = False
            page.update()

    async def run_llm(_):
        if not api_key_set(cfg):
            toast(page, key_msg)
            page.update()
            return
        busy.visible = True
        page.update()
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, llm_parse_transcription_and_save_results, cur(), cfg)
            md = Metadata(image_path=cur())
            llm_tf.value = md.ai_result or ""
            refresh(fi, pr, ne, la)
            toast(page, "LLM parse complete.")
        except Exception as ex:
            toast(page, str(ex))
        finally:
            busy.visible = False
            page.update()

    ocr_btn = ft.FilledButton("Run OCR", icon=ft.Icons.DOCUMENT_SCANNER, on_click=run_ocr)
    llm_btn = ft.FilledButton("Parse with LLM", icon=ft.Icons.PSYCHOLOGY, on_click=run_llm)
    refresh(fi, pr, ne, la)

    return ft.Container(
        content=ft.Column(
            [
                ft.Row([fi, pr, idx_text, ne, la], alignment=ft.MainAxisAlignment.CENTER),
                ft.Row(
                    [
                        ft.Column([img_frame]),
                        ft.Column(
                            [
                                ft.Text("Metadata", weight=ft.FontWeight.W_600),
                                meta_list,
                                ft.Row([ocr_btn, llm_btn, busy], spacing=8),
                            ],
                            expand=True,
                        ),
                    ],
                    alignment=ft.CrossAxisAlignment.START,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                ),
                ocr_tf,
                llm_tf,
            ],
            spacing=12,
            scroll=ft.ScrollMode.AUTO,
        ),
        padding=16,
    )
