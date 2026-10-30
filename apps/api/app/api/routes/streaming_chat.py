import asyncio
import logging
import time
from collections.abc import AsyncIterator
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from app.agent.run_registry import RunRegistry
from app.agent.runtime import AgentRuntimeError
from app.agent.streaming_runtime import (
    AgentGenerationCancelled,
    AgentStreamEvent,
    StreamingAgentRuntime,
)
from app.api.dependencies import (
    get_chat_service,
    get_current_user_id,
    get_run_registry,
    get_streaming_agent_runtime,
)
from app.api.sse import encode_sse
from app.schemas.chat import ChatRequest
from app.services.chat_service import (
    ChatService,
    ConversationBusyError,
    ConversationNotFoundError,
    RunNotFoundError,
)


router = APIRouter()
logger = logging.getLogger(__name__)

def _latency_ms(started:float)->int:
    return int((time.perf_counter()-started)*1000)

async def _watch_disconnect(request:Request,cancel_event:asyncio.Event)->None:
    while not cancel_event.is_set():
        if await request.is_disconnected():
            cancel_event.set()
            return
        await asyncio.sleep(0.1)
    
@router.post("/conversations/{conversation_id}/messages:stream")
async def stream_message(
    conversation_id: UUID,
    payload: ChatRequest,
    request: Request,
    runtime: Annotated[StreamingAgentRuntime, Depends(get_streaming_agent_runtime)],
    service: Annotated[ChatService, Depends(get_chat_service)],
    registry: Annotated[RunRegistry, Depends(get_run_registry)],
    owner_id: Annotated[UUID, Depends(get_current_user_id)],
) -> StreamingResponse:
    try:
        run_id=service.start_run(conversation_id,owner_id,payload.message)
    except ConversationNotFoundError as error:
        raise HTTPException(status_code=404,detail="会话不存在")
    except ConversationBusyError as error:
        raise HTTPException(status_code=409, detail="当前会话正在生成回答") from error

    active = await registry.register(run_id,owner_id)
#!这里好好看看
    async def events() -> AsyncIterator[bytes]:
        started = time.perf_counter()
        partial_answer = ""
        watcher = asyncio.create_task(
            _watch_disconnect(request, active.cancel_event)
        )
        try:
            async for event in runtime.stream(
                payload.message, run_id, active.cancel_event
            ):
                if event.type == "text_delta":
                    partial_answer += event.text or ""
                yield encode_sse(event.type, event.to_dict())

            latency = _latency_ms(started)
            service.complete_run(run_id, conversation_id, partial_answer, latency)
            completed = AgentStreamEvent(
                "run_completed", run_id, latency_ms=latency
            )
            yield encode_sse(completed.type, completed.to_dict())

        except AgentGenerationCancelled:
            latency = _latency_ms(started)
            service.cancel_run(
                run_id, conversation_id, partial_answer, latency
            )
            cancelled = AgentStreamEvent(
                "run_cancelled",
                run_id,
                message="已停止生成，已保留当前回答。",
                latency_ms=latency,
            )
            if not await request.is_disconnected():
                yield encode_sse(cancelled.type, cancelled.to_dict())
        except asyncio.CancelledError:
            latency = _latency_ms(started)
            service.cancel_run(
                run_id, conversation_id, partial_answer, latency
            )
            raise

        except AgentRuntimeError as error:
            latency = _latency_ms(started)

            if error.code in {"BIOMEDICAL_POLICY_BLOCKED", "BIOMEDICAL_TOPIC_NOT_FOUND"}:
                reply = "\n".join(
                    part for part in (error.message, error.next_action) if part
                )

                saved = service.complete_run(run_id, conversation_id, reply, latency)
                if not saved:
                    return

                delta = AgentStreamEvent("text_delta", run_id, text=reply)
                yield encode_sse(delta.type, delta.to_dict())

                completed = AgentStreamEvent("run_completed", run_id, latency_ms=latency)
                yield encode_sse(completed.type, completed.to_dict())
                return

            service.fail_run(run_id, error.code, latency, partial_answer)
            failed = AgentStreamEvent(
                "run_error", run_id, message=error.message, code=error.code
            )
            yield encode_sse(failed.type, failed.to_dict())



        except Exception:
            logger.exception("streaming agent failed", extra={"run_id": str(run_id)})
            latency = _latency_ms(started)
            try:
                service.fail_run(run_id, "AGENT_UNAVAILABLE", latency, partial_answer)
            except Exception:
                logger.exception("保存失败状态时再次发生异常")
            failed = AgentStreamEvent(
                "run_error",
                run_id,
                message="BioAgent 暂时不可用，请稍后重试。",
                code="AGENT_UNAVAILABLE",
            )
            yield encode_sse(failed.type, failed.to_dict())
        finally:
            watcher.cancel()
            await asyncio.gather(watcher, return_exceptions=True)
            await registry.unregister(run_id)

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
        },
    )

@router.post("/runs/{run_id}/cancel", status_code=status.HTTP_202_ACCEPTED)
async def cancel_run(
    run_id: UUID,
    service: Annotated[ChatService, Depends(get_chat_service)],
    registry: Annotated[RunRegistry, Depends(get_run_registry)],
    owner_id: Annotated[UUID, Depends(get_current_user_id)],
) -> dict[str, str | bool]:
    try:
        run = service.get_owned_run(run_id, owner_id)
    except RunNotFoundError as error:
        raise HTTPException(status_code=404, detail="运行不存在") from error

    if run.status != "running":
        return {"run_id": str(run_id), "status": run.status, "accepted": False}

    accepted = await registry.request_cancel(run_id, owner_id)
    if not accepted:
        raise HTTPException(
            status_code=409,
            detail="运行不在当前 API 进程；请检查 worker 配置",
        )
    return {"run_id": str(run_id), "status": "cancelling", "accepted": True}