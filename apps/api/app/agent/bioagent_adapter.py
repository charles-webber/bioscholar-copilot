#import asyncio
#from collections.abc import AsyncGenerator
from threading import Lock
from typing import Any,Callable

from app.agent.legacy_bioagent.biomedical_agent import run_biomedical_agent
from app.agent.runtime import AgentAnswer,AgentRuntimeError

Runner=Callable[...,dict[str,Any]]


class BioAgentAdapter:
    def __init__(self,runner:Runner=run_biomedical_agent)->None:
        self._runner=runner
        # 这里异步换成同步
        # self._lock=asyncio.Lock()
        self._lock=Lock()
    #删除async
    def invoke(self,message:str)->AgentAnswer:
        with self._lock:
            result=self._runner(task=message)

        if result.get("ok") is True:    
            summary=result.get("summary")
            if not isinstance(summary, str) or not summary.strip():
                raise AgentRuntimeError(
                    code="BIOMEDICAL_INVALID_RESULT",
                    message="Biomedical Agent 成功结果中缺少 summary。"
                )
            llm = result.get("llm") if isinstance(result.get("llm"),dict) else {}
            usage = result.get("usage") if isinstance(llm.get("usage"),dict) else {}
            return AgentAnswer(
                text=summary,
                topic=str(result.get("resolved_topic") or "") or None,
                source_refs=tuple(result.get("source_refs") or ()),
                model=str(llm.get("model") or "") or None,
                input_tokens=usage.get("prompt_tokens") or usage.get("input_tokens"),
                output_tokens=usage.get("completion_tokens") or usage.get("output_tokens"),
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
'''
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
'''
