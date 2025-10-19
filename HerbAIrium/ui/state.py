"""
Session state management for HerbAIrium.
Initializes and manages all session state variables.
"""
import streamlit as st
import json
import os
from pathlib import Path


def initialize_session_state():
    """Initialize all session state variables with default values."""
    
    # Workspace and file management
    if 'workspace_folder' not in st.session_state:
        st.session_state.workspace_folder = None
    if 'image_files' not in st.session_state:
        st.session_state.image_files = []
    if 'current_image_index' not in st.session_state:
        st.session_state.current_image_index = 0
    if 'browse_directory' not in st.session_state:
        st.session_state.browse_directory = str(Path.home())
    
    # OLM configuration parameters
    if 'olm_base_url' not in st.session_state:
        st.session_state.olm_base_url = "https://api.deepinfra.com/v1/openai/chat/completions"
    if 'olm_api_key' not in st.session_state:
        st.session_state.olm_api_key = ""
    if 'olm_model' not in st.session_state:
        st.session_state.olm_model = "allenai/olmOCR-7B-0825"
    if 'olm_prompt' not in st.session_state:
        st.session_state.olm_prompt = "Please extract all text from this herbarium specimen image."
    if 'olm_temperature' not in st.session_state:
        st.session_state.olm_temperature = 0.7
    if 'olm_max_tokens' not in st.session_state:
        st.session_state.olm_max_tokens = 4096
    
    # OCR results storage (indexed by image path)
    if 'ocr_results' not in st.session_state:
        st.session_state.ocr_results = {}
    if 'ocr_processing' not in st.session_state:
        st.session_state.ocr_processing = False


def reset_workspace():
    """Reset workspace-related session state."""
    st.session_state.workspace_folder = None
    st.session_state.image_files = []
    st.session_state.current_image_index = 0


def reset_olm_config():
    """Reset OLM configuration to defaults."""
    st.session_state.olm_base_url = "https://api.deepinfra.com/v1/openai/chat/completions"
    st.session_state.olm_api_key = ""
    st.session_state.olm_model = "allenai/olmOCR-7B-0825"
    st.session_state.olm_temperature = 0.7
    st.session_state.olm_max_tokens = 4096
    st.session_state.olm_prompt = "Please extract all text from this herbarium specimen image."


def get_config_path():
    """Get the path to the configuration file for the current workspace."""
    if st.session_state.workspace_folder:
        return os.path.join(st.session_state.workspace_folder, ".herbairium_config.json")
    return None


def save_configuration():
    """Save the current OLM configuration to a file in the workspace folder."""
    config_path = get_config_path()
    if not config_path:
        raise ValueError("No workspace folder selected")
    
    # Only save configuration-related settings (not runtime state like image_files)
    config_data = {
        "olm_base_url": st.session_state.olm_base_url,
        "olm_model": st.session_state.olm_model,
        "olm_prompt": st.session_state.olm_prompt,
        "olm_temperature": st.session_state.olm_temperature,
        "olm_max_tokens": st.session_state.olm_max_tokens,
        "olm_api_key": st.session_state.olm_api_key,
    }
    
    try:
        with open(config_path, "w") as f:
            json.dump(config_data, f, indent=2)
        return True
    except Exception as e:
        st.error(f"Failed to save configuration: {str(e)}")
        return False


def load_configuration():
    """Load the configuration from a file in the workspace folder."""
    config_path = get_config_path()
    if not config_path or not os.path.exists(config_path):
        return False
    
    try:
        with open(config_path, "r") as f:
            config_data = json.load(f)
        # Update session state with loaded configuration
        if "olm_base_url" in config_data:
            st.session_state.olm_base_url = config_data["olm_base_url"]
        if "olm_api_key" in config_data:
            st.session_state.olm_api_key = config_data["olm_api_key"]
        if "olm_model" in config_data:
            st.session_state.olm_model = config_data["olm_model"]
        if "olm_prompt" in config_data:
            st.session_state.olm_prompt = config_data["olm_prompt"]
        if "olm_temperature" in config_data:
            st.session_state.olm_temperature = config_data["olm_temperature"]
        if "olm_max_tokens" in config_data:
            st.session_state.olm_max_tokens = config_data["olm_max_tokens"]
        
        return True
    except Exception as e:
        st.error(f"Failed to load configuration: {str(e)}")
        return False


def has_saved_configuration():
    """Check if a saved configuration exists for the current workspace."""
    config_path = get_config_path()
    return config_path and os.path.exists(config_path)