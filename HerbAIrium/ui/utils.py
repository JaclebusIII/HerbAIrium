"""
Utility functions for HerbAIrium UI.
Includes file handling, OCR processing, and formatting helpers.
"""
import sys
import json

import streamlit as st
from pathlib import Path

# Add parent directory to path to import clients
sys.path.append(str(Path(__file__).parent.parent))
from clients.deepinfra_client import DeepinfraClient


def load_images_from_folder(folder_path):
    """
    Load all image files from the specified folder.
    
    Args:
        folder_path: Path to the folder to scan for images
        
    Returns:
        List of image file paths (sorted)
    """
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'}
    folder = Path(folder_path)
    
    if not folder.exists() or not folder.is_dir():
        return []
    
    try:
        files = sorted([
            str(f) for f in folder.iterdir() 
            if f.is_file() and f.suffix.lower() in image_extensions
        ])
        return files
    except PermissionError:
        st.error("❌ Permission denied to access this directory.")
        return []
    except Exception as e:
        st.error(f"❌ Error reading directory: {str(e)}")
        return []


def process_ocr(image_path):
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
            base_url=st.session_state.configuration.llm_base_url,
            api_key=st.session_state.configuration.deepinfra_api_key,
            model=st.session_state.configuration.olm_model,
            prompt=st.session_state.configuration.olm_prompt
        )
        
        # Run inference
        result = client.inference(
            pdf_path=image_path,
            temperature=st.session_state.configuration.olm_temperature
        )

        return result
    except Exception as e:
        raise Exception(f"OCR processing failed: {str(e)}")


def llm_parse_transcription(transcription: str):
    """
    Parse the transcription using the LLM.
    
    Args:
        transcription: The transcription to parse
        
    Returns:
        Parsed transcription
    """
    try:
        client = DeepinfraClient(
            base_url=st.session_state.configuration.llm_base_url,
            api_key=st.session_state.configuration.deepinfra_api_key,
            model=st.session_state.configuration.llm_parse_model,
            prompt=st.session_state.configuration.llm_parse_prompt
        )
        result = client.inference(
            temperature=st.session_state.configuration.llm_parse_temperature,
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