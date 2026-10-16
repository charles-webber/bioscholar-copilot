#from collections.abc import AsyncGenerator
from dataclasses import dataclass
#from typing import Any
from typing import Protocol

#区别
@dataclass(frozen=True)
class AgentAnswer:
    text:str
    topic:str|None=None
    source_refs:tuple[str,...]=()
    model:str|None=None
    input_tokens:str|None=None
    output_tokens:str|None=None
'''
class AgentEvent:
    type:str
    data:dict[str,Any]
'''
class AgentRuntimeError(RuntimeError):
    def __init__(
        self,
        code:str,
        message:str,
        next_action:str="",
        retryable:bool=False,
    )->None:
        super().__init__(message)
        self.code=code
        self.message=message
        self.next_action=next_action
        self.retryable=retryable

class AgentRuntime(Protocol):
    #async def invoke(self,message:str)->str:...
    def invoke(self,message:str)->AgentAnswer:...