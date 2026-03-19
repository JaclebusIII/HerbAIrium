from models.configuration import Configuration
from utils import llm_parse_transcription_and_save_results, process_ocr_and_save_results


def run_ocr_on_image(image_path: str, configuration: Configuration):
    try:
        process_ocr_and_save_results(image_path, configuration)
        return (image_path, True, None)
    except Exception as e:
        return (image_path, False, str(e))


def run_llm_on_image(image_path: str, configuration: Configuration):
    try:
        llm_parse_transcription_and_save_results(image_path, configuration)
        return (image_path, True, None)
    except Exception as e:
        return (image_path, False, str(e))
