import asyncio
import hashlib
from collections.abc import AsyncIterator
from uuid import UUID

from app.agent.legacy_bioagent import agent_fourday as core
from app.agent.legacy_bioagent.biomedical_agent import configure_core
from app.agent.legacy_bioagent.biomedical_kb import list_topics, resolve_topic
from app.agent.legacy_bioagent.biomedical_policy import check_model_output, check_request
from app.agent.legacy_bioagent.context_builder import (
    build_context,
    build_evidence,
    build_system_prompt,
    build_user_prompt,
    load_recent_trace,
)
from app.agent.runtime import AgentRuntimeError
from app.agent.streaming_llm_client import NativeModelStreamer
from app.agent.streaming_runtime import (
    AgentGenerationCancelled,
    AgentStreamEvent,
)


class StreamingBioAgent:
    def __init__(self, model_streamer: NativeModelStreamer) -> None:
        self._model_streamer = model_streamer
        self._legacy_state_lock = asyncio.Lock()

    async def stream(
        self,
        message: str,
        run_id: UUID,
        cancel_event: asyncio.Event,
    ) -> AsyncIterator[AgentStreamEvent]:
        yield AgentStreamEvent("run_started", run_id)
        self._raise_if_cancelled(cancel_event)

        policy = check_request(message)
        if not policy.allowed:
            raise AgentRuntimeError(
                "BIOMEDICAL_POLICY_BLOCKED",
                policy.reason,
                policy.next_action,
            )

        yield AgentStreamEvent("tool_started", run_id, tool="local_notes")
        async with self._legacy_state_lock:
            notes = configure_core()
            topic = resolve_topic(message, notes)
            if topic is None:
                topics = ", ".join(list_topics(notes)[:12])
                raise AgentRuntimeError(
                    "BIOMEDICAL_TOPIC_NOT_FOUND",
                    "没有识别出知识库中的生物医学主题。",
                    f"请尝试具体主题，例如：{topics}",
                )
            search = core.call_read_tool(
                core.search_notes_page,
                {"query": topic, "response_format": "detailed"},
            )
            if not search["ok"]:
                self._raise_tool_error(search)
            note_ref = search["result"][0]["note_ref"]
            read = core.call_read_tool(
                core.get_note_chunk,
                {"note_ref": note_ref, "cursor": 0, "max_chars": 240},
            )
            if not read["ok"]:
                self._raise_tool_error(read)
            evidence = build_evidence(
                ref=f"note:{note_ref}:cursor=0",
                title=note_ref,
                content=read["content"],
                source="notes_long.txt",
                cursor=0,
                max_chars=240,
            )
            system_prompt = build_system_prompt()
            context = build_context(
                system=system_prompt,
                task=message,
                memory={"resolved_topic": topic, "note_ref": note_ref},
                retrieved_evidence=[evidence],
                recent_trace=load_recent_trace(core.TRACE_FILE, max_items=3),
            )
            user_prompt = build_user_prompt(context)

        yield AgentStreamEvent("tool_completed", run_id, tool="local_notes")
        self._raise_if_cancelled(cancel_event)

        answer = ""
        async for delta in self._model_streamer.stream_text(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_output_tokens=2048,
            cancel_event=cancel_event,
        ):
            self._raise_if_cancelled(cancel_event)
            remaining = 1200 - len(answer)
            if remaining <= 0:
                break
            visible = delta.text[:remaining]
            candidate = answer + visible
            if candidate.strip():
                output_policy = check_model_output(candidate)
                if not output_policy.allowed:
                    raise AgentRuntimeError(
                        "MODEL_OUTPUT_BLOCKED",
                        output_policy.reason,
                        output_policy.next_action,
                    )
            answer = candidate
            if visible:
                yield AgentStreamEvent("text_delta", run_id, text=visible)

        self._raise_if_cancelled(cancel_event)
        if not answer.strip():
            raise AgentRuntimeError(
                "LLM_EMPTY_RESPONSE",
                "模型调用成功，但回答内容为空。",
                "稍后重试。",
                True,
            )

        task_hash = hashlib.sha256(message.encode("utf-8")).hexdigest()[:12]
        async with self._legacy_state_lock:
            write_result = core.write_summary_once(
                answer,
                f"summary-{topic.casefold()}-{task_hash}",
            )
        if not write_result["ok"]:
            self._raise_tool_error(write_result)

    @staticmethod
    def _raise_if_cancelled(cancel_event: asyncio.Event) -> None:
        if cancel_event.is_set():
            raise AgentGenerationCancelled

    @staticmethod
    def _raise_tool_error(result: dict[str, object]) -> None:
        error = result["error"]
        if not isinstance(error, dict):
            raise AgentRuntimeError("TOOL_ERROR", "工具执行失败。")
        raise AgentRuntimeError(
            str(error.get("code", "TOOL_ERROR")),
            str(error.get("message", "工具执行失败。")),
            str(error.get("next_action", "检查服务日志。")),
            bool(error.get("retryable", False)),
        )