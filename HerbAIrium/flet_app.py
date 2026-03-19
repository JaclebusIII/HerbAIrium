from __future__ import annotations

import sys
import weakref
from pathlib import Path

_root = Path(__file__).resolve().parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

import flet as ft

from flet_ui.main_view import show_main_view
from flet_ui.state import AppState
from flet_ui.workspace import build_workspace_view


def main(page: ft.Page):
    page.title = "HerbAIrium"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 0
    page.window.min_width = 900
    page.window.min_height = 640

    state = AppState()
    fp = ft.FilePicker()
    fp._parent = weakref.ref(page)
    state.folder_picker = fp

    def open_main():
        show_main_view(page, state)

    page.add(build_workspace_view(page, state, open_main))
    page.update()


if __name__ == "__main__":
    ft.run(main)
