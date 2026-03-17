import os
import json
from pathlib import Path

from typing import Any, Optional

from pydantic_settings import BaseSettings
from pydantic import ConfigDict


def _blank(v: Any) -> bool:
    return v is None or (isinstance(v, str) and not v.strip())


def _sanitize_metadata_dict(data: dict) -> dict:
    """Sidecar JSON may have '' or invalid types; coerce before Pydantic validation."""
    d = dict(data)

    def opt_int(key: str) -> None:
        if key not in d:
            return
        v = d[key]
        if _blank(v):
            d[key] = None
            return
        if isinstance(v, bool):
            d[key] = None
            return
        if isinstance(v, int):
            return
        try:
            d[key] = int(float(str(v).strip()))
        except (TypeError, ValueError):
            d[key] = None

    def opt_float(key: str) -> None:
        if key not in d:
            return
        v = d[key]
        if _blank(v):
            d[key] = None
            return
        try:
            d[key] = float(str(v).strip())
        except (TypeError, ValueError):
            d[key] = None

    for k in ("recordNumber", "minimumElevationInMeters"):
        opt_int(k)
    for k in ("decimalLatitude", "decimalLongitude"):
        opt_float(k)

    if "catalogNumber" in d and d["catalogNumber"] is not None:
        c = d["catalogNumber"]
        d["catalogNumber"] = None if _blank(c) else str(c).strip() or None

    ac = d.get("associatedCollectors")
    if ac is not None and not isinstance(ac, list):
        if isinstance(ac, str) and ac.strip():
            d["associatedCollectors"] = [ac.strip()]
        else:
            d["associatedCollectors"] = None

    return d


class Metadata(BaseSettings):
    model_config = ConfigDict(
        extra='allow'
    )

    image_path: str
    ocr_result: Optional[str] = None
    ai_result: Optional[str] = None

    catalogNumber: Optional[str] = None
    recordNumber: Optional[int] = None
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
    minimumElevationInMeters: Optional[int] = None


    def __init__(self, image_path: str, **kwargs):
        image_path_obj = Path(image_path)
        metadata_path = str(image_path_obj.with_suffix('.json'))

        if os.path.exists(metadata_path):
            with open(metadata_path, 'r') as f:
                json_data = _sanitize_metadata_dict(json.load(f))
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