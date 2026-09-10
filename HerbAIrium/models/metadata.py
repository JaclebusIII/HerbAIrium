import os
import json
from pathlib import Path

from PIL import Image
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import ConfigDict, field_validator


class Metadata(BaseSettings):
    model_config = ConfigDict(
        extra='allow',
        validate_assignment=True,
    )

    image_path: str
    ocr_result: Optional[str] = None
    ai_result: Optional[str] = None

    catalogNumber: Optional[str] = None
    recordNumber: Optional[str | int] = None
    family: Optional[str] = None
    scientificName: Optional[str] = None
    scientificNameAuthorship: Optional[str] = None
    eventDate: Optional[str] = None
    country: Optional[str] = None
    stateProvince: Optional[str] = None
    County: Optional[str] = None
    Locality: Optional[str] = None
    decimalLatitude: Optional[float] = None
    decimalLongitude: Optional[float] = None
    recordedBy: Optional[str] = None
    associatedCollectors: Optional[list[str]] = None
    minimumElevationInMeters: Optional[float] = None

    @field_validator(
        "decimalLatitude",
        "decimalLongitude",
        "minimumElevationInMeters",
        mode="before",
    )
    @classmethod
    def blank_numeric_value_as_none(cls, value):
        if isinstance(value, str) and not value.strip():
            return None
        return value

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