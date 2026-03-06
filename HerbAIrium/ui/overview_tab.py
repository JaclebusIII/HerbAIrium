"""
Overview tab component.
Displays the overview of the workspace.
"""
import streamlit as st
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from utils import process_ocr_and_save_results, llm_parse_transcription_and_save_results


def process_single_image_ocr(image_path, configuration):
    """Process OCR for a single image. Returns (image_path, success, error)."""
    try:
        process_ocr_and_save_results(image_path, configuration)
        return (image_path, True, None)
    except Exception as e:
        return (image_path, False, str(e))


def process_single_image_llm(image_path, configuration):
    """Process LLM parsing for a single image. Returns (image_path, success, error)."""
    try:
        llm_parse_transcription_and_save_results(image_path, configuration)
        return (image_path, True, None)
    except Exception as e:
        return (image_path, False, str(e))


def render_overview_tab():
    """Render the overview tab."""
    st.header("Overview")
    
    api_configured = bool(st.session_state.configuration.deepinfra_api_key)
    
    if st.button("Parse All Images", width='stretch', disabled=not api_configured):
        if api_configured:
            image_files = st.session_state.configuration.image_files
            configuration = st.session_state.configuration
            
            if not image_files:
                st.warning("⚠️ No image files found in the workspace.")
                return
            
            # Initialize progress tracking
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            total_images = len(image_files)
            
            # Phase 1: OCR Processing
            ocr_successful = []
            ocr_failed = []
            
            with ThreadPoolExecutor(max_workers=5) as executor:
                # Submit all OCR tasks
                ocr_futures = {executor.submit(process_single_image_ocr, img, configuration): img 
                              for img in image_files}
                
                # Track progress as OCR tasks complete
                completed_ocr = 0
                for future in as_completed(ocr_futures):
                    completed_ocr += 1
                    image_path = ocr_futures[future]
                    
                    # Update progress bar (Phase 1 is 50% of total work)
                    progress = (completed_ocr / total_images) * 0.5
                    progress_bar.progress(progress)
                    status_text.text(f"Phase 1: OCR - Processing {completed_ocr} of {total_images}: {Path(image_path).name}")
                    
                    # Get result
                    image_path_result, success, error = future.result()
                    if success:
                        ocr_successful.append(image_path_result)
                    else:
                        ocr_failed.append((Path(image_path_result).name, error))
            
            # Phase 2: LLM Processing (only for successful OCR images)
            llm_successful = []
            llm_failed = []
            
            if ocr_successful:
                with ThreadPoolExecutor(max_workers=5) as executor:
                    # Submit all LLM tasks for successful OCR images
                    llm_futures = {executor.submit(process_single_image_llm, img, configuration): img 
                                  for img in ocr_successful}
                    
                    # Track progress as LLM tasks complete
                    completed_llm = 0
                    for future in as_completed(llm_futures):
                        completed_llm += 1
                        image_path = llm_futures[future]
                        
                        # Update progress bar (Phase 2 is 50% of total work, starting at 50%)
                        progress = 0.5 + (completed_llm / len(ocr_successful)) * 0.5
                        progress_bar.progress(progress)
                        status_text.text(f"Phase 2: LLM Parsing - Processing {completed_llm} of {len(ocr_successful)}: {Path(image_path).name}")
                        
                        # Get result
                        image_path_result, success, error = future.result()
                        if success:
                            llm_successful.append(image_path_result)
                        else:
                            llm_failed.append((Path(image_path_result).name, error))
            
            # Clear progress indicators
            progress_bar.empty()
            status_text.empty()
            
            # Show completion summary
            total_successful = len(llm_successful)
            total_failed_ocr = len(ocr_failed)
            total_failed_llm = len(llm_failed)
            
            if total_failed_ocr == 0 and total_failed_llm == 0:
                st.success(f"✅ Successfully processed all {total_successful} images!")
            else:
                st.warning(f"⚠️ OCR: {len(ocr_successful)} succeeded, {total_failed_ocr} failed. "
                          f"LLM: {total_successful} succeeded, {total_failed_llm} failed.")
                
                # Show failed images if any
                failed_all = ocr_failed + llm_failed
                if failed_all:
                    with st.expander("View Failed Images", expanded=False):
                        for image_name, error in failed_all:
                            st.error(f"**{image_name}**: {error}")
        else:
            st.warning("⚠️ Please configure your API key in the Configuration tab first.")
    
    if not api_configured:
        st.caption("⚠️ API key required to parse images")