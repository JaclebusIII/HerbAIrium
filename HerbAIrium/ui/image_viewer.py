"""
Image viewer component.
Displays images with navigation controls and OCR processing functionality.
"""
import streamlit as st
from pathlib import Path
from PIL import Image
from utils import process_ocr, format_file_size, llm_parse_transcription
from PIL import ImageOps


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
    
    col_image, col_meta = st.columns([1, 2])
    with col_image:
        image = Image.open(image_path)
        resized_image = ImageOps.pad(image, (500, 500), color="white")
        st.image(resized_image, use_container_width=True)
    with col_meta:
        ov_tab, ai_tab = col_meta.tabs(["Overview", "AI tools"])
        with ov_tab:
            st.metric("Dimensions", f"{image.width} × {image.height} px")
            st.metric("File Size", size_str)
            
        with ai_tab:
            render_action_buttons(image_path)
            render_ocr_results(image_path)
            render_llm_parse_results(image_path)


   
    




def render_action_buttons(image_path):
    """
    Render action buttons for OCR and AI analysis.
    
    Args:
        image_path: Path to the current image
    """
    col_action1, col_action2 = st.columns(2)
    
    with col_action1:
        # Check if API key is configured
        api_configured = bool(st.session_state.deepinfra_api_key)
        
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
        api_configured = bool(st.session_state.deepinfra_api_key)
        if st.button("🤖 Analyze with AI", use_container_width=True, disabled=not api_configured):
            if api_configured:
                st.session_state.ai_processing = True
                with st.spinner("🔄 Analyzing image with AI..."):
                    try:
                        result = llm_parse_transcription(st.session_state.ocr_results[image_path])
                        st.session_state.ai_results[image_path] = result
                        st.session_state.ai_processing = False
                        st.success("✅ AI analysis complete!")
            
                    except Exception as e:
                        st.session_state.ai_processing = False
                        st.error(f"❌ {str(e)}")
            else:
                st.warning("⚠️ Please configure your API key in the Configuration tab first.")
        
        if not api_configured:
            st.caption("⚠️ API key required")

def render_ocr_results(image_path):
    """
    Render OCR results if available for the current image.
    
    Args:
        image_path: Path to the current image
    """
    st.divider()
    st.subheader("📄 OCR Transcription Results")
    
    if image_path in st.session_state.ocr_results:
        result_text = st.session_state.ocr_results[image_path]
    else:
        result_text = "No OCR results available"
    
    # Display in an expandable section
    with st.expander("View Full Transcription", expanded=True):
        st.text_area(
            "Transcription",
            value=result_text,
            height=300,
            key=f"ocr_result_{image_path}_{hash(result_text)}",
            label_visibility="collapsed",
            disabled=True
        )
    
    # Add copy button and clear button
    col_res1, col_res2, col_res3 = st.columns([2, 1, 1])
    with col_res1:
        st.caption(f"Characters: {len(result_text)} | Words: {len(result_text.split())}")


def render_llm_parse_results(image_path):
    """
    Render LLM parse results if available for the current image.
    
    Args:
        image_path: Path to the current image
    """
    st.divider()
    st.subheader("📄 LLM Parse Results")
    
    if image_path in st.session_state.ai_results:
        result_text = st.session_state.ai_results[image_path]
    else:
        result_text = "No LLM parse results available"
    
    # Display in an expandable section
    with st.expander("View Full Parsed Results", expanded=True):
        st.text_area(
            "Parsed Results",
            value=result_text,
            height=300,
            key=f"llm_parse_result_{image_path}_{hash(result_text)}",
            label_visibility="collapsed",
            disabled=True
        )




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
            
        except Exception as e:
            st.error(f"❌ Error loading image: {str(e)}")
    else:
        st.warning("⚠️ No image files found in the selected workspace.")

