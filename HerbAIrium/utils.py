"""
Utility functions for HerbAIrium UI.
Includes file handling, OCR processing, and formatting helpers.
"""
import sys
import json

import streamlit as st
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
            prompt=configuration.olm_prompt
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
            prompt=configuration.llm_parse_prompt
        )
        result = client.inference(
            temperature=configuration.llm_parse_temperature,
            text=transcription
        )
        return result
    except Exception as e:
        raise Exception(f"LLM parsing failed: {str(e)}")

def parse_llm_results(llm_result: str):
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
    metadata = Metadata(image_path=image_path)
    metadata.ocr_result = process_ocr(image_path, configuration)
    metadata.save()

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
        if llm_parse_result is not None:
            metadata.llm_parse_result = llm_parse_result
            metadata.save()
    else:
        raise Exception("No OCR result found for this image.")