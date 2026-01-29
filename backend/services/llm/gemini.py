from typing import Any

import google.generativeai as genai
from google.generativeai.types import GenerationConfig

from .base import LLMProvider


class GeminiError(Exception):
    """Raised when Gemini request fails."""

    pass


class GeminiProvider(LLMProvider):
    """
    Google Gemini implementation of LLMProvider.

    Free tier: 15 RPM, 1M tokens/day.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-2.5-flash",
        timeout: int = 120,
    ):
        self.model_name = model
        self.timeout = timeout
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model)

    async def generate(
        self,
        prompt: str,
        json_mode: bool = False,
        temperature: float = 0.3,
    ) -> dict[str, Any]:
        """Generate completion from Gemini."""
        try:
            generation_config = GenerationConfig(
                temperature=temperature,
                response_mime_type="application/json" if json_mode else "text/plain",
            )

            response = await self.model.generate_content_async(
                prompt,
                generation_config=generation_config,
            )

            if json_mode:
                import json

                return json.loads(response.text)
            return {"text": response.text}

        except Exception as e:
            raise GeminiError(f"Gemini request failed: {e}")

    async def generate_with_tools(
        self,
        messages: list[dict],
        tools: list[dict],
    ) -> dict[str, Any]:
        """Generate completion with tool-calling capability."""
        try:
            gemini_tools = self._convert_tools(tools)
            chat = self.model.start_chat(history=self._convert_messages(messages[:-1]))

            response = await chat.send_message_async(
                messages[-1]["content"],
                tools=gemini_tools if gemini_tools else None,
            )

            result = {"content": response.text, "tool_calls": []}

            if response.candidates[0].content.parts:
                for part in response.candidates[0].content.parts:
                    if hasattr(part, "function_call"):
                        result["tool_calls"].append(
                            {
                                "function": {
                                    "name": part.function_call.name,
                                    "arguments": dict(part.function_call.args),
                                }
                            }
                        )

            return result

        except Exception as e:
            raise GeminiError(f"Gemini request failed: {e}")

    async def is_healthy(self) -> bool:
        """Check if Gemini is available."""
        try:
            response = await self.model.generate_content_async("ping")
            return response is not None
        except Exception:
            return False

    def _convert_messages(self, messages: list[dict]) -> list[dict]:
        """Convert standard messages to Gemini format."""
        history = []
        for msg in messages:
            role = "user" if msg["role"] == "user" else "model"
            history.append({"role": role, "parts": [msg["content"]]})
        return history

    def _convert_tools(self, tools: list[dict]) -> list:
        """Convert standard tools to Gemini format."""
        if not tools:
            return []

        function_declarations = []
        for tool in tools:
            if tool.get("type") == "function":
                func = tool["function"]
                function_declarations.append(
                    {
                        "name": func["name"],
                        "description": func["description"],
                        "parameters": func.get("parameters", {}),
                    }
                )

        return (
            [genai.types.Tool(function_declarations=function_declarations)]
            if function_declarations
            else []
        )
