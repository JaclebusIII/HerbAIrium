import requests
import base64
import json

class OLMocrClient:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        prompt: str,
    ):
        self.base_url = base_url
        self.api_key = api_key
        self.prompt = prompt

    def inference(self, pdf_path: str, temperature: float):
        with open(pdf_path, "rb") as pdf_file:
            pdf_data = pdf_file.read()

        pdf_data = base64.b64encode(pdf_data).decode("utf-8")

        response = requests.post(
            self.base_url,
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": "allenai/olmOCR-7B-0825",
                "messages": [
                    {
                        "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{pdf_data}"
                            }
                        },
                        {
                            "type": "text",
                            "text": self.prompt
                        }
                    ]
                    },
                ],
                "max_tokens": 4096,
                "temperature": temperature,
            },
        )
        response_json = response.json()
        return response_json["choices"][0]["message"]["content"]
