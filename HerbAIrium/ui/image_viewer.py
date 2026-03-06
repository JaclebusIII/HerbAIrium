"""
Image viewer component.
Displays images with navigation controls and OCR processing functionality.
"""
import streamlit as st
from pathlib import Path
from PIL import Image, ImageOps
from streamlit_image_zoom import image_zoom

from models.metadata import Metadata
from utils import process_ocr, format_file_size, llm_parse_transcription_and_save_results

def render_navigation_controls():
    """Render the image navigation controls (First, Previous, Next, Last)."""
    col_nav1, col_nav2, col_nav3, col_nav4, col_nav5 = st.columns([1, 1, 3, 1, 1])
    
    with col_nav1:
        if st.button("⏮️ First", width='stretch', 
                     disabled=(st.session_state.current_image_index == 0)):
            st.session_state.current_image_index = 0
            st.rerun()
    
    with col_nav2:
        if st.button("⬅️ Previous", width='stretch', 
                     disabled=(st.session_state.current_image_index == 0)):
            st.session_state.current_image_index -= 1
            st.rerun()
    
    with col_nav3:
        st.markdown(
            f"<h3 style='text-align: center;'>Image {st.session_state.current_image_index + 1} "
            f"of {len(st.session_state.configuration.image_files)}</h3>",
            unsafe_allow_html=True
        )
    
    with col_nav4:
        if st.button("➡️ Next", width='stretch', 
                     disabled=(st.session_state.current_image_index >= len(st.session_state.configuration.image_files) - 1)):
            st.session_state.current_image_index += 1
            st.rerun()
    
    with col_nav5:
        if st.button("⏭️ Last", width='stretch', 
                     disabled=(st.session_state.current_image_index >= len(st.session_state.configuration.image_files) - 1)):
            st.session_state.current_image_index = len(st.session_state.configuration.image_files) - 1
            st.rerun()


