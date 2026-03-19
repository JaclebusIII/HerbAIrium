import json

from clients.deepinfra_client import DeepinfraClient
from models.configuration import Configuration
from models.metadata import Metadata


def process_ocr(image_path: str, configuration: Configuration):
    try:
        client = DeepinfraClient(
            base_url=configuration.llm_base_url,
            api_key=configuration.deepinfra_api_key,
            model=configuration.olm_model,
            prompt=configuration.olm_prompt,
        )
        return client.inference(pdf_path=image_path, temperature=configuration.olm_temperature)
    except Exception as e:
        raise Exception(f"OCR processing failed: {str(e)}") from e


def llm_parse_transcription(transcription: str, configuration: Configuration):
    try:
        client = DeepinfraClient(
            base_url=configuration.llm_base_url,
            api_key=configuration.deepinfra_api_key,
            model=configuration.llm_parse_model,
            prompt=configuration.llm_parse_prompt,
        )
        return client.inference(
            temperature=configuration.llm_parse_temperature,
            text=transcription,
        )
    except Exception as e:
        raise Exception(f"LLM parsing failed: {str(e)}") from e


def json_to_dict(llm_result: str):
    try:
        return json.loads(llm_result)
    except Exception:
        return None


def _blank_json_value(v) -> bool:
    return v is None or (isinstance(v, str) and not v.strip())


def _json_opt_int(v):
    if _blank_json_value(v):
        return None
    try:
        return int(float(str(v).strip()))
    except (TypeError, ValueError):
        return None


def _json_opt_float(v):
    if _blank_json_value(v):
        return None
    try:
        return float(str(v).strip())
    except (TypeError, ValueError):
        return None


def _json_opt_str(v):
    if v is None:
        return None
    s = str(v).strip()
    return s if s else None


def _json_collectors(v):
    if _blank_json_value(v):
        return None
    if isinstance(v, list):
        out = [str(x).strip() for x in v if x is not None and str(x).strip()]
        return out or None
    if isinstance(v, str) and v.strip():
        return [v.strip()]
    return None


def apply_parsed_json_to_metadata(metadata: Metadata, d: dict) -> None:
    c = d.get("catalogNumber")
    metadata.catalogNumber = None if _blank_json_value(c) else (str(c).strip() or None)
    metadata.recordNumber = _json_opt_int(d.get("recordNumber"))
    metadata.family = _json_opt_str(d.get("family"))
    metadata.scientificName = _json_opt_str(d.get("scientificName"))
    metadata.scientificNameAuthorship = _json_opt_str(d.get("scientificNameAuthorship"))
    metadata.eventDate = _json_opt_str(d.get("eventDate"))
    metadata.country = _json_opt_str(d.get("country"))
    metadata.stateProvince = _json_opt_str(d.get("stateProvince"))
    metadata.County = _json_opt_str(d.get("County"))
    metadata.Locality = _json_opt_str(d.get("Locality"))
    metadata.decimalLatitude = _json_opt_float(d.get("decimalLatitude"))
    metadata.decimalLongitude = _json_opt_float(d.get("decimalLongitude"))
    metadata.recordedBy = _json_opt_str(d.get("recordedBy"))
    metadata.associatedCollectors = _json_collectors(d.get("associatedCollectors"))
    metadata.minimumElevationInMeters = _json_opt_int(d.get("minimumElevationInMeters"))


def format_file_size(size_bytes):
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f} KB"
    return f"{size_bytes / (1024 * 1024):.2f} MB"


def process_ocr_and_save_results(image_path: str, configuration: Configuration):
    metadata = Metadata(image_path=image_path)
    metadata.ocr_result = process_ocr(image_path, configuration)
    metadata.save()


def llm_parse_transcription_and_save_results(image_path: str, configuration: Configuration):
    metadata = Metadata(image_path=image_path)
    transcription = metadata.ocr_result
    if transcription is None:
        raise Exception("No OCR result found for this image.")
    llm_parse_result = llm_parse_transcription(transcription, configuration)
    metadata.ai_result = llm_parse_result
    if llm_parse_result is not None:
        json_result = json_to_dict(llm_parse_result)
        if isinstance(json_result, dict):
            apply_parsed_json_to_metadata(metadata, json_result)
    metadata.save()
