import json
import time

from collections.abc import AsyncIterator
from typing import Annotated
from uuid import UUID
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from app.agent.runtime import AgentRuntime, AgentRuntimeError
from app.api.dependencies import (
    get_agent_runtime,
    get_chat_service,
    get_current_user_id,
)

from app.schemas.chat import ChatRequest, ChatResponse

router = APIRouter()

def encode_event(event:dict)->bytes:
    return (json.dumps(event,ensure_ascii=False))+"\n".encode("utf-8")


@router.post("/conversations/{conversation_id}/messages:stream")

async def stream_message(
    conversation_id:str,
    payload:ChatRequest,
    request:Request,
    agent_runtime:Annotated[AgentRuntime,Depends(get_agent_runtime)],
)->StreamingResponse:
    async def generate()->AsyncIterator[bytes]:
        run_id=str(uuid4())
        started=time.perf_counter()
        yield encode_event({"type": "run_started", "run_id": run_id})
        yield encode_event(
            {"type": "status", "label": "正在执行安全检查与本地知识检索"}
        )
        try:
            async for event in agent_runtime.stream(payload.message):
                if await request.is_disconnected():
                    break
                if event.type=="done":
                    latency_ms=int((time.perf_counter()-started)*1000)
                    yield encode_event(
                        {
                            "type":"done",
                            "run_id":run_id,
                            "latency_ms":latency_ms,
                        }
                    )
                else:
                    yield encode_event({"type:event.type,**event.data"})
        except AgentRuntimeError as exc:
            message = exc.message
            if exc.next_action:
                message+=f"下一步:{exc.next_action}"
            yield encode_event(
                {"type": "error", "code": exc.code, "message": message}
            )
        except Exception:
            # 真实项目中同时记录 trace_id 和完整异常，不能把内部异常暴露给用户。
            yield encode_event({"type": "error", "message": "生成失败，请稍后重试"})

    return StreamingResponse(generate(),media_type="application/x-ndjson")














async def chat(
    payload:ChatRequest,
    runtime:Annotated[AgentRuntime,Depends(get_agent_runtime)],
)->ChatResponse:
    try:
        answer = await runtime.invoke(payload.message)
    except AgentRuntimeError as exc:
        if exc.code in {
            "BIOMEDICAL_POLICY_BLOCKED",
            "BIOMEDICAL_TOPIC_NOT_FOUND",
        }:
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
        elif exc.retryable or exc.code.startswith("LLM_"):
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE
        else:
            status_code=status.HTTP_502_BAD_GATEWAY

        detail=exc.message
        if exc.next_action:
            detail+=f"下一步：{exc.next_action}"
        raise HTTPException(status_code=status_code,detail=detail)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="BioAgent 暂时不可用，请稍后重试"
        )from exc

    return ChatResponse(
        conversation_id=payload.conversation_id or str(uuid4()),
        answer=answer
    )