import base64
import asyncio
import threading

import httpx
import requests


_thread_local = threading.local()


def _session() -> requests.Session:
    session = getattr(_thread_local, "session", None)
    if session is None:
        session = requests.Session()
        _thread_local.session = session
    return session


class DeepinfraClient:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        prompt: str,
        max_tokens: int,
    ):
        self.base_url = base_url
        self.api_key = api_key
        self.model = model
        self.prompt = prompt
        self.max_tokens = max_tokens

    def inference(
        self,
        temperature: float,
        pdf_path: str | None = None,
        text: str | None = None,
    ):
        response = _session().post(
            self.base_url,
            headers=self._headers(),
            json=self.request_body(
                temperature=temperature,
                pdf_path=pdf_path,
                text=text,
            ),
            timeout=(15, 300),
        )
        return self.completion_content(response)

    async def async_inference(
        self,
        client: httpx.AsyncClient,
        temperature: float,
        pdf_path: str | None = None,
        text: str | None = None,
    ) -> str:
        body = await asyncio.to_thread(
            self.request_body,
            temperature,
            pdf_path,
            text,
        )
        response = await client.post(
            self.base_url,
            headers=self._headers(),
            json=body,
        )
        try:
            response.raise_for_status()
            return self.completion_json_content(response.json())
        except httpx.HTTPStatusError as exc:
            detail = response.text[:500]
            raise RuntimeError(
                f"DeepInfra request failed with status {response.status_code}: {detail}"
            ) from exc
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise RuntimeError("DeepInfra returned an invalid completion response.") from exc

    def request_body(
        self,
        temperature: float,
        pdf_path: str | None = None,
        text: str | None = None,
    ) -> dict:
        pdf_data = None
        if pdf_path:
            try:
                with open(pdf_path, "rb") as pdf_file:
                    pdf_data = base64.b64encode(pdf_file.read()).decode("utf-8")
            except OSError as exc:
                raise RuntimeError(f"Failed to read image: {exc}") from exc

        content = [{"type": "text", "text": self.prompt}]
        if text:
            content.append({"type": "text", "text": text})
        if pdf_data:
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{pdf_data}"},
            })

        return {
            "model": self.model,
            "messages": [{"role": "user", "content": content}],
            "max_tokens": self.max_tokens,
            "temperature": temperature,
        }

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}"}

    @staticmethod
    def completion_content(response: requests.Response) -> str:
        try:
            response.raise_for_status()
            return DeepinfraClient.completion_json_content(response.json())
        except requests.HTTPError as exc:
            detail = response.text[:500]
            raise RuntimeError(
                f"DeepInfra request failed with status {response.status_code}: {detail}"
            ) from exc
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise RuntimeError("DeepInfra returned an invalid completion response.") from exc

    @staticmethod
    def completion_json_content(response_json: dict) -> str:
        result = response_json["choices"][0]["message"]["content"]
        if not isinstance(result, str) or not result.strip():
            raise ValueError("Completion content is empty.")
        return result


class DeepinfraBatchClient:
    TERMINAL_STATUSES = {"completed", "failed", "expired", "cancelled"}

    def __init__(self, completion_url: str, api_key: str):
        suffix = "/chat/completions"
        normalized_url = completion_url.rstrip("/")
        if not normalized_url.endswith(suffix):
            raise ValueError(
                "Batch processing requires an OpenAI-compatible /chat/completions URL."
            )
        self.base_url = normalized_url[:-len(suffix)]
        self.api_key = api_key

    def upload_file(self, path: str) -> str:
        with open(path, "rb") as batch_file:
            response = _session().post(
                f"{self.base_url}/files",
                headers=self._headers(),
                data={"purpose": "batch"},
                files={"file": ("batch_input.jsonl", batch_file, "application/jsonl")},
                timeout=(15, 300),
            )
        return self._json(response)["id"]

    def create_batch(self, input_file_id: str) -> dict:
        response = _session().post(
            f"{self.base_url}/batches",
            headers=self._headers(),
            json={
                "input_file_id": input_file_id,
                "endpoint": "/v1/chat/completions",
                "completion_window": "24h",
            },
            timeout=(15, 60),
        )
        return self._json(response)

    def retrieve_batch(self, batch_id: str) -> dict:
        response = _session().get(
            f"{self.base_url}/batches/{batch_id}",
            headers=self._headers(),
            timeout=(15, 60),
        )
        return self._json(response)

    def download_file(self, file_id: str) -> str:
        response = _session().get(
            f"{self.base_url}/files/{file_id}/content",
            headers=self._headers(),
            timeout=(15, 300),
        )
        response.raise_for_status()
        return response.text

    def cancel_batch(self, batch_id: str) -> None:
        response = _session().post(
            f"{self.base_url}/batches/{batch_id}/cancel",
            headers=self._headers(),
            timeout=(15, 60),
        )
        response.raise_for_status()

    def delete_file(self, file_id: str) -> None:
        response = _session().delete(
            f"{self.base_url}/files/{file_id}",
            headers=self._headers(),
            timeout=(15, 60),
        )
        response.raise_for_status()

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}"}

    @staticmethod
    def _json(response: requests.Response) -> dict:
        try:
            response.raise_for_status()
            result = response.json()
            if not isinstance(result, dict):
                raise ValueError("Response is not an object.")
            return result
        except requests.HTTPError as exc:
            detail = response.text[:500]
            raise RuntimeError(
                f"DeepInfra batch request failed with status "
                f"{response.status_code}: {detail}"
            ) from exc
        except ValueError as exc:
            raise RuntimeError("DeepInfra returned an invalid batch response.") from exc
