import os
import json
from pydantic_settings import BaseSettings
from pydantic import ConfigDict, Field


IMAGE_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.tif', '.tiff')  # Define your extensions

class Configuration(BaseSettings):
    model_config = ConfigDict(
        extra='allow'
    )
    
    # Required field set during initialization
    image_files: list[str] = Field(default_factory=list)
    
    # API configuration with defaults
    llm_base_url: str = "https://api.deepinfra.com/v1/openai/chat/completions"
    deepinfra_api_key: str = ""
    olm_model: str = "allenai/olmOCR-7B-0825"
    olm_temperature: float = 0.7
    olm_max_tokens: int = 4096
    olm_prompt: str = "Please extract all text from this herbarium specimen image."
    llm_parse_model: str = "openai/gpt-oss-120b"
    llm_parse_temperature: float = 0.7
    llm_parse_max_tokens: int = 4096
    llm_parse_prompt: str = (
        "The following is a transcription of a herbarium specimen image. "
        "Please parse the transcription and extract the following information: "
        "collector name, location, family, and collection date. "
        "Return the information in a JSON format. "
        "The JSON format should be: "
        "{'collector_name': 'string', 'location': 'string', 'family': 'string', 'collection_date': 'string'}"
    )
    
    def __init__(self, workspace_folder: str, **kwargs):
        configuration_path = os.path.join(workspace_folder, ".herbairium_configuration.json")
        
        # Scan for image files (case-insensitive)
        image_files = [
            os.path.join(workspace_folder, f) for f in os.listdir(workspace_folder) 
            if os.path.isfile(os.path.join(workspace_folder, f)) and f.lower().endswith(IMAGE_EXTENSIONS)
        ]
        
        # Load from JSON if it exists
        if os.path.exists(configuration_path):
            with open(configuration_path, 'r') as f:
                json_data = json.load(f)
                kwargs.update(json_data)
        
        # Always use the freshly scanned image_files list (don't override with saved JSON)
        kwargs['image_files'] = image_files
        
        # Initialize with all values
        super().__init__(
            **kwargs
        )
        self.configuration_path = configuration_path

    def save(self) -> bool:
        try:
            with open(self.configuration_path, 'w') as f:
                json.dump(self.model_dump(), f)
            return True
        except Exception as e:
            return False