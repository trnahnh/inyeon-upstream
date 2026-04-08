import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any

from openai import AsyncOpenAI, APIStatusError, APITimeoutError

from .base import LLMProvider, LLMError

_MAX_RETRIES = 3


class OpenAIError(LLMError):
    pass


def _extract_retry_delay(exc: APIStatusError, attempt: int) -> float:
    retry_after = exc.response.headers.get("retry-after")
    if retry_after:
        try:
            return float(retry_after) + 1
        except ValueError:
            pass
    return 2 ** (attempt + 1)


class OpenAIProvider(LLMProvider):

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4.1-mini",
        timeout: int = 120,
    ):
        self.model = model
        self.timeout = timeout
        self.client = AsyncOpenAI(api_key=api_key, timeout=timeout, max_retries=0)

    async def generate(
        self,
        prompt: str,
        json_mode: bool = False,
        temperature: float = 0.3,
    ) -> dict[str, Any]:
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        last_exc: Exception | None = None
        for attempt in range(_MAX_RETRIES):
            try:
                response = await self.client.chat.completions.create(**kwargs)
                text = response.choices[0].message.content
                if text is None:
                    raise OpenAIError("OpenAI returned an empty response")
                if json_mode:
                    return json.loads(text)
                return {"text": text}
            except OpenAIError:
                raise
            except APIStatusError as e:
                if e.status_code == 429 and attempt < _MAX_RETRIES - 1:
                    delay = _extract_retry_delay(e, attempt)
                    await asyncio.sleep(delay)
                    last_exc = e
                    continue
                raise OpenAIError(f"OpenAI request failed: {e}")
            except APITimeoutError:
                raise OpenAIError(f"Request timed out after {self.timeout}s")
            except json.JSONDecodeError as e:
                raise OpenAIError(f"Invalid JSON in response: {e}")
            except Exception as e:
                raise OpenAIError(f"OpenAI request failed: {e}")

        raise OpenAIError(f"OpenAI request failed after {_MAX_RETRIES} retries: {last_exc}")

    async def generate_stream(
        self,
        prompt: str,
        json_mode: bool = False,
        temperature: float = 0.3,
    ) -> AsyncIterator[str]:
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "stream": True,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        try:
            stream = await self.client.chat.completions.create(**kwargs)
            async for chunk in stream:
                delta = chunk.choices[0].delta if chunk.choices else None
                if delta and delta.content:
                    yield delta.content
        except APITimeoutError:
            raise OpenAIError(f"Request timed out after {self.timeout}s")
        except APIStatusError as e:
            raise OpenAIError(f"OpenAI streaming failed: {e}")
        except OpenAIError:
            raise
        except Exception as e:
            raise OpenAIError(f"OpenAI streaming failed: {e}")

    async def generate_with_tools(
        self,
        messages: list[dict],
        tools: list[dict],
    ) -> dict[str, Any]:
        last_exc: Exception | None = None
        for attempt in range(_MAX_RETRIES):
            try:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=tools if tools else None,
                )
                message = response.choices[0].message
                result: dict[str, Any] = {
                    "content": message.content or "",
                    "tool_calls": [],
                }
                if message.tool_calls:
                    for tc in message.tool_calls:
                        result["tool_calls"].append(
                            {
                                "function": {
                                    "name": tc.function.name,
                                    "arguments": json.loads(tc.function.arguments),
                                }
                            }
                        )
                return result
            except OpenAIError:
                raise
            except APIStatusError as e:
                if e.status_code == 429 and attempt < _MAX_RETRIES - 1:
                    delay = _extract_retry_delay(e, attempt)
                    await asyncio.sleep(delay)
                    last_exc = e
                    continue
                raise OpenAIError(f"OpenAI request failed: {e}")
            except APITimeoutError:
                raise OpenAIError(f"Request timed out after {self.timeout}s")
            except Exception as e:
                raise OpenAIError(f"OpenAI request failed: {e}")

        raise OpenAIError(f"OpenAI request failed after {_MAX_RETRIES} retries: {last_exc}")

    async def is_healthy(self) -> bool:
        try:
            await self.client.models.list()
            return True
        except Exception:
            return False
