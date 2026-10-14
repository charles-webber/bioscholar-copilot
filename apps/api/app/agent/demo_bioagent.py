from collections.abc import AsyncIterator

from app.agent.runtime import AgentEvent


class DemoAgentRuntime:
    async def invoke(self, message: str) -> str:
        return f"BioAgent 已收到你的问题：{message}"

    async def stream(self, message: str) -> AsyncIterator[AgentEvent]:
        yield AgentEvent(type="delta", data={"text": await self.invoke(message)})
        yield AgentEvent(type="done", data={})