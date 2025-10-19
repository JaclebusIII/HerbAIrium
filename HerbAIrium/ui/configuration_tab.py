"""
Configuration tab component.
Handles OLM OCR configuration interface.
"""
import streamlit as st
from state import reset_olm_config, save_configuration, has_saved_configuration


def render_api_settings():
    """Render API configuration section."""
    st.subheader("🔌 API Settings")
    
    olm_base_url = st.text_input(
        "Base URL",
        value=st.session_state.olm_base_url,
        help="The base URL for the API endpoint"
    )
    
    olm_api_key = st.text_input(
        "API Key",
        value=st.session_state.olm_api_key,
        type="password",
        help="Your API key for authentication"
    )
    
    olm_model = st.text_input(
        "Model Name",
        value=st.session_state.olm_model,
        help="The model identifier to use"
    )
    
    return olm_base_url, olm_api_key, olm_model


def render_model_parameters():
    """Render model parameters section."""
    st.subheader("🎛️ Model Parameters")
    
    olm_temperature = st.slider(
        "Temperature",
        min_value=0.0,
        max_value=2.0,
        value=st.session_state.olm_temperature,
        step=0.1,
        help="Controls randomness in output. Lower = more focused, Higher = more creative"
    )
    
    olm_max_tokens = st.number_input(
        "Max Tokens",
        min_value=1,
        max_value=32000,
        value=st.session_state.olm_max_tokens,
        step=256,
        help="Maximum number of tokens to generate"
    )
    
    return olm_temperature, olm_max_tokens


def render_prompt_configuration():
    """Render prompt configuration section."""
    st.subheader("💬 OCR Prompt")
    
    olm_prompt = st.text_area(
        "Prompt Template",
        value=st.session_state.olm_prompt,
        height=150,
        help="The prompt that will be sent to the model along with the image"
    )
    
    return olm_prompt


def render_configuration_actions(config_values):
    """
    Render save/reset/test buttons.
    
    Args:
        config_values: Tuple of configuration values to save
    """
    olm_base_url, olm_api_key, olm_model, olm_temperature, olm_max_tokens, olm_prompt = config_values
    
    col_save1, col_save2, col_save3 = st.columns(3)
    
    with col_save1:
        if st.button("💾 Save Configuration", use_container_width=True, type="primary"):
            # Update session state with current values
            st.session_state.olm_base_url = olm_base_url
            st.session_state.olm_api_key = olm_api_key
            st.session_state.olm_model = olm_model
            st.session_state.olm_temperature = olm_temperature
            st.session_state.olm_max_tokens = olm_max_tokens
            st.session_state.olm_prompt = olm_prompt
            
            # Save to file
            if save_configuration():
                st.success("✅ Configuration saved to workspace!")
            else:
                st.warning("⚠️ Configuration updated in session but not saved to file")
    
    with col_save2:
        if st.button("🔄 Reset to Defaults", use_container_width=True):
            reset_olm_config()
            st.rerun()
    
    with col_save3:
        # Test connection button
        if st.button("🧪 Test Connection", use_container_width=True):
            if olm_api_key:
                st.info("Connection test functionality will be implemented here")
            else:
                st.warning("⚠️ Please enter an API key first")


def render_configuration_summary():
    """Render configuration summary section."""
    with st.expander("📋 Current Configuration Summary"):
        st.json({
            "base_url": st.session_state.olm_base_url,
            "model": st.session_state.olm_model,
            "temperature": st.session_state.olm_temperature,
            "max_tokens": st.session_state.olm_max_tokens,
            "api_key_set": bool(st.session_state.olm_api_key),
            "prompt_length": len(st.session_state.olm_prompt)
        })


def render_configuration_tab():
    """Render the complete configuration tab."""
    st.header("⚙️ OLM OCR Configuration")
    st.write("Configure the parameters for the OLMoCR model.")
    
    # Show configuration status
    if has_saved_configuration():
        st.info("💾 This workspace has a saved configuration that was loaded automatically.")
    else:
        st.info("📝 No saved configuration found for this workspace. Settings will use defaults.")
    
    st.divider()
    
    # API Configuration
    olm_base_url, olm_api_key, olm_model = render_api_settings()
    st.divider()
    
    # Model Parameters
    olm_temperature, olm_max_tokens = render_model_parameters()
    st.divider()
    
    # Prompt Configuration
    olm_prompt = render_prompt_configuration()
    st.divider()
    
    # Save/Reset buttons
    config_values = (olm_base_url, olm_api_key, olm_model, olm_temperature, olm_max_tokens, olm_prompt)
    render_configuration_actions(config_values)
    st.divider()
    
    # Configuration summary
    render_configuration_summary()

