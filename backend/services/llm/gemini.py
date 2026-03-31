import asyncio
import json
import re
from typing import Any

from google import genai
from google.genai import types

from .base import LLMProvider, LLMError

_RETRY_DELAY_RE = re.compile(r"retryDelay['\"]:\s*['\"](\d+)")
_MAX_RETRIES = 3


class GeminiError(LLMError):
    pass


def _is_rate_limit_error(exc: Exception) -> bool:
    code = getattr(exc, "code", None) or getattr(exc, "status_code", None)
    if code in (429, 8):  # HTTP 429 or gRPC RESOURCE_EXHAUSTED
        return True
    return "RESOURCE_EXHAUSTED" in str(exc)


def _extract_retry_delay(exc: Exception) -> float:
    match = _RETRY_DELAY_RE.search(str(exc))
    return float(match.group(1)) + 1 if match else 10.0


class GeminiProvider(LLMProvider):

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-2.5-flash",
        timeout: int = 120,
    ):
        self.model_name = model
        self.timeout = timeout
        self.client = genai.Client(
            api_key=api_key,
            http_options={"timeout": timeout * 1000},
        )

    async def generate(
        self,
        prompt: str,
        json_mode: bool = False,
        temperature: float = 0.3,
    ) -> dict[str, Any]:
        config = types.GenerateContentConfig(
            temperature=temperature,
            response_mime_type="application/json" if json_mode else "text/plain",
        )

        last_exc: Exception | None = None
        for attempt in range(_MAX_RETRIES):
            try:
                response = await self.client.aio.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=config,
                )

                text = response.text if response and response.text else None
                if text is None:
                    raise GeminiError("Gemini returned an empty response (possibly blocked by safety filters)")

                if json_mode:
                    return json.loads(text)
                return {"text": text}
            except GeminiError:
                raise
            except Exception as e:
                if _is_rate_limit_error(e) and attempt < _MAX_RETRIES - 1:
                    delay = _extract_retry_delay(e)
                    await asyncio.sleep(delay)
                    last_exc = e
                    continue
                raise GeminiError(f"Gemini request failed: {e}")

        raise GeminiError(f"Gemini request failed after {_MAX_RETRIES} retries: {last_exc}")

    async def generate_with_tools(
        self,
        messages: list[dict],
        tools: list[dict],
    ) -> dict[str, Any]:
        gemini_tools = self._convert_tools(tools)
        contents = self._convert_messages(messages)
        config = types.GenerateContentConfig(
            tools=gemini_tools if gemini_tools else None,
        )

        last_exc: Exception | None = None
        for attempt in range(_MAX_RETRIES):
            try:
                response = await self.client.aio.models.generate_content(
                    model=self.model_name,
                    contents=contents,
                    config=config,
                )

                text = ""
                try:
                    text = response.text or ""
                except Exception:
                    text = ""

                result = {"content": text, "tool_calls": []}
                if response.candidates and response.candidates[0].content.parts:
                    for part in response.candidates[0].content.parts:
                        if part.function_call:
                            result["tool_calls"].append(
                                {
                                    "function": {
                                        "name": part.function_call.name,
                                        "arguments": dict(part.function_call.args),
                                    }
                                }
                            )
                return result
            except GeminiError:
                raise
            except Exception as e:
                if _is_rate_limit_error(e) and attempt < _MAX_RETRIES - 1:
                    delay = _extract_retry_delay(e)
                    await asyncio.sleep(delay)
                    last_exc = e
                    continue
                raise GeminiError(f"Gemini request failed: {e}")

        raise GeminiError(f"Gemini request failed after {_MAX_RETRIES} retries: {last_exc}")

    async def is_healthy(self) -> bool:
        try:
            response = await self.client.aio.models.generate_content(
                model=self.model_name,
                contents="ping",
            )
            return response is not None
        except Exception:
            return False

    def _convert_messages(self, messages: list[dict]) -> list[types.Content]:
        contents = []
        for msg in messages:
            role = "user" if msg["role"] == "user" else "model"
            contents.append(
                types.Content(
                    role=role,
                    parts=[types.Part.from_text(text=msg["content"])],
                )
            )
        return contents

    def _convert_tools(self, tools: list[dict]) -> list[types.Tool]:
        if not tools:
            return []

        function_declarations = []
        for tool in tools:
            if tool.get("type") == "function":
                func = tool["function"]
                function_declarations.append(
                    types.FunctionDeclaration(
                        name=func["name"],
                        description=func["description"],
                        parameters=func.get("parameters", {}),
                    )
                )

        return (
            [types.Tool(function_declarations=function_declarations)]
            if function_declarations
            else []
        )
