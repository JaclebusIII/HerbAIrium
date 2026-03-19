import asyncio
from pathlib import Path

import flet as ft

from .batch import run_llm_on_image, run_ocr_on_image
from .helpers import api_key_set
from .state import AppState


def build_overview_tab(page: ft.Page, state: AppState) -> ft.Control:
    pb = ft.ProgressBar(width=480, visible=False)
    status = ft.Text()
    summary = ft.Markdown()
    parse_btn = ft.FilledButton("Parse all images (OCR + LLM)")

    async def on_parse(_):
        cfg = state.configuration
        assert cfg is not None
        if not api_key_set(cfg):
            status.value = "Set API key in Configuration, then Save."
            page.update()
            return
        files = cfg.image_files
        if not files:
            status.value = "No images in workspace."
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
                r = await loop.run_in_executor(None, lambda ip=img: run_ocr_on_image(ip, cfg))
            async with lock:
                ocr_done[0] += 1
                d = ocr_done[0]
                pb.value = min(0.5, (d / n) * 0.5)
                status.value = f"OCR {d}/{n}: {Path(img).name}"
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
                    r = await loop.run_in_executor(None, lambda ip=img: run_llm_on_image(ip, cfg))
                async with lock:
                    llm_done[0] += 1
                    d = llm_done[0]
                    pb.value = 0.5 + min(0.5, (d / m) * 0.5)
                    status.value = f"LLM {d}/{m}: {Path(img).name}"
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
            f"- **OCR:** {len(ocr_ok)} ok, {len(ocr_fail)} failed.",
            f"- **LLM:** {len(llm_ok)} ok, {len(llm_fail)} failed.",
        ]
        if ocr_fail or llm_fail:
            lines.append("\n**Failures:**\n")
            for name, err in ocr_fail + llm_fail:
                lines.append(f"- `{name}`: {err}\n")
        else:
            lines.append("\nDone.")
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
