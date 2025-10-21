import requests
import base64
import json

class DeepinfraClient:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        prompt: str,
    ):
        self.base_url = base_url
        self.api_key = api_key
        self.model = model
        self.prompt = prompt

    def inference(
        self,
        temperature: float,
        pdf_path: str = None,
        text: str = None,
    ):
        pdf_data = None
        if pdf_path:
            try:
                with open(pdf_path, "rb") as pdf_file:
                    pdf_data = pdf_file.read()
                    pdf_data = base64.b64encode(pdf_data).decode("utf-8")
            except Exception as e:
                print(f"Error reading PDF file: {e}")
                return None

        content = [
            {
                "type": "text",
                "text": self.prompt
            }
        ]

        if text:
            content.append({
                "type": "text",
                "text": text
            })

        if pdf_data:
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{pdf_data}"
                }
            })
        

        response = requests.post(
            self.base_url,
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": content,
                    },
                ],
                "max_tokens": 4096,
                "temperature": temperature,
            },
        )
        response_json = response.json()
        return response_json["choices"][0]["message"]["content"]
