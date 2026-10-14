from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status

from app.agent.runtime import AgentRuntime, AgentRuntimeError
from app.api.dependencies import get_agent_runtime
from app.schemas.chat import ChatRequest, ChatResponse

router = APIRouter()

@router.post("/chat",response_model=ChatResponse)
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