import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from backend.services.llm.openai import OpenAIProvider, OpenAIError, _extract_retry_delay
from backend.services.llm.factory import create_llm_provider, ProviderConfigError


def _mock_response(content="Hello", tool_calls=None):
    message = MagicMock()
    message.content = content
    message.tool_calls = tool_calls
    choice = MagicMock()
    choice.message = message
    response = MagicMock()
    response.choices = [choice]
    return response


def _mock_tool_call(name="my_func", arguments='{"key": "value"}'):
    tc = MagicMock()
    tc.function.name = name
    tc.function.arguments = arguments
    return tc


class TestOpenAIProvider:

    def setup_method(self):
        with patch("backend.services.llm.openai.AsyncOpenAI"):
            self.provider = OpenAIProvider(api_key="test-key")

    @pytest.mark.asyncio
    async def test_generate_returns_text(self):
        self.provider.client.chat.completions.create = AsyncMock(
            return_value=_mock_response("Hello world")
        )
        result = await self.provider.generate("Say hello")
        assert result == {"text": "Hello world"}

    @pytest.mark.asyncio
    async def test_generate_json_mode(self):
        self.provider.client.chat.completions.create = AsyncMock(
            return_value=_mock_response('{"key": "value"}')
        )
        result = await self.provider.generate("Return JSON", json_mode=True)
        assert result == {"key": "value"}

    @pytest.mark.asyncio
    async def test_generate_json_mode_passes_response_format(self):
        self.provider.client.chat.completions.create = AsyncMock(
            return_value=_mock_response('{"a": 1}')
        )
        await self.provider.generate("Return JSON", json_mode=True)
        call_kwargs = self.provider.client.chat.completions.create.call_args[1]
        assert call_kwargs["response_format"] == {"type": "json_object"}

    @pytest.mark.asyncio
    async def test_generate_empty_response_raises(self):
        self.provider.client.chat.completions.create = AsyncMock(
            return_value=_mock_response(content=None)
        )
        with pytest.raises(OpenAIError, match="empty response"):
            await self.provider.generate("Say hello")

    @pytest.mark.asyncio
    async def test_generate_rate_limit_retries(self):
        from openai import APIStatusError

        error_response = httpx.Response(429, headers={"retry-after": "0"}, request=httpx.Request("POST", "https://api.openai.com"))
        exc = APIStatusError("rate limited", response=error_response, body=None)

        self.provider.client.chat.completions.create = AsyncMock(
            side_effect=[exc, _mock_response("ok")]
        )
        result = await self.provider.generate("test")
        assert result == {"text": "ok"}
        assert self.provider.client.chat.completions.create.call_count == 2

    @pytest.mark.asyncio
    async def test_generate_rate_limit_exhausted(self):
        from openai import APIStatusError

        error_response = httpx.Response(429, headers={"retry-after": "0"}, request=httpx.Request("POST", "https://api.openai.com"))
        exc = APIStatusError("rate limited", response=error_response, body=None)

        self.provider.client.chat.completions.create = AsyncMock(
            side_effect=[exc, exc, exc]
        )
        with pytest.raises(OpenAIError, match="OpenAI request failed"):
            await self.provider.generate("test")

    @pytest.mark.asyncio
    async def test_generate_timeout_raises(self):
        from openai import APITimeoutError

        self.provider.client.chat.completions.create = AsyncMock(
            side_effect=APITimeoutError(request=httpx.Request("POST", "https://api.openai.com"))
        )
        with pytest.raises(OpenAIError, match="timed out"):
            await self.provider.generate("test")

    @pytest.mark.asyncio
    async def test_generate_invalid_json_raises(self):
        self.provider.client.chat.completions.create = AsyncMock(
            return_value=_mock_response("not json")
        )
        with pytest.raises(OpenAIError, match="Invalid JSON"):
            await self.provider.generate("test", json_mode=True)

    @pytest.mark.asyncio
    async def test_generate_with_tools_returns_tool_calls(self):
        tc = _mock_tool_call("get_weather", '{"city": "NYC"}')
        self.provider.client.chat.completions.create = AsyncMock(
            return_value=_mock_response(content="", tool_calls=[tc])
        )
        result = await self.provider.generate_with_tools(
            messages=[{"role": "user", "content": "weather?"}],
            tools=[{"type": "function", "function": {"name": "get_weather"}}],
        )
        assert result["tool_calls"] == [
            {"function": {"name": "get_weather", "arguments": {"city": "NYC"}}}
        ]

    @pytest.mark.asyncio
    async def test_generate_with_tools_no_tool_calls(self):
        self.provider.client.chat.completions.create = AsyncMock(
            return_value=_mock_response("Just text", tool_calls=None)
        )
        result = await self.provider.generate_with_tools(
            messages=[{"role": "user", "content": "hello"}],
            tools=[],
        )
        assert result == {"content": "Just text", "tool_calls": []}

    @pytest.mark.asyncio
    async def test_is_healthy_returns_true(self):
        self.provider.client.models.list = AsyncMock(return_value=MagicMock())
        assert await self.provider.is_healthy() is True

    @pytest.mark.asyncio
    async def test_is_healthy_returns_false_on_error(self):
        self.provider.client.models.list = AsyncMock(side_effect=Exception("fail"))
        assert await self.provider.is_healthy() is False


class TestExtractRetryDelay:

    def test_reads_retry_after_header(self):
        response = httpx.Response(429, headers={"retry-after": "5"}, request=httpx.Request("POST", "https://api.openai.com"))
        from openai import APIStatusError
        exc = APIStatusError("rate limited", response=response, body=None)
        assert _extract_retry_delay(exc, 0) == 6.0

    def test_exponential_fallback(self):
        response = httpx.Response(429, request=httpx.Request("POST", "https://api.openai.com"))
        from openai import APIStatusError
        exc = APIStatusError("rate limited", response=response, body=None)
        assert _extract_retry_delay(exc, 0) == 2
        assert _extract_retry_delay(exc, 1) == 4
        assert _extract_retry_delay(exc, 2) == 8


class TestFactoryOpenAI:

    def test_creates_openai_provider(self):
        with patch("backend.services.llm.factory.OpenAIProvider") as mock_cls:
            create_llm_provider(provider="openai", openai_api_key="sk-test")
            mock_cls.assert_called_once_with(
                api_key="sk-test",
                model="gpt-4.1-mini",
                timeout=120,
            )

    def test_missing_key_raises(self):
        with pytest.raises(ProviderConfigError, match="OpenAI requires api_key"):
            create_llm_provider(provider="openai")

    def test_custom_model(self):
        with patch("backend.services.llm.factory.OpenAIProvider") as mock_cls:
            create_llm_provider(
                provider="openai",
                openai_api_key="sk-test",
                openai_model="gpt-4.1-nano",
            )
            mock_cls.assert_called_once_with(
                api_key="sk-test",
                model="gpt-4.1-nano",
                timeout=120,
            )

    def test_default_model(self):
        with patch("backend.services.llm.factory.OpenAIProvider") as mock_cls:
            create_llm_provider(provider="openai", openai_api_key="sk-test")
            _, kwargs = mock_cls.call_args
            assert kwargs["model"] == "gpt-4.1-mini"
