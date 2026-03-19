from pathlib import Path

import flet as ft

from .state import AppState
from .tab_config import build_config_tab
from .tab_image import build_image_tab
from .tab_overview import build_overview_tab
from .workspace import build_workspace_view


def show_main_view(page: ft.Page, state: AppState) -> None:
    assert state.workspace_folder and state.configuration
    cfg = state.configuration

    def open_main():
        show_main_view(page, state)

    def change_ws(_):
        state.workspace_folder = None
        state.configuration = None
        state.current_image_index = 0
        page.controls.clear()
        page.add(build_workspace_view(page, state, open_main))
        page.update()

    header = ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Column(
                            [
                                ft.Text(
                                    f"Workspace: {Path(state.workspace_folder).name}",
                                    size=20,
                                    weight=ft.FontWeight.W_600,
                                ),
                                ft.Text(state.workspace_folder, size=12, color=ft.Colors.ON_SURFACE_VARIANT),
                                ft.Text(f"{len(cfg.image_files)} images", size=12),
                            ],
                            expand=True,
                        ),
                        ft.OutlinedButton(
                            "Change workspace", icon=ft.Icons.SWAP_HORIZ, on_click=change_ws
                        ),
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
    page.add(ft.Column([header, ft.Divider(height=1), tabs], expand=True, spacing=0))
    page.update()
