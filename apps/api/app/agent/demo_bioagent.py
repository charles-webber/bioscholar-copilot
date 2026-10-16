#from collections.abc import AsyncIterator

#from app.agent.runtime import AgentEvent
from app.agent.runtime import AgentAnswer

class DemoAgentRuntime:
    def invoke(self, message: str) -> AgentAnswer:
        return AgentAnswer(text="BioAgent 已收到你的问题：{message}",model="demo")
'''
    async def stream(self, message: str) -> AsyncIterator[AgentEvent]:
        yield AgentEvent(type="delta", data={"text": await self.invoke(message)})
        yield AgentEvent(type="done", data={})
'''