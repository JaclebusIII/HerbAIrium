import os
import json
from pathlib import Path

from PIL import Image
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import ConfigDict, Field


class Metadata(BaseSettings):
    model_config = ConfigDict(
        extra='allow'
    )

    image_path: str
    ocr_result: Optional[str] = None
    ai_result: Optional[str] = None

    collector_name: Optional[str] = None
    location: Optional[str] = None
    family: Optional[str] = None
    collection_date: Optional[str] = None


    def __init__(self, image_path: str, **kwargs):
        image_path_obj = Path(image_path)
        metadata_path = str(image_path_obj.with_suffix('.json'))

        if os.path.exists(metadata_path):
            with open(metadata_path, 'r') as f:
                json_data = json.load(f)
                kwargs.update(json_data)

        kwargs["image_path"] = image_path

        super().__init__(
            **kwargs
        )
        self.metadata_path = metadata_path

    def save(self) -> bool:
        try:
            with open(self.metadata_path, 'w') as f:
                json.dump(self.model_dump(), f)
            return True
        except Exception as e:
            return False