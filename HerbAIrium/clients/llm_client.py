import requests
import json

class LLMClient:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        system_prompt: str = None,
    ):
        self.base_url = base_url
        self.api_key = api_key
        self.model = model
        self.system_prompt = system_prompt

    def inference(self, user_message: str, temperature: float = 0.7, max_tokens: int = 4096):
        messages = []
        
        # Add system prompt if provided
        if self.system_prompt:
            messages.append({
                "role": "system",
                "content": self.system_prompt
            })
        
        # Add user message
        messages.append({
            "role": "user",
            "content": user_message
        })

        response = requests.post(
            self.base_url,
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": self.model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
            },
        )
        response_json = response.json()
        return response_json["choices"][0]["message"]["content"]