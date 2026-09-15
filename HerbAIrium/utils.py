"""
Utility functions for HerbAIrium UI.
Includes file handling, OCR processing, and formatting helpers.
"""
import sys
import json

from pathlib import Path

# Add parent directory to path to import clients
from clients.deepinfra_client import DeepinfraClient
from models.metadata import Metadata
from models.configuration import Configuration


def process_ocr(
    image_path: str,
    configuration: Configuration
    ):
    """
    Process OCR on the given image using DeepinfraClient.
    
    Args:
        image_path: Path to the image file to process
        
    Returns:
        OCR result text
        
    Raises:
        Exception: If OCR processing fails
    """
    try:
        # Create client with current configuration
        client = DeepinfraClient(
            base_url=configuration.llm_base_url,
            api_key=configuration.deepinfra_api_key,
            model=configuration.olm_model,
            prompt=configuration.olm_prompt,
            max_tokens=configuration.olm_max_tokens,
        )
        
        # Run inference
        result = client.inference(
            pdf_path=image_path,
            temperature=configuration.olm_temperature
        )

        return result
    except Exception as e:
        raise Exception(f"OCR processing failed: {str(e)}")


def llm_parse_transcription(
    transcription: str,
    configuration: Configuration
    ):
    """
    Parse the transcription using the LLM.
    
    Args:
        transcription: The transcription to parse
        
    Returns:
        Parsed transcription
    """
    try:
        client = DeepinfraClient(
            base_url=configuration.llm_base_url,
            api_key=configuration.deepinfra_api_key,
            model=configuration.llm_parse_model,
            prompt=configuration.llm_parse_prompt,
            max_tokens=configuration.llm_parse_max_tokens,
        )
        result = client.inference(
            temperature=configuration.llm_parse_temperature,
            text=transcription
        )
        return result
    except Exception as e:
        raise Exception(f"LLM parsing failed: {str(e)}")

def json_to_dict(llm_result: str):
    """
    Parse Json from LLM result.
    
    Args:
        llm_result: The LLM result to parse
    """
    try:
        dict_result = json.loads(llm_result)
        return dict_result
    except Exception as e:
        return None


def catalog_number_from_image_path(image_path: str) -> str:
    return Path(image_path).stem


def format_file_size(size_bytes):
    """
    Format file size in bytes to human-readable string.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted size string (e.g., "1.5 MB")
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.2f} MB"


def process_ocr_and_save_results(
    image_path: str,
    configuration: Configuration
    ):
    """
    Process OCR and save the results to the database.
    
    Args:
        image_path: Path to the image file to process
    """
    save_ocr_result(image_path, process_ocr(image_path, configuration))


def save_ocr_result(image_path: str, ocr_result: str):
    metadata = Metadata(image_path=image_path)
    metadata.ocr_result = ocr_result
    if not metadata.save():
        raise OSError("Failed to save OCR metadata.")

def llm_parse_transcription_and_save_results(
    image_path: str,
    configuration: Configuration
    ):
    """
    Parse the transcription and save the results to the database.
    
    Args:
        image_path: Path to the image file to process
        configuration: Configuration
    """
    metadata = Metadata(image_path=image_path)
    transcription = metadata.ocr_result
    if transcription is not None:
        llm_parse_result = llm_parse_transcription(transcription, configuration)
        save_llm_parse_result(image_path, llm_parse_result)
    else:
        raise Exception("No OCR result found for this image.")


def save_llm_parse_result(image_path: str, llm_parse_result: str):
    json_result = json_to_dict(llm_parse_result)
    if not isinstance(json_result, dict):
        raise ValueError("LLM parsing returned invalid JSON.")

    metadata = Metadata(image_path=image_path)
    metadata.catalogNumber = catalog_number_from_image_path(image_path)
    metadata.recordNumber = json_result["recordNumber"]
    metadata.family = json_result["family"]
    metadata.scientificName = json_result["scientificName"]
    metadata.scientificNameAuthorship = json_result["scientificNameAuthorship"]
    metadata.eventDate = json_result["eventDate"]
    metadata.country = json_result["country"]
    metadata.stateProvince = json_result["stateProvince"]
    metadata.County = json_result["County"]
    metadata.Locality = json_result["Locality"]
    metadata.decimalLatitude = json_result["decimalLatitude"]
    metadata.decimalLongitude = json_result["decimalLongitude"]
    metadata.recordedBy = json_result["recordedBy"]
    metadata.associatedCollectors = json_result["associatedCollectors"]
    metadata.minimumElevationInMeters = json_result["minimumElevationInMeters"]
    metadata.ai_result = llm_parse_result
    if not metadata.save():
        raise OSError("Failed to save parsed metadata.")