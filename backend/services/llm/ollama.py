import json
from typing import Any

import httpx

from .base import LLMProvider


class OllamaError(Exception):
    """Raised when Ollama request fails."""

    pass


class OllamaProvider(LLMProvider):
    """
    Ollama implementation of LLMProvider.

    Ollama runs locally - no API costs, full privacy.
    Supports tool calling since Ollama 0.3+.

    Usage:
        provider = OllamaProvider("http://localhost:11434", "qwen2.5-coder:7b")
        result = await provider.generate("Explain this code", json_mode=True)
    """

    def __init__(
        self,
        base_url: str,
        model: str,
        timeout: int = 120,
    ):
        self.base_url = base_url
        self.model = model
        self.timeout = timeout

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

    async def generate_with_tools(
        self,
        messages: list[dict],
        tools: list[dict],
    ) -> dict[str, Any]:
        """
        Generate completion with tool-calling capability.

        Uses Ollama's /api/chat endpoint which supports tools.

        Args:
            messages: Conversation history as list of message dicts.
                    Format: [{"role": "user", "content": "..."}]
            tools: Available tools in Ollama format.

        Returns:
            dict with 'message' containing 'content' and optional 'tool_calls'.

        Raises:
            OllamaError: If request fails.
        """
        payload = {
            "model": self.model,
            "messages": messages,
            "tools": tools,
            "stream": False,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json=payload,
                )
                response.raise_for_status()
                return response.json()

        except httpx.TimeoutException:
            raise OllamaError(f"Request timed out after {self.timeout}s")
        except httpx.HTTPStatusError as e:
            raise OllamaError(f"HTTP {e.response.status_code}: {e.response.text}")
        except Exception as e:
            raise OllamaError(f"Ollama request failed: {e}")

    async def is_healthy(self) -> bool:
        """
        Check if Ollama service is running and responsive.

        Returns:
            True if Ollama is healthy, False otherwise.
        """
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                return response.status_code == 200
        except Exception:
            return False