def render_image_display():
    """
    Render the image display with metadata.
    
    Args:
        image_path: Path to the image file
    """
    file_path = Path(st.session_state.metadata.image_path)
    
    # Image info header
    st.subheader(f"🖼️ {file_path.name}")
    
    # File details
    file_size = file_path.stat().st_size
    size_str = format_file_size(file_size)
    
    col_image, col_meta = st.columns([1, 1])
    with col_image:
        image = Image.open(st.session_state.metadata.image_path)
        # resized_image = ImageOps.pad(image, (500, 500), color="white")
        image_zoom(
            image,
            size=(image.width//2, image.height//2),
            mode="default",
            keep_resolution=True,
        )
    with col_meta:
        ov_tab, ai_tab = col_meta.tabs(["Overview", "AI tools"])
        with ov_tab:
            st.metric("Dimensions", f"{image.width} × {image.height} px")
            st.metric("File Size", size_str)
            st.metric("Image Path", st.session_state.metadata.image_path)
            st.metric("Catalog Number", st.session_state.metadata.catalogNumber)
            st.metric("Record Number", st.session_state.metadata.recordNumber)
            st.metric("Family", st.session_state.metadata.family)
            st.metric("Scientific Name", st.session_state.metadata.scientificName)
            st.metric("Scientific Name Authorship", st.session_state.metadata.scientificNameAuthorship)
            st.metric("Event Date", st.session_state.metadata.eventDate)
            st.metric("Country", st.session_state.metadata.country)
            st.metric("State Province", st.session_state.metadata.stateProvince)
            st.metric("County", st.session_state.metadata.County)
            st.metric("Locality", st.session_state.metadata.Locality)
            st.metric("Decimal Latitude", st.session_state.metadata.decimalLatitude)
            st.metric("Decimal Longitude", st.session_state.metadata.decimalLongitude)
            st.metric("Recorded By", st.session_state.metadata.recordedBy)
            st.metric("Associated Collectors", ", ".join(st.session_state.metadata.associatedCollectors))
            st.metric("Minimum Elevation in Meters", st.session_state.metadata.minimumElevationInMeters)
        with ai_tab:
            render_action_buttons()
            render_ocr_results()
            render_llm_parse_results()


   
    




def render_action_buttons():
    """
    Render action buttons for OCR and AI analysis.
    
    Args:
        image_path: Path to the current image
    """
    col_action1, col_action2 = st.columns(2)

    api_configured = bool(st.session_state.configuration.deepinfra_api_key)
    
    with col_action1:
        if st.button("🔍 Process with OCR", width='stretch', disabled=not api_configured):
            if api_configured:
                st.session_state.ocr_processing = True
                with st.spinner("🔄 Processing image with OCR..."):
                    try:
                        st.session_state.metadata.ocr_result = process_ocr(st.session_state.metadata.image_path, st.session_state.configuration)
                        st.success("✅ OCR processing complete!")
                        st.session_state.metadata.save()
                    except Exception as e:
                        st.error(f"❌ {str(e)}")
            else:
                st.warning("⚠️ Please configure your API key in the Configuration tab first.")
        
        if not api_configured:
            st.caption("⚠️ API key required")
    
    with col_action2:
        if st.button("🤖 Parse with LLM", width='stretch', disabled=not api_configured):
            if api_configured:
                st.session_state.ai_processing = True
                with st.spinner("🔄 Parsing with LLM..."):
                    try:
                        st.session_state.metadata.ai_result = llm_parse_transcription_and_save_results(st.session_state.metadata.image_path, st.session_state.configuration)
                        st.success("✅ LLM parsing complete!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ {str(e)}")
            else:
                st.warning("⚠️ Please configure your API key in the Configuration tab first.")
        
        if not api_configured:
            st.caption("⚠️ API key required")

def render_ocr_results():
    """
    Render OCR results if available for the current image.
    
    Args:
        image_path: Path to the current image
    """
    st.divider()
    st.subheader("📄 OCR Transcription Results")
    
    if st.session_state.metadata.ocr_result:
        result_text = st.session_state.metadata.ocr_result
    else:
        result_text = "No OCR results available"
    
    # Display in an expandable section
    with st.expander("View Full Transcription", expanded=True):
        st.text_area(
            "Transcription",
            value=result_text,
            height=300,
            key=f"ocr_result_{st.session_state.metadata.image_path}_{hash(result_text)}",
            label_visibility="collapsed",
            disabled=True
        )
    
    # Add copy button and clear button
    col_res1, col_res2, col_res3 = st.columns([2, 1, 1])
    with col_res1:
        st.caption(f"Characters: {len(result_text)} | Words: {len(result_text.split())}")


def render_llm_parse_results():
    """
    Render LLM parse results if available for the current image.
    
    Args:
        image_path: Path to the current image
    """
    st.divider()
    st.subheader("📄 LLM Parse Results")
    
    if st.session_state.metadata.ai_result:
        result_text = st.session_state.metadata.ai_result
    else:
        result_text = "No LLM parse results available"
    
    # Display in an expandable section
    with st.expander("View Full Parsed Results", expanded=True):
        st.text_area(
            "Parsed Results",
            value=result_text,
            height=300,
            key=f"llm_parse_result_{st.session_state.metadata.image_path}_{hash(result_text)}",
            label_visibility="collapsed",
            disabled=True
        )   




def render_image_viewer():
    """Render the complete image viewer tab."""
    if st.session_state.configuration.image_files:
        # Navigation controls
        render_navigation_controls()
        st.divider()
        
        # Get current image path
        st.session_state.metadata = Metadata(image_path=st.session_state.configuration.image_files[st.session_state.current_image_index])       
        
        # try:
        # Display image and metadata
        render_image_display()
        st.divider()
                
        # except Exception as e:
        #     st.error(f"❌ Error loading image: {str(e)}")
    else:
        st.warning("⚠️ No image files found in the selected workspace.")

