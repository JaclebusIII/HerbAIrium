from io import BytesIO
from pathlib import Path

import flet as ft
from PIL import Image as PILImage

from models.configuration import Configuration


def toast(page: ft.Page, message: str) -> None:
    page.show_dialog(ft.SnackBar(content=ft.Text(message)))


def api_key_set(cfg: Configuration) -> bool:
    return bool((cfg.deepinfra_api_key or "").strip())


def image_bytes_for_viewer(path: str) -> bytes:
    p = Path(path)
    try:
        with PILImage.open(p) as im:
            im.load()
            m = 2048
            if max(im.size) > m:
                im = im.copy()
                im.thumbnail((m, m), PILImage.Resampling.LANCZOS)
            buf = BytesIO()
            if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
                im.convert("RGBA").save(buf, format="PNG", optimize=True)
            else:
                im.convert("RGB").save(buf, format="JPEG", quality=90, optimize=True)
            return buf.getvalue()
    except Exception:
        return p.read_bytes()
