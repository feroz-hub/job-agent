"""Official Google Gen AI SDK adapter."""
import os
import httpx
from google import genai
from google.genai import errors, types
from .models import RESPONSE_SCHEMA
from .provider import ProviderError, TransientProviderError


class GeminiProvider:
    def __init__(self, api_key: str | None = None, model: str | None = None):
        key = api_key if api_key is not None else os.getenv("GEMINI_API_KEY", "")
        self.model = (model if model is not None else os.getenv("GEMINI_MODEL", "")).strip()
        if not key.strip():
            raise ValueError("Set GEMINI_API_KEY in .env")
        if not self.model:
            raise ValueError("Set GEMINI_MODEL in .env to a supported model ID")
        self.client = genai.Client(api_key=key, http_options=types.HttpOptions(
            timeout=60000, retry_options=types.HttpRetryOptions(attempts=1)))

    def generate(self, prompt: str) -> str:
        try:
            response = self.client.models.generate_content(
                model=self.model, contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json",
                                                   response_json_schema=RESPONSE_SCHEMA),
            )
            return response.text or ""
        except errors.APIError as exc:
            # Never include raw provider exceptions, prompts, or keys in logs/UI.
            message = f"Gemini request failed (HTTP {exc.code})"
            if exc.code in (408, 429, 500, 502, 503, 504):
                raise TransientProviderError(message) from None
            raise ProviderError(message) from None
        except (httpx.TransportError, TimeoutError) as exc:
            raise TransientProviderError("Gemini network request failed") from None

    def close(self) -> None:
        self.client.close()
