"""
HerbAIrium - Main Application
A Streamlit-based herbarium image viewer and OCR processor.
"""
import streamlit as st
from pathlib import Path

# Import application modules
from state import initialize_session_state, reset_workspace
from workspace_selector import render_workspace_selector
from image_viewer import render_image_viewer
from configuration_tab import render_configuration_tab

# Page configuration
st.set_page_config(page_title="HerbAIrium", layout="wide")

# Initialize session state
initialize_session_state()

# App header
st.title("HerbAIrium")
st.write("Welcome to HerbAIrium, your personal herbarium assistant.")
st.divider()

# Main application logic
if st.session_state.workspace_folder is None:
    # Show workspace selector if no workspace is selected
    render_workspace_selector()
else:
    # Show main workspace interface with tabs
    st.header(f"📂 Workspace: `{Path(st.session_state.workspace_folder).name}`")
    
    # Workspace header with info and change button
    col_header1, col_header2 = st.columns([3, 1])
    with col_header1:
        st.caption(f"Full path: `{st.session_state.workspace_folder}`")
        st.caption(f"Total images: {len(st.session_state.configuration.image_files)}")
    with col_header2:
        if st.button("🔄 Change Workspace", width='stretch'):
            reset_workspace()
            st.rerun()
    
    st.divider()
    
    # Create tabs
    tab1, tab2 = st.tabs(["🖼️ Image Viewer", "⚙️ Configuration"])
    
    with tab1:
        render_image_viewer()
    
    with tab2:
        render_configuration_tab()
