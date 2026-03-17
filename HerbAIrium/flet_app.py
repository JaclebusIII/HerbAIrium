"""
HerbAIrium — Flet desktop/web UI.
Reuses Configuration, Metadata, DeepinfraClient, and utils.
"""
from __future__ import annotations

import asyncio
import sys
import weakref
from dataclasses import dataclass
from pathlib import Path

_root = Path(__file__).resolve().parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

import flet as ft

from models.configuration import Configuration
from models.metadata import Metadata
from utils import (
    format_file_size,
    llm_parse_transcription_and_save_results,
    process_ocr,
    process_ocr_and_save_results,
)


def process_single_image_ocr(image_path: str, configuration: Configuration):
    try:
        process_ocr_and_save_results(image_path, configuration)
        return (image_path, True, None)
    except Exception as e:
        return (image_path, False, str(e))


def process_single_image_llm(image_path: str, configuration: Configuration):
    try:
        llm_parse_transcription_and_save_results(image_path, configuration)
        return (image_path, True, None)
    except Exception as e:
        return (image_path, False, str(e))


@dataclass
class AppState:
    workspace_folder: str | None = None
    configuration: Configuration | None = None
    current_image_index: int = 0
    folder_picker: ft.FilePicker | None = None


def _image_bytes_for_viewer(path: str) -> bytes:
    """
    Flet desktop often fails to load file:// URLs for arbitrary paths.
    Feed decoded image bytes instead; downscale large files for stable IPC.
    """
    from io import BytesIO

    from PIL import Image as PILImage

    p = Path(path)
    try:
        with PILImage.open(p) as im:
            im.load()
            max_edge = 2048
            if max(im.size) > max_edge:
                im = im.copy()
                im.thumbnail((max_edge, max_edge), PILImage.Resampling.LANCZOS)
            buf = BytesIO()
            if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
                im = im.convert("RGBA")
                im.save(buf, format="PNG", optimize=True)
            else:
                rgb = im.convert("RGB")
                rgb.save(buf, format="JPEG", quality=90, optimize=True)
            return buf.getvalue()
    except Exception:
        return p.read_bytes()


def _toast(page: ft.Page, message: str) -> None:
    """Flet 0.80+: snack bars are shown via show_dialog, not page.snack_bar."""
    page.show_dialog(ft.SnackBar(content=ft.Text(message)))


def _api_key_set(cfg: Configuration) -> bool:
    return bool((cfg.deepinfra_api_key or "").strip())


