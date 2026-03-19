from __future__ import annotations

from dataclasses import dataclass

import flet as ft

from models.configuration import Configuration


@dataclass
class AppState:
    workspace_folder: str | None = None
    configuration: Configuration | None = None
    current_image_index: int = 0
    folder_picker: ft.FilePicker | None = None
