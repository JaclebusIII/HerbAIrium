"""
Configuration tab component.
Handles OLM OCR configuration interface.
"""
import streamlit as st
from state import save_configuration


def render_api_settings():
    """Render API configuration section."""
    st.subheader("LLM Server Settings")
    
    llm_base_url = st.text_input(
        "Base URL",
        value=st.session_state.configuration.llm_base_url,
        help="The base URL for the API endpoint"
    )
    
    deepinfra_api_key = st.text_input(
        "API Key",
        value=st.session_state.configuration.deepinfra_api_key,
        type="password",
        help="Your API key for authentication"
    )
    

    return llm_base_url, deepinfra_api_key


def render_model_parameters():
    """Render model parameters section."""
    st.subheader("🎛️ VLM OCR Model Parameters")

    olm_model = st.text_input(
        "Model Name",
        value=st.session_state.configuration.olm_model,
        help="The model identifier to use"
    )

    olm_temperature = st.slider(
        "Temperature",
        min_value=0.0,
        max_value=2.0,
        value=st.session_state.configuration.olm_temperature,
        step=0.1,
        help="Controls randomness in output. Lower = more focused, Higher = more creative"
    )
    
    olm_max_tokens = st.number_input(
        "Max Tokens",
        min_value=1,
        max_value=32000,
        value=st.session_state.configuration.olm_max_tokens,
        step=256,
        help="Maximum number of tokens to generate"
    )

    olm_prompt = st.text_area(
        "Prompt Template",
        value=st.session_state.configuration.olm_prompt,
        height=150,
        help="The prompt that will be sent to the model along with the image"
    )
        
    return olm_model, olm_temperature, olm_max_tokens, olm_prompt


def render_llm_parse_parameters():
    """Render LLM parse parameters section."""
    st.subheader("LLM Parse Model Parameters")

    llm_parse_model = st.text_input(
        "Model Name",
        value=st.session_state.configuration.llm_parse_model,
        help="The model identifier to use"
    )

    llm_parse_temperature = st.slider(
        "Parsing Temperature",
        min_value=0.0,
        max_value=2.0,
        value=st.session_state.configuration.llm_parse_temperature,
        step=0.1,
        help="Controls randomness in output. Lower = more focused, Higher = more creative"
    )

    llm_parse_max_tokens = st.number_input(
        "Parsing Max Tokens",
        min_value=1,
        max_value=32000,
        value=st.session_state.configuration.llm_parse_max_tokens,
        step=256,
        help="Maximum number of tokens to generate"
    )

    llm_parse_prompt = st.text_area(
        "Prompt Template",
        value=st.session_state.configuration.llm_parse_prompt,
        height=150,
        help="The prompt that will be sent to the model along with the transcription"
    )

    st.divider()

    return llm_parse_model, llm_parse_temperature, llm_parse_max_tokens, llm_parse_prompt

def render_configuration_actions(config_values):
    """
    Render save/reset/test buttons.
    
    Args:
        config_values: Tuple of configuration values to save
    """
    llm_base_url, deepinfra_api_key, olm_model, olm_temperature, olm_max_tokens, olm_prompt, llm_parse_model, llm_parse_temperature, llm_parse_max_tokens, llm_parse_prompt = config_values
    
    col_save1, col_save2, col_save3 = st.columns(3)
    
    with col_save1:
        if st.button("💾 Save Configuration", width='stretch', type="primary"):
            # Update session state with current values
            st.session_state.configuration.llm_base_url = llm_base_url
            st.session_state.configuration.deepinfra_api_key = deepinfra_api_key
            st.session_state.configuration.olm_model = olm_model
            st.session_state.configuration.olm_temperature = olm_temperature
            st.session_state.configuration.olm_max_tokens = olm_max_tokens
            st.session_state.configuration.olm_prompt = olm_prompt
            st.session_state.configuration.llm_parse_model = llm_parse_model
            st.session_state.configuration.llm_parse_temperature = llm_parse_temperature
            st.session_state.configuration.llm_parse_max_tokens = llm_parse_max_tokens
            st.session_state.configuration.llm_parse_prompt = llm_parse_prompt

            if st.session_state.configuration.save():
                st.success("Configuration saved successfully")
            else:
                st.error("Failed to save configuration")
    
    with col_save3:
        # Test connection button
        if st.button("🧪 Test Connection", width='stretch'):
            if deepinfra_api_key:
                st.info("Connection test functionality will be implemented here")
            else:
                st.warning("⚠️ Please enter an API key first")


def render_configuration_summary():
    """Render configuration summary section."""
    with st.expander("📋 Current Configuration Summary"):
        st.json({
            "base_url": st.session_state.configuration.llm_base_url,
            "model": st.session_state.configuration.olm_model,
            "temperature": st.session_state.configuration.olm_temperature,
            "max_tokens": st.session_state.configuration.olm_max_tokens,
            "prompt_length": len(st.session_state.configuration.olm_prompt),
            "api_key_set": bool(st.session_state.configuration.deepinfra_api_key),
            "parse_model": st.session_state.configuration.llm_parse_model,
            "parse_temperature": st.session_state.configuration.llm_parse_temperature,
            "parse_max_tokens": st.session_state.configuration.llm_parse_max_tokens,
            "parse_prompt_length": len(st.session_state.configuration.llm_parse_prompt)
        })


def render_configuration_tab():
    """Render the complete configuration tab."""
    st.header("⚙️ OLM OCR Configuration")
    st.write("Configure the parameters for the OLMoCR model.")

    st.divider()
    
    # API Configuration
    llm_base_url, deepinfra_api_key = render_api_settings()
    st.divider()
    
    # Model Parameters
    olm_model, olm_temperature, olm_max_tokens, olm_prompt = render_model_parameters()
    st.divider()
    
    # LLM Parse Parameters
    llm_parse_model, llm_parse_temperature, llm_parse_max_tokens, llm_parse_prompt = render_llm_parse_parameters()
    st.divider()
    
    # Save/Reset buttons
    config_values = (llm_base_url, deepinfra_api_key, olm_model, olm_temperature, olm_max_tokens, olm_prompt, llm_parse_model, llm_parse_temperature, llm_parse_max_tokens, llm_parse_prompt)
    render_configuration_actions(config_values)
    st.divider()
    
    # Configuration summary
    render_configuration_summary()