def build_workspace_view(page: ft.Page, state: AppState) -> ft.Control:
    path_field = ft.TextField(
        label="Workspace folder path",
        hint_text="/path/to/herbarium/images",
        expand=True,
    )
    hint = ft.Text(color=ft.Colors.ERROR)

    async def open_folder(_):
        if page.web:
            hint.value = "Folder browse is not available in the browser; enter the path manually."
            page.update()
            return
        picker = state.folder_picker
        if picker is None:
            hint.value = "Folder picker is not ready."
            page.update()
            return
        try:
            chosen = await picker.get_directory_path(
                dialog_title="Select workspace folder",
            )
        except ft.FletUnsupportedPlatformException:
            hint.value = "Folder browse is not available here; enter the path manually."
            page.update()
            return
        except Exception as ex:
            hint.value = f"Folder dialog failed: {ex}"
            page.update()
            return
        if not chosen:
            page.update()
            return
        state.workspace_folder = chosen
        state.configuration = Configuration(workspace_folder=chosen)
        state.current_image_index = 0
        show_main_view(page, state)
        page.update()

    def use_path(_):
        hint.value = ""
        p = (path_field.value or "").strip()
        if not p:
            hint.value = "Enter a folder path."
            page.update()
            return
        if not Path(p).is_dir():
            hint.value = "Not a valid directory."
            page.update()
            return
        state.workspace_folder = p
        state.configuration = Configuration(workspace_folder=p)
        state.current_image_index = 0
        show_main_view(page, state)

    return ft.Container(
        content=ft.Column(
            [
                ft.Text("HerbAIrium", size=28, weight=ft.FontWeight.BOLD),
                ft.Text("Select a folder containing herbarium images."),
                ft.Row(
                    [
                        path_field,
                        ft.Button(
                            content="Browse…",
                            icon=ft.Icons.FOLDER_OPEN,
                            on_click=open_folder,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.START,
                ),
                ft.Button(content="Open this folder", icon=ft.Icons.LOGIN, on_click=use_path),
                hint,
            ],
            spacing=16,
            tight=True,
        ),
        padding=24,
    )


def build_overview_tab(page: ft.Page, state: AppState) -> ft.Control:
    pb = ft.ProgressBar(width=480, visible=False)
    status = ft.Text()
    summary = ft.Markdown()

    parse_btn = ft.FilledButton("Parse all images (OCR + LLM)")

    async def on_parse(_):
        cfg = state.configuration
        assert cfg is not None
        if not _api_key_set(cfg):
            status.value = "Set your API key in the Configuration tab first."
            page.update()
            return
        files = cfg.image_files
        if not files:
            status.value = "No image files in this workspace."
            page.update()
            return

        parse_btn.disabled = True
        pb.visible = True
        pb.value = 0
        status.value = ""
        summary.value = ""
        page.update()

        loop = asyncio.get_event_loop()
        sem = asyncio.Semaphore(5)
        n = len(files)
        lock = asyncio.Lock()

        ocr_done = [0]

        async def ocr_one(img: str):
            async with sem:
                r = await loop.run_in_executor(
                    None,
                    lambda ip=img: process_single_image_ocr(ip, cfg),
                )
            async with lock:
                ocr_done[0] += 1
                d = ocr_done[0]
                pb.value = min(0.5, (d / n) * 0.5)
                status.value = f"Phase 1 — OCR: {d}/{n} ({Path(img).name})"
                page.update()
            return r

        ocr_results = await asyncio.gather(*[ocr_one(f) for f in files])

        ocr_ok = [p for p, ok, _ in ocr_results if ok]
        ocr_fail = [(Path(p).name, err) for p, ok, err in ocr_results if not ok]

        llm_ok: list[str] = []
        llm_fail: list[tuple[str, str]] = []

        if ocr_ok:
            m = len(ocr_ok)
            llm_done = [0]

            async def llm_one(img: str):
                async with sem:
                    r = await loop.run_in_executor(
                        None,
                        lambda ip=img: process_single_image_llm(ip, cfg),
                    )
                async with lock:
                    llm_done[0] += 1
                    d = llm_done[0]
                    pb.value = 0.5 + min(0.5, (d / m) * 0.5)
                    status.value = f"Phase 2 — LLM: {d}/{m} ({Path(img).name})"
                    page.update()
                return r

            llm_results = await asyncio.gather(*[llm_one(f) for f in ocr_ok])
            for p, ok, err in llm_results:
                if ok:
                    llm_ok.append(p)
                else:
                    llm_fail.append((Path(p).name, err or ""))

        pb.visible = False
        parse_btn.disabled = False

        lines = [
            f"- **OCR:** {len(ocr_ok)} succeeded, {len(ocr_fail)} failed.",
            f"- **LLM:** {len(llm_ok)} succeeded, {len(llm_fail)} failed.",
        ]
        if ocr_fail or llm_fail:
            lines.append("\n**Failures:**\n")
            for name, err in ocr_fail + llm_fail:
                lines.append(f"- `{name}`: {err}\n")
        else:
            lines.append("\nAll images completed successfully.")
        summary.value = "\n".join(lines)
        status.value = "Done."
        page.update()

    parse_btn.on_click = on_parse

    return ft.Container(
        content=ft.Column(
            [
                ft.Text("Overview", size=22, weight=ft.FontWeight.W_600),
                parse_btn,
                pb,
                status,
                summary,
            ],
            spacing=12,
            scroll=ft.ScrollMode.AUTO,
        ),
        padding=16,
    )


def build_image_tab(page: ft.Page, state: AppState) -> ft.Control:
    cfg = state.configuration
    assert cfg is not None
    paths = cfg.image_files
    if not paths:
        return ft.Container(ft.Text("No images in workspace."), padding=16)

    img_ctrl = ft.Image(
        src=_image_bytes_for_viewer(paths[state.current_image_index]),
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

    def current_path() -> str:
        return paths[state.current_image_index]

    def sync_nav_buttons(
        first_b: ft.Button,
        prev_b: ft.Button,
        next_b: ft.Button,
        last_b: ft.Button,
    ):
        i, last = state.current_image_index, len(paths) - 1
        first_b.disabled = prev_b.disabled = i <= 0
        next_b.disabled = last_b.disabled = i >= last

    def refresh_display(
        first_b: ft.Button,
        prev_b: ft.Button,
        next_b: ft.Button,
        last_b: ft.Button,
    ):
        p = current_path()
        try:
            img_ctrl.src = _image_bytes_for_viewer(p)
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
            [
                ft.Text(f"File: {fp.name}", weight=ft.FontWeight.W_500),
                ft.Text(f"Size: {sz}"),
            ]
        )
        fields = [
            ("catalogNumber", md.catalogNumber),
            ("recordNumber", md.recordNumber),
            ("family", md.family),
            ("scientificName", md.scientificName),
            ("scientificNameAuthorship", md.scientificNameAuthorship),
            ("eventDate", md.eventDate),
            ("country", md.country),
            ("stateProvince", md.stateProvince),
            ("County", md.County),
            ("Locality", md.Locality),
            ("decimalLatitude", md.decimalLatitude),
            ("decimalLongitude", md.decimalLongitude),
            ("recordedBy", md.recordedBy),
            ("associatedCollectors", ", ".join(md.associatedCollectors or [])),
            ("minimumElevationInMeters", md.minimumElevationInMeters),
        ]
        for k, v in fields:
            meta_list.controls.append(ft.Text(f"{k}: {v}", size=13))

        ocr_tf.value = md.ocr_result or ""
        llm_tf.value = md.ai_result or ""
        idx_text.value = f"Image {state.current_image_index + 1} of {len(paths)}"
        sync_nav_buttons(first_b, prev_b, next_b, last_b)
        page.update()

    first_b = ft.Button(content="First", icon=ft.Icons.FIRST_PAGE)
    prev_b = ft.Button(content="Previous", icon=ft.Icons.CHEVRON_LEFT)
    next_b = ft.Button(content="Next", icon=ft.Icons.CHEVRON_RIGHT)
    last_b = ft.Button(content="Last", icon=ft.Icons.LAST_PAGE)

    def go_first(_):
        state.current_image_index = 0
        refresh_display(first_b, prev_b, next_b, last_b)

    def go_prev(_):
        state.current_image_index = max(0, state.current_image_index - 1)
        refresh_display(first_b, prev_b, next_b, last_b)

    def go_next(_):
        state.current_image_index = min(len(paths) - 1, state.current_image_index + 1)
        refresh_display(first_b, prev_b, next_b, last_b)

    def go_last(_):
        state.current_image_index = len(paths) - 1
        refresh_display(first_b, prev_b, next_b, last_b)

    first_b.on_click = go_first
    prev_b.on_click = go_prev
    next_b.on_click = go_next
    last_b.on_click = go_last

    async def run_ocr(_):
        if not _api_key_set(cfg):
            _toast(
                page,
                "Add your API key in the Configuration tab, click Save, then try again.",
            )
            page.update()
            return
        busy.visible = True
        page.update()
        try:
            loop = asyncio.get_event_loop()
            text = await loop.run_in_executor(None, process_ocr, current_path(), cfg)
            md = Metadata(image_path=current_path())
            md.ocr_result = text
            md.save()
            ocr_tf.value = text or ""
            _toast(page, "OCR complete.")
        except Exception as ex:
            _toast(page, str(ex))
        finally:
            busy.visible = False
            page.update()

    async def run_llm(_):
        if not _api_key_set(cfg):
            _toast(
                page,
                "Add your API key in the Configuration tab, click Save, then try again.",
            )
            page.update()
            return
        busy.visible = True
        page.update()
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                llm_parse_transcription_and_save_results,
                current_path(),
                cfg,
            )
            md = Metadata(image_path=current_path())
            llm_tf.value = md.ai_result or ""
            refresh_display(first_b, prev_b, next_b, last_b)
            _toast(page, "LLM parse complete.")
        except Exception as ex:
            _toast(page, str(ex))
        finally:
            busy.visible = False
            page.update()

    ocr_btn = ft.FilledButton("Run OCR", icon=ft.Icons.DOCUMENT_SCANNER, on_click=run_ocr)
    llm_btn = ft.FilledButton("Parse with LLM", icon=ft.Icons.PSYCHOLOGY, on_click=run_llm)

    refresh_display(first_b, prev_b, next_b, last_b)

    return ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [first_b, prev_b, idx_text, next_b, last_b],
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                ft.Row(
                    [
                        ft.Column([img_frame], alignment=ft.MainAxisAlignment.START),
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


def build_config_tab(page: ft.Page, state: AppState) -> ft.Control:
    cfg = state.configuration
    assert cfg is not None

    base_url = ft.TextField(label="LLM base URL", value=cfg.llm_base_url, expand=True)
    api_key = ft.TextField(label="API key", value=cfg.deepinfra_api_key, password=True, can_reveal_password=True, expand=True)
    olm_model = ft.TextField(label="VLM / OCR model", value=cfg.olm_model, expand=True)
    olm_temp = ft.Slider(
        label="OCR temperature",
        min=0,
        max=2,
        divisions=20,
        value=cfg.olm_temperature,
    )
    olm_tokens = ft.TextField(
        label="OCR max tokens",
        value=str(cfg.olm_max_tokens),
        keyboard_type=ft.KeyboardType.NUMBER,
    )
    olm_prompt = ft.TextField(
        label="OCR prompt",
        value=cfg.olm_prompt,
        multiline=True,
        min_lines=4,
        max_lines=12,
        expand=True,
    )
    parse_model = ft.TextField(label="Parse model", value=cfg.llm_parse_model, expand=True)
    parse_temp = ft.Slider(
        label="Parse temperature",
        min=0,
        max=2,
        divisions=20,
        value=cfg.llm_parse_temperature,
    )
    parse_tokens = ft.TextField(
        label="Parse max tokens",
        value=str(cfg.llm_parse_max_tokens),
        keyboard_type=ft.KeyboardType.NUMBER,
    )
    parse_prompt = ft.TextField(
        label="Parse prompt",
        value=cfg.llm_parse_prompt,
        multiline=True,
        min_lines=6,
        max_lines=20,
        expand=True,
    )
    save_msg = ft.Text()

    def save_config(_):
        try:
            cfg.llm_base_url = base_url.value or cfg.llm_base_url
            cfg.deepinfra_api_key = api_key.value or ""
            cfg.olm_model = olm_model.value or cfg.olm_model
            cfg.olm_temperature = float(olm_temp.value)
            cfg.olm_max_tokens = int(olm_tokens.value or "4096")
            cfg.olm_prompt = olm_prompt.value or cfg.olm_prompt
            cfg.llm_parse_model = parse_model.value or cfg.llm_parse_model
            cfg.llm_parse_temperature = float(parse_temp.value)
            cfg.llm_parse_max_tokens = int(parse_tokens.value or "4096")
            cfg.llm_parse_prompt = parse_prompt.value or cfg.llm_parse_prompt
        except ValueError as e:
            save_msg.value = f"Invalid number: {e}"
            save_msg.color = ft.Colors.ERROR
            page.update()
            return
        if cfg.save():
            save_msg.value = "Configuration saved."
            save_msg.color = ft.Colors.GREEN
        else:
            save_msg.value = "Save failed."
            save_msg.color = ft.Colors.ERROR
        page.update()

    return ft.Container(
        content=ft.Column(
            [
                ft.Text("Configuration", size=22, weight=ft.FontWeight.W_600),
                base_url,
                api_key,
                ft.Divider(),
                ft.Text("VLM OCR", weight=ft.FontWeight.W_600),
                olm_model,
                olm_temp,
                olm_tokens,
                olm_prompt,
                ft.Divider(),
                ft.Text("LLM parse", weight=ft.FontWeight.W_600),
                parse_model,
                parse_temp,
                parse_tokens,
                parse_prompt,
                ft.FilledButton("Save configuration", icon=ft.Icons.SAVE, on_click=save_config),
                save_msg,
            ],
            spacing=12,
            scroll=ft.ScrollMode.AUTO,
        ),
        padding=16,
    )


def show_main_view(page: ft.Page, state: AppState) -> None:
    assert state.workspace_folder and state.configuration
    cfg = state.configuration

    def change_ws(_):
        state.workspace_folder = None
        state.configuration = None
        state.current_image_index = 0
        page.controls.clear()
        page.add(build_workspace_view(page, state))
        page.update()

    header = ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Column(
                            [
                                ft.Text(f"Workspace: {Path(state.workspace_folder).name}", size=20, weight=ft.FontWeight.W_600),
                                ft.Text(state.workspace_folder, size=12, color=ft.Colors.ON_SURFACE_VARIANT),
                                ft.Text(f"{len(cfg.image_files)} images", size=12),
                            ],
                            expand=True,
                        ),
                        ft.OutlinedButton("Change workspace", icon=ft.Icons.SWAP_HORIZ, on_click=change_ws),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.START,
                ),
            ],
            spacing=4,
        ),
        padding=ft.Padding.only(left=16, right=16, top=12, bottom=8),
    )

    tabs = ft.Tabs(
        length=3,
        selected_index=0,
        animation_duration=ft.Duration(milliseconds=200),
        content=ft.Column(
            [
                ft.TabBar(
                    tabs=[
                        ft.Tab(label="Overview"),
                        ft.Tab(label="Image viewer"),
                        ft.Tab(label="Configuration"),
                    ],
                ),
                ft.TabBarView(
                    controls=[
                        build_overview_tab(page, state),
                        build_image_tab(page, state),
                        build_config_tab(page, state),
                    ],
                    expand=True,
                ),
            ],
            expand=True,
            spacing=0,
        ),
        expand=True,
    )

    page.controls.clear()
    page.add(
        ft.Column(
            [
                header,
                ft.Divider(height=1),
                tabs,
            ],
            expand=True,
            spacing=0,
        )
    )
    page.update()


def main(page: ft.Page):
    page.title = "HerbAIrium"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 0
    page.window.min_width = 900
    page.window.min_height = 640

    state = AppState()
    # FilePicker must NOT be in overlay (breaks client). Register as service + parent page.
    fp = ft.FilePicker()
    fp._parent = weakref.ref(page)
    state.folder_picker = fp

    page.add(build_workspace_view(page, state))
    page.update()


if __name__ == "__main__":
    ft.run(main)
