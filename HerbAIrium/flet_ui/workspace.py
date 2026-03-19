from collections.abc import Callable
from pathlib import Path

import flet as ft

from models.configuration import Configuration

from .state import AppState


def build_workspace_view(
    page: ft.Page, state: AppState, open_main: Callable[[], None]
) -> ft.Control:
    path_field = ft.TextField(
        label="Workspace folder path",
        hint_text="/path/to/herbarium/images",
        expand=True,
    )
    hint = ft.Text(color=ft.Colors.ERROR)

    async def open_folder(_):
        if page.web:
            hint.value = "In the browser, type the folder path below."
            page.update()
            return
        picker = state.folder_picker
        if picker is None:
            hint.value = "Folder picker not ready."
            page.update()
            return
        try:
            chosen = await picker.get_directory_path(dialog_title="Select workspace folder")
        except ft.FletUnsupportedPlatformException:
            hint.value = "Folder browse not available; type the path below."
            page.update()
            return
        except Exception as ex:
            hint.value = str(ex)
            page.update()
            return
        if not chosen:
            page.update()
            return
        state.workspace_folder = chosen
        state.configuration = Configuration(workspace_folder=chosen)
        state.current_image_index = 0
        open_main()
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
        open_main()

    return ft.Container(
        content=ft.Column(
            [
                ft.Text("HerbAIrium", size=28, weight=ft.FontWeight.BOLD),
                ft.Text("Open a folder of herbarium images."),
                ft.Row(
                    [
                        path_field,
                        ft.Button(content="Browse…", icon=ft.Icons.FOLDER_OPEN, on_click=open_folder),
                    ],
                ),
                ft.Button(content="Open this folder", icon=ft.Icons.LOGIN, on_click=use_path),
                hint,
            ],
            spacing=16,
            tight=True,
        ),
        padding=24,
    )
