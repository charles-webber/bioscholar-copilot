import asyncio
from collections.abc import AsyncGenerator
from dataclasses import asdict,dataclass
from typing import Literal,Protocol
from uuid import UUID

EventType = Literal[
    "run_started",
    "text_delta",
    "tool_started",
    "tool_completed",
    "run_completed",
    "run_cancelled",
    "run_error",
]

@dataclass(frozen=True)
class AgentStreamEvent:
    type: EventType
    run_id: UUID
    text: str | None = None
    tool: str | None = None
    message: str | None = None
    code: str | None = None
    latency_ms: int | None = None
    
    def to_dict(self)->dict[str,str|int]:
        values=asdict(self)
        values["run_id"]=str(self.run_id)
        return {key:value for key,value in values.items() if value is not None}

class AgentGenerationCancelled(Exception):
    """协作取消信号被观察到；它不是模型失败。"""

class StreamingAgentRuntime(Protocol):
    def stream(
        self,
        message: str,
        run_id: UUID,
        cancel_event: asyncio.Event,
    )->AsyncIterator[AgentStreamEvent]:
        """产生一次运行的领域事件。"""
        raise NotImplementedError