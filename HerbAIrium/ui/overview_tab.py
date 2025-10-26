"""
Overview tab component.
Displays the overview of the workspace.
"""
import streamlit as st

def render_overview_tab():
    """Render the overview tab."""
    st.header("Overview")
    
    if st.button("Parse All Images", width='stretch'):
        pass