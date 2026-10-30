import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AsyncOpenAI,
    AuthenticationError,
    RateLimitError,
)

from app.agent.runtime import AgentRuntimeError
from app.agent.streaming_runtime import AgentGenerationCancelled


@dataclass(frozen=True)
class ModelDelta:
    text: str


def _map_error(error: Exception) -> AgentRuntimeError:
    if isinstance(error, AuthenticationError):
        return AgentRuntimeError("LLM_AUTH_FAILED", "模型认证失败。", "检查 API Key。")
    if isinstance(error, RateLimitError):
        return AgentRuntimeError("LLM_RATE_LIMITED", "模型请求受限。", "稍后重试。", True)
    if isinstance(error, APITimeoutError):
        return AgentRuntimeError("LLM_TIMEOUT", "模型请求超时。", "稍后重试。", True)
    if isinstance(error, APIConnectionError):
        return AgentRuntimeError("LLM_CONNECTION_ERROR", "无法连接模型接口。", "检查网络和 Base URL。", True)
    if isinstance(error, APIStatusError):
        retryable = error.status_code in {408, 409, 429} or error.status_code >= 500
        return AgentRuntimeError(
            f"LLM_HTTP_{error.status_code}",
            f"模型接口返回 HTTP {error.status_code}。",
            "检查模型服务日志或稍后重试。",
            retryable,
        )
    return AgentRuntimeError("LLM_STREAM_ERROR", "模型流读取失败。", "检查服务日志。", True)


async def _next_or_cancel(iterator: Any, cancel_event: asyncio.Event) -> Any:
    next_task = asyncio.create_task(anext(iterator))
    cancel_task = asyncio.create_task(cancel_event.wait())
    done, pending = await asyncio.wait(
        {next_task, cancel_task},
        return_when=asyncio.FIRST_COMPLETED,
    )
    for task in pending:
        task.cancel()
    await asyncio.gather(*pending, return_exceptions=True)
    if cancel_task in done and cancel_task.result():
        next_task.cancel()
        await asyncio.gather(next_task, return_exceptions=True)
        raise AgentGenerationCancelled
    return next_task.result()


class NativeModelStreamer:
    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        api_style: str,
        timeout_seconds: float = 20.0,
    ) -> None:
        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout_seconds,
            max_retries=1,
        )
        self._model = model
        self._api_style = api_style

    async def stream_text(
        self,
        system_prompt: str,
        user_prompt: str,
        max_output_tokens: int,
        cancel_event: asyncio.Event,
    ) -> AsyncIterator[ModelDelta]:
        try:
            if self._api_style == "chat_completions":
                async for delta in self._stream_chat(
                    system_prompt, user_prompt, max_output_tokens, cancel_event
                ):
                    yield delta
                return
            if self._api_style == "responses":
                async for delta in self._stream_responses(
                    system_prompt, user_prompt, max_output_tokens, cancel_event
                ):
                    yield delta
                return
            raise AgentRuntimeError(
                "LLM_CONFIG_ERROR",
                "BIOMEDICAL_LLM_API_STYLE 配置无效。",
                "使用 chat_completions 或 responses。",
            )
        except (asyncio.CancelledError,AgentGenerationCancelled):
            raise
        except AgentRuntimeError:
            raise
        except Exception as error:
            raise _map_error(error) from error

    async def _stream_chat(
        self,
        system_prompt: str,
        user_prompt: str,
        max_output_tokens: int,
        cancel_event: asyncio.Event,
    ) -> AsyncIterator[ModelDelta]:
        stream = await self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=max_output_tokens,
            stream=True,
        )
        iterator = stream.__aiter__()
        try:
            while True:
                try:
                    chunk = await _next_or_cancel(iterator, cancel_event)
                except StopAsyncIteration:
                    break
                if not chunk.choices:
                    continue
                text = chunk.choices[0].delta.content or ""
                if text:
                    yield ModelDelta(text)
        finally:
            await stream.close()

    async def _stream_responses(
        self,
        system_prompt: str,
        user_prompt: str,
        max_output_tokens: int,
        cancel_event: asyncio.Event,
    ) -> AsyncIterator[ModelDelta]:
        manager = self._client.responses.stream(
            model=self._model,
            instructions=system_prompt,
            input=user_prompt,
            max_output_tokens=max_output_tokens,
        )
        async with manager as stream:
            iterator = stream.__aiter__()
            while True:
                try:
                    event = await _next_or_cancel(iterator, cancel_event)
                except StopAsyncIteration:
                    break
                if event.type == "response.output_text.delta" and event.delta:
                    yield ModelDelta(event.delta)