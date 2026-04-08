from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any

import json


class LLMError(Exception):
    """Base exception for all LLM provider errors."""

    pass


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        json_mode: bool = False,
        temperature: float = 0.3,
    ) -> dict[str, Any]:
        """Generate a completion from the LLM."""
        pass

    async def generate_stream(
        self,
        prompt: str,
        json_mode: bool = False,
        temperature: float = 0.3,
    ) -> AsyncIterator[str]:
        """Stream tokens from the LLM. Default falls back to generate()."""
        result = await self.generate(
            prompt, json_mode=json_mode, temperature=temperature
        )
        if json_mode:
            yield json.dumps(result)
        else:
            yield result.get("text", "")

    @abstractmethod
    async def generate_with_tools(
        self,
        messages: list[dict],
        tools: list[dict],
    ) -> dict[str, Any]:
        """Generate a completion with tool-calling capability."""
        pass

    @abstractmethod
    async def is_healthy(self) -> bool:
        """Check if the LLM provider is available."""
        pass
