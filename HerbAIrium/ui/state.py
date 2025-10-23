"""
Session state management for HerbAIrium.
Initializes and manages all session state variables.
"""
import streamlit as st
import json
import os
from pathlib import Path

from models.configuration import Configuration
# from models.metadata import Metadata


def initialize_session_state():
    """Initialize all session state variables with default values."""

    if 'workspace_folder' not in st.session_state:
        st.session_state.workspace_folder = None
    
    # Workspace and file management
    if 'current_image_index' not in st.session_state:
        st.session_state.current_image_index = 0


def save_configuration():
    """Save the configuration to the workspace folder."""
    st.session_state.configuration.save()

def reset_workspace():
    """Reset the workspace folder."""
    st.session_state.workspace_folder = None
    st.session_state.current_image_index = 0
    st.session_state.configuration = None


def load_configuration():
    """Load the configuration from the workspace folder."""
    return Configuration(workspace_folder=st.session_state.workspace_folder)
