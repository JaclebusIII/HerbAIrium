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
        "Please parse the transcription and extract the following information into a JSON format:\n\n"
        "catalogNumber: This is the barcode number. Should be an int\n"
        "recordNumber: This is the random number on the label, often closely located to the collector's name. Should be an int\n"
        "family: Always ends with '-aceae'. Should be a string\n"
        "scientificName: Should include both genus and species names. The first letter of the genus name should always be capitalized. The species name should always be all lowercase. Should be a string\n"
        "scientificNameAuthorship: This is the name or abbreviation listed after the species name. Should be a string\n"
        "eventDate: Convert to the format YYYY-MM-DD. Return as a string\n"
        "country: If in the USA, always write it down as 'United States' not US, USA, America, United States of America, or anything else. Should be a string\n"
        "stateProvince: Use fuzzy matching to make sure state or province name is spelled correctly. Should be a string\n"
        "County: Use fuzzy matching to make sure county name is spelled correctly. Should be a string\n"
        "Locality: Everything related to the location of the specimen. Should be a string\n"
        "decimalLatitude: Only include if it is on the label. Leave blank if not on label. Convert to decimal degree. Should be a float\n"
        "decimalLongitude: Only include if it is on the label. Leave blank if not on label. Convert to decimal degree. Should be a float\n"
        "recordedBy: First person's name listed. Should be a string\n"
        "associatedCollectors: If there is more than one collector, list all subsequent collectors here. Should be a list of strings\n"
        "minimumElevationInMeters: Only include if it is on the label. If listed as feet, convert to Meters. Should be an int\n\n"
        "Return the information in a JSON format with the above field names. "
        "Leave fields blank (empty string or null) if the information is not found in the transcription."
        "Do not surround json data in 'json``` <blah> ``` ' just start response with '{'"
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