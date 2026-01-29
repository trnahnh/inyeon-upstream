from abc import ABC, abstractmethod
from typing import Any


class LLMProvider(ABC):
    """
    Abstract base class for LLM providers.

    All LLM providers (Ollama, Gemini, OpenAI) must implement this interface.
    This allows the application to swap providers without changing agent code.
    """

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        json_mode: bool = False,
        temperature: float = 0.3,
    ) -> dict[str, Any]:
        """
        Generate a completion from the LLM.

        Args:
            prompt: The input prompt to send to the model.
            json_mode: If True, request structured JSON output.
            temperature: Sampling temperature (0.0-1.0). Lower = more deterministic.

        Returns:
            dict containing the response. Format depends on json_mode:
            - json_mode=True: parsed JSON object
            - json_mode=False: {"text": "response string"}
        """
        pass

    @abstractmethod
    async def generate_with_tools(
        self,
        messages: list[dict],
        tools: list[dict],
    ) -> dict[str, Any]:
        """
        Generate a completion with tool-calling capability.

        This enables agentic workflows where the LLM can request tool execution.

        Args:
            messages: Conversation history as list of message dicts.
            tools: Available tools in provider-specific format.

        Returns:
            dict containing response with optional tool_calls.
        """
        pass

    @abstractmethod
    async def is_healthy(self) -> bool:
        """
        Check if the LLM provider is available and responsive.

        Returns:
            True if the provider is healthy, False otherwise.
        """
        pass
