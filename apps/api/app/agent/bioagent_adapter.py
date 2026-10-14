import asyncio
from collections.abc import AsyncGenerator
from typing import Any,Callable

from app.agent.legacy_bioagent.biomedical_agent import run_biomedical_agent
from app.agent.runtime import AgentEvent,AgentRuntimeError

Runner=Callable[...,dict[str,Any]]


class BioAgentAdapter:
    def __init__(self,runner:Runner=run_biomedical_agent)->None:
        self._runner=runner
        # 旧代码会修改模块全局变量；单进程内先串行执行，避免请求互相覆盖。
        self._lock=asyncio.Lock()

    async def invoke(self,message:str)->str:
        async with self._lock:
            result=await asyncio.to_thread(self._runner,task=message)

        if result.get("ok") is True:    
            summary=result.get("summary")
            if isinstance(summary,str) and summary.strip():
                return summary
            raise AgentRuntimeError(
                code="BIOMEDICAL_INVALID_RESULT",
                message="Biomedical Agent 成功结果中缺少 summary。"
            )

        error = result.get("error")
        if not isinstance(error,dict):
            raise AgentRuntimeError(
                code="BIOMEDICAL_INVALID_RESULT",
                message="Biomedical Agent 返回了无法识别的失败结果。",
            )

        raise AgentRuntimeError(
            code=str(error.get("code","BIOMEDICAL_UNKNOWN_ERROR")),
            message=str(error.get("message", "Biomedical Agent 执行失败。")),
            next_action=str(error.get("next_action","")),
            retryable=bool(error.get("retryable",False))
        )

    async def stream(self,message:str)->AsyncGenerator[AgentEvent]:
       # 先完成旧项目的整段生成和输出安全检查，再分块交给 UI。
        answer=await self.invoke(message)
        for start in range(0,len(answer),24):
            yield AgentEvent(
                type="delta",
                data={"text":answer[start:start+24]}
            )
            await asyncio.sleep(0)
        yield AgentEvent(type="done",data={})

