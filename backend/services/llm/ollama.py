import asyncio
import json
from typing import Any

import httpx

from .base import LLMProvider, LLMError

_MAX_RETRIES = 3
_RETRYABLE_STATUS = {429, 503}


class OllamaError(LLMError):
    pass


class OllamaProvider(LLMProvider):

    def __init__(
        self,
        base_url: str,
        model: str,
        timeout: int = 120,
    ):
        self.base_url = base_url
        self.model = model
        self.timeout = timeout
        self._client = httpx.AsyncClient(base_url=base_url, timeout=timeout)

    async def generate(
        self,
        prompt: str,
        json_mode: bool = False,
        temperature: float = 0.3,
    ) -> dict[str, Any]:
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

        last_exc: Exception | None = None
        for attempt in range(_MAX_RETRIES):
            try:
                response = await self._client.post("/api/generate", json=payload)
                response.raise_for_status()
                result = response.json()

                if json_mode:
                    return json.loads(result["response"])
                return {"text": result["response"]}

            except httpx.TimeoutException:
                raise OllamaError(f"Request timed out after {self.timeout}s")
            except httpx.HTTPStatusError as e:
                if e.response.status_code in _RETRYABLE_STATUS and attempt < _MAX_RETRIES - 1:
                    await asyncio.sleep(2 ** (attempt + 1))
                    last_exc = e
                    continue
                raise OllamaError(f"HTTP {e.response.status_code}: {e.response.text}")
            except json.JSONDecodeError as e:
                raise OllamaError(f"Invalid JSON response: {e}")
            except OllamaError:
                raise
            except Exception as e:
                raise OllamaError(f"Ollama request failed: {e}")

        raise OllamaError(f"Ollama request failed after {_MAX_RETRIES} retries: {last_exc}")

    async def generate_with_tools(
        self,
        messages: list[dict],
        tools: list[dict],
    ) -> dict[str, Any]:
        payload = {
            "model": self.model,
            "messages": messages,
            "tools": tools,
            "stream": False,
        }

        last_exc: Exception | None = None
        for attempt in range(_MAX_RETRIES):
            try:
                response = await self._client.post("/api/chat", json=payload)
                response.raise_for_status()
                return response.json()

            except httpx.TimeoutException:
                raise OllamaError(f"Request timed out after {self.timeout}s")
            except httpx.HTTPStatusError as e:
                if e.response.status_code in _RETRYABLE_STATUS and attempt < _MAX_RETRIES - 1:
                    await asyncio.sleep(2 ** (attempt + 1))
                    last_exc = e
                    continue
                raise OllamaError(f"HTTP {e.response.status_code}: {e.response.text}")
            except OllamaError:
                raise
            except Exception as e:
                raise OllamaError(f"Ollama request failed: {e}")

        raise OllamaError(f"Ollama request failed after {_MAX_RETRIES} retries: {last_exc}")

    async def is_healthy(self) -> bool:
        try:
            response = await self._client.get("/api/tags")
            return response.status_code == 200
        except Exception:
            return False
