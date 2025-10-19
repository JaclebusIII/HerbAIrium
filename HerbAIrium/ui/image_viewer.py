"""
Image viewer component.
Displays images with navigation controls and OCR processing functionality.
"""
import streamlit as st
from pathlib import Path
from PIL import Image
from utils import process_ocr, format_file_size


def render_navigation_controls():
    """Render the image navigation controls (First, Previous, Next, Last)."""
    col_nav1, col_nav2, col_nav3, col_nav4, col_nav5 = st.columns([1, 1, 3, 1, 1])
    
    with col_nav1:
        if st.button("⏮️ First", use_container_width=True, 
                     disabled=(st.session_state.current_image_index == 0)):
            st.session_state.current_image_index = 0
            st.rerun()
    
    with col_nav2:
        if st.button("⬅️ Previous", use_container_width=True, 
                     disabled=(st.session_state.current_image_index == 0)):
            st.session_state.current_image_index -= 1
            st.rerun()
    
    with col_nav3:
        st.markdown(
            f"<h3 style='text-align: center;'>Image {st.session_state.current_image_index + 1} "
            f"of {len(st.session_state.image_files)}</h3>",
            unsafe_allow_html=True
        )
    
    with col_nav4:
        if st.button("➡️ Next", use_container_width=True, 
                     disabled=(st.session_state.current_image_index >= len(st.session_state.image_files) - 1)):
            st.session_state.current_image_index += 1
            st.rerun()
    
    with col_nav5:
        if st.button("⏭️ Last", use_container_width=True, 
                     disabled=(st.session_state.current_image_index >= len(st.session_state.image_files) - 1)):
            st.session_state.current_image_index = len(st.session_state.image_files) - 1
            st.rerun()


def render_image_display(image_path):
    """
    Render the image display with metadata.
    
    Args:
        image_path: Path to the image file
    """
    file_path = Path(image_path)
    
    # Image info header
    st.subheader(f"🖼️ {file_path.name}")
    
    # File details
    file_size = file_path.stat().st_size
    size_str = format_file_size(file_size)
    
    # Display image
    # make image smaller to 1024x1024
    image = Image.open(image_path)
    image.thumbnail((1024, 1024))
    st.image(image, use_container_width=False)
    
    # Image metadata
    col_meta1, col_meta2, col_meta3 = st.columns(3)
    with col_meta1:
        st.metric("Dimensions", f"{image.width} × {image.height} px")
    with col_meta2:
        st.metric("Format", image.format)
    with col_meta3:
        st.metric("File Size", size_str)


def render_action_buttons(image_path):
    """
    Render action buttons for OCR and AI analysis.
    
    Args:
        image_path: Path to the current image
    """
    col_action1, col_action2 = st.columns(2)
    
    with col_action1:
        # Check if API key is configured
        api_configured = bool(st.session_state.olm_api_key)
        
        if st.button("🔍 Process with OCR", use_container_width=True, disabled=not api_configured):
            if api_configured:
                st.session_state.ocr_processing = True
                with st.spinner("🔄 Processing image with OCR..."):
                    try:
                        result = process_ocr(image_path)
                        st.session_state.ocr_results[image_path] = result
                        st.session_state.ocr_processing = False
                        st.success("✅ OCR processing complete!")
                        st.rerun()
                    except Exception as e:
                        st.session_state.ocr_processing = False
                        st.error(f"❌ {str(e)}")
            else:
                st.warning("⚠️ Please configure your API key in the Configuration tab first.")
        
        if not api_configured:
            st.caption("⚠️ API key required")
    
    with col_action2:
        if st.button("🤖 Analyze with AI", use_container_width=True):
            st.info("AI analysis will be implemented here")


def render_ocr_results(image_path):
    """
    Render OCR results if available for the current image.
    
    Args:
        image_path: Path to the current image
    """
    if image_path in st.session_state.ocr_results:
        st.divider()
        st.subheader("📄 OCR Transcription Results")
        
        result_text = st.session_state.ocr_results[image_path]
        
        # Display in an expandable section
        with st.expander("View Full Transcription", expanded=True):
            st.text_area(
                "Transcription",
                value=result_text,
                height=300,
                key=f"ocr_result_{st.session_state.current_image_index}",
                label_visibility="collapsed"
            )
        
        # Add copy button and clear button
        col_res1, col_res2, col_res3 = st.columns([2, 1, 1])
        with col_res1:
            st.caption(f"Characters: {len(result_text)} | Words: {len(result_text.split())}")
        with col_res2:
            if st.button("📋 Copy to Clipboard", use_container_width=True):
                st.code(result_text, language=None)
                st.info("💡 Select and copy the text above")
        with col_res3:
            if st.button("🗑️ Clear Result", use_container_width=True):
                del st.session_state.ocr_results[image_path]
                st.rerun()


def render_image_viewer():
    """Render the complete image viewer tab."""
    if st.session_state.image_files:
        # Navigation controls
        render_navigation_controls()
        st.divider()
        
        # Get current image path
        current_image_path = st.session_state.image_files[st.session_state.current_image_index]
        
        try:
            # Display image and metadata
            render_image_display(current_image_path)
            st.divider()
            
            # Action buttons
            render_action_buttons(current_image_path)
            
            # OCR results (if available)
            render_ocr_results(current_image_path)
            
        except Exception as e:
            st.error(f"❌ Error loading image: {str(e)}")
    else:
        st.warning("⚠️ No image files found in the selected workspace.")

