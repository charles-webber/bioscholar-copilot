#import json
import time
#from collections.abc import AsyncIterator


import logging
from typing import Annotated
from uuid import UUID
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status

from app.agent.runtime import AgentRuntime, AgentRuntimeError
from app.api.dependencies import (
    get_agent_runtime,
    get_chat_service,
    get_current_user_id,
)
from app.schemas.chat import ChatRequest, ChatResponse

from app.services.chat_service import ChatService,ConversationNotFoundError

router = APIRouter()
logger = logging.getLogger(__name__)

def agent_http_error(exc:AgentRuntimeError)->HTTPException:
    if exc.code in {"BIOMEDICAL_POLICY_BLOCKED","BIOMEDICAL_TOPIC_NOT_FOUND"}:
        status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    elif exc.retryable:
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    else:
        status_code = status.HTTP_502_BAD_GATEWAY
    return HTTPException(
        status_code=status_code,
        detail={
            "code": exc.code,
            "message": exc.message,
            "next_action": exc.next_action,
            "retryable": exc.retryable,            
        }
    )

def unavailable_error()->HTTPException:
    return HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail={
            "code": "AGENT_UNAVAILABLE",
            "message": "BioAgent 暂时不可用，请稍后重试。",
            "next_action": "稍后重试。",
            "retryable": True,
        }
    )





@router.post("/chat", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    runtime: Annotated[AgentRuntime, Depends(get_agent_runtime)],
) -> ChatResponse:
    try:
        answer = runtime.invoke(payload.message)

    except AgentRuntimeError as exc:
       raise agent_http_error(exc) from exc
    except Exception as exc:
        raise unavailable_error() from exc
    

    return ChatResponse(
        conversation_id=payload.conversation_id or uuid4(),
        answer=answer.text,
        citations=[],
    )


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=ChatResponse,
)    
def send_message(
    conversation_id:UUID,
    payload:ChatRequest,
    runtime:Annotated[AgentRuntime,Depends(get_agent_runtime)],
    services:Annotated[ChatService,Depends(get_chat_service)],
    owner_id:Annotated[UUID,Depends(get_current_user_id)],
)->ChatResponse:
    try:
        run_id = services.start_run(conversation_id,owner_id,payload.message)
    except ConversationNotFoundError as exc:
        raise HTTPException(status_code=404,detail="会话不存在")from exc
        
    started = time.perf_counter()
    
    try :
        answer = runtime.invoke(payload.message)
    except AgentRuntimeError as exc:
        latency_ms = int((time.perf_counter()-started)*1000)
        services.fail_run(run_id,exc.code,latency_ms)
        raise agent_http_error(exc) from exc
    except Exception as exc:
        latency_ms = int((time.perf_counter() - started) * 1000)
        services.fail_run(run_id, "AGENT_UNAVAILABLE", latency_ms)
        raise unavailable_error() from exc

    latency_ms = int((time.perf_counter() - started) * 1000)
    services.complete_run(run_id, conversation_id, answer, latency_ms)
    return ChatResponse(
        conversation_id=conversation_id,
        answer=answer.text,
        citations=[],
    )














