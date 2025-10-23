"""
Workspace folder selection component.
Handles the initial folder selection UI before the main workspace is loaded.
"""
import streamlit as st
import os
from utils import load_images_from_folder
from state import load_configuration


def render_workspace_selector():
    """Render the workspace folder selection interface."""
    st.header("📁 Select Workspace Folder")
    st.info("👇 Please select a folder containing your herbarium images to begin.")
    
    # Manual path entry
    custom_path = st.text_input("Workspace File Path", placeholder="/path/to/folder")
    if st.button("📂 Select This Folder", key="select_manual") and custom_path:
        if os.path.isdir(custom_path):
            images = load_images_from_folder(custom_path)
            if images:
                # Set workspace folder and load images
                st.session_state.workspace_folder = custom_path
                st.session_state.image_files = images
                st.session_state.current_image_index = 0
                
                # Auto-load saved configuration if it exists
                st.session_state.configuration = load_configuration()
                
                st.rerun()
            else:
                st.warning("⚠️ No image files found in this folder.")
        else:
            st.error("❌ Invalid directory path.")
    
    st.divider()

