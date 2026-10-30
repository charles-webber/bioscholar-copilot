import time
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status

from app.agent.runtime import AgentRuntime, AgentRuntimeError
from app.api.dependencies import get_agent_runtime, get_chat_service, get_current_user_id
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_service import (
    ChatService,
    ConversationBusyError,
    ConversationNotFoundError,
)


router = APIRouter()


def agent_http_error(error: AgentRuntimeError) -> HTTPException:
    if error.code in {"BIOMEDICAL_POLICY_BLOCKED", "BIOMEDICAL_TOPIC_NOT_FOUND"}:
        status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    elif error.retryable:
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    else:
        status_code = status.HTTP_502_BAD_GATEWAY
    return HTTPException(
        status_code=status_code,
        detail={
            "code": error.code,
            "message": error.message,
            "next_action": error.next_action,
            "retryable": error.retryable,
        },
    )


def unavailable_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail={
            "code": "AGENT_UNAVAILABLE",
            "message": "BioAgent 暂时不可用，请稍后重试。",
            "next_action": "稍后重试。",
            "retryable": True,
        },
    )


@router.post("/chat", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    runtime: Annotated[AgentRuntime, Depends(get_agent_runtime)],
) -> ChatResponse:
    try:
        answer = runtime.invoke(payload.message)
    except AgentRuntimeError as error:
        raise agent_http_error(error) from error
    except Exception as error:
        raise unavailable_error() from error
    return ChatResponse(
        conversation_id=payload.conversation_id or uuid4(),
        answer=answer.text,
        citations=[],
    )


@router.post("/conversations/{conversation_id}/messages", response_model=ChatResponse)
def send_message(
    conversation_id: UUID,
    payload: ChatRequest,
    runtime: Annotated[AgentRuntime, Depends(get_agent_runtime)],
    service: Annotated[ChatService, Depends(get_chat_service)],
    owner_id: Annotated[UUID, Depends(get_current_user_id)],
) -> ChatResponse:
    try:
        run_id = service.start_run(conversation_id, owner_id, payload.message)
    except ConversationNotFoundError as error:
        raise HTTPException(status_code=404, detail="会话不存在") from error
    except ConversationBusyError as error:
        raise HTTPException(status_code=409, detail="当前会话正在生成回答") from error

    started = time.perf_counter()
    try:
        answer = runtime.invoke(payload.message)
    except AgentRuntimeError as error:
        service.fail_run(run_id, error.code, int((time.perf_counter() - started) * 1000))
        raise agent_http_error(error) from error
    except Exception as error:
        service.fail_run(run_id, "AGENT_UNAVAILABLE", int((time.perf_counter() - started) * 1000))
        raise unavailable_error() from error

    latency_ms = int((time.perf_counter() - started) * 1000)
    service.complete_run(run_id, conversation_id, answer.text, latency_ms)
    return ChatResponse(
        conversation_id=conversation_id,
        answer=answer.text,
        citations=[],
    )