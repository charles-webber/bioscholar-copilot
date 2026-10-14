from collections.abc import AsyncGenerator
from typing import Protocol

class AgentEvent:
    def __init__(self,event_type:str,data:dict):
        self.type=event_type
        self.data=data

class Agentruntime(Protocol):
    async def invoke(self,message:str)->str:...
    async def stream(self,message:str)->AsyncInterator[AgentEvent]:...