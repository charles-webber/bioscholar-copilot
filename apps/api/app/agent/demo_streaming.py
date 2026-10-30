import asyncio
from collections.abc import AsyncIterator
from uuid import UUID

from app.agent.streaming_runtime import AgentGenerationCancelled, AgentStreamEvent


class DemoStreamingRuntime:
    async def stream(
        self,
        message: str,
        run_id: UUID,
        cancel_event: asyncio.Event,
    ) -> AsyncIterator[AgentStreamEvent]:
        yield AgentStreamEvent("run_started", run_id)
        await asyncio.sleep(0)
        if cancel_event.is_set():
            raise AgentGenerationCancelled
        yield AgentStreamEvent(
            "text_delta",
            run_id,
            text=f"BioAgent 已收到你的问题：{message}",
        )