import json
from typing import Any

import httpx

from backend.core.config import settings


class OllamaError(Exception):
    """Raised when Ollama request fails."""

    pass


class OllamaClient:
    """
    Async client for Ollama API.

    Usage:
        client = OllamaClient()
        result = await client.generate("Explain this code", json_mode=True)
    """

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout: int | None = None,
    ):
        self.base_url = base_url or settings.ollama_url
        self.model = model or settings.ollama_model
        self.timeout = timeout or settings.ollama_timeout

    async def generate(
        self,
        prompt: str,
        json_mode: bool = False,
        temperature: float = 0.3,
    ) -> dict[str, Any]:
        """
        Generate completion from Ollama.

        Args:
            prompt: The prompt to send to the model.
            json_mode: If True, request JSON output format.
            temperature: Sampling temperature (0.0-1.0). Lower = more deterministic.

        Returns:
            Parsed JSON dict if json_mode=True, else {"text": response}.

        Raises:
            OllamaError: If request fails or response is invalid.
        """
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
            },
        }

        if json_mode:
            payload["format"] = "json"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                )
                response.raise_for_status()
                result = response.json()

                if json_mode:
                    return json.loads(result["response"])
                return {"text": result["response"]}

        except httpx.TimeoutException:
            raise OllamaError(f"Request timed out after {self.timeout}s")
        except httpx.HTTPStatusError as e:
            raise OllamaError(f"HTTP {e.response.status_code}: {e.response.text}")
        except json.JSONDecodeError as e:
            raise OllamaError(f"Invalid JSON response: {e}")
        except Exception as e:
            raise OllamaError(f"Ollama request failed: {e}")

    async def is_healthy(self) -> bool:
        """Check if Ollama service is running and responsive."""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                return response.status_code == 200
        except Exception:
            return False
