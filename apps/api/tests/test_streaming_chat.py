import asyncio
import json
from collections.abc import AsyncIterator
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agent.run_registry import RunRegistry
from app.agent.runtime import AgentAnswer
from app.agent.streaming_runtime import AgentStreamEvent
from app.api.dependencies import (
    get_agent_runtime,
    get_current_user_id,
    get_run_registry,
    get_streaming_agent_runtime,
)
from app.db.models.message import Message
from app.db.models.run import AgentRun
from app.main import app
from conftest import OTHER_OWNER_ID, OWNER_ID


class FakeStreamingRuntime:
    async def stream(
        self,
        message: str,
        run_id: UUID,
        cancel_event: asyncio.Event,
    ) -> AsyncIterator[AgentStreamEvent]:
        yield AgentStreamEvent("run_started", run_id)
        yield AgentStreamEvent("text_delta", run_id, text="PCR ")
        yield AgentStreamEvent("text_delta", run_id, text="是扩增技术。")


class FailingStreamingRuntime:
    async def stream(
        self,
        message: str,
        run_id: UUID,
        cancel_event: asyncio.Event,
    ) -> AsyncIterator[AgentStreamEvent]:
        yield AgentStreamEvent("run_started", run_id)
        raise RuntimeError("provider down")
        yield AgentStreamEvent("text_delta", run_id, text="不可到达")


class FakeSyncRuntime:
    def invoke(self, message: str) -> AgentAnswer:
        return AgentAnswer(text=f"同步：{message}", model="test")


def create_conversation(client: TestClient) -> str:
    response = client.post("/api/conversations", json={"title": "新对话"})
    assert response.status_code == 201
    return str(response.json()["id"])


def sse_events(response_text: str) -> list[dict[str, object]]:
    events: list[dict[str, object]] = []
    for frame in response_text.replace("\r\n", "\n").split("\n\n"):
        data_lines = [line[5:].lstrip() for line in frame.splitlines() if line.startswith("data:")]
        if data_lines:
            events.append(json.loads("\n".join(data_lines)))
    return events


def test_streams_multiple_deltas_and_persists(client: TestClient, db: Session) -> None:
    app.dependency_overrides[get_streaming_agent_runtime] = lambda: FakeStreamingRuntime()
    try:
        conversation_id = create_conversation(client)
        response = client.post(
            f"/api/conversations/{conversation_id}/messages:stream",
            json={"message": "PCR 是什么？"},
        )
        assert response.status_code == 200
        events = sse_events(response.text)
        assert [event["type"] for event in events] == [
            "run_started", "text_delta", "text_delta", "run_completed"
        ]
        assert "".join(str(event.get("text", "")) for event in events) == "PCR 是扩增技术。"

        messages = db.scalars(
            select(Message).where(Message.conversation_id == UUID(conversation_id)).order_by(Message.created_at)
        ).all()
        assert [(item.role, item.content, item.status) for item in messages] == [
            ("user", "PCR 是什么？", "completed"),
            ("assistant", "PCR 是扩增技术。", "completed"),
        ]
        run = db.scalar(select(AgentRun).where(AgentRun.conversation_id == UUID(conversation_id)))
        assert run is not None and run.status == "completed"
    finally:
        app.dependency_overrides.pop(get_streaming_agent_runtime, None)


def test_stream_failure_has_terminal_event(client: TestClient, db: Session) -> None:
    app.dependency_overrides[get_streaming_agent_runtime] = lambda: FailingStreamingRuntime()
    try:
        conversation_id = create_conversation(client)
        response = client.post(
            f"/api/conversations/{conversation_id}/messages:stream",
            json={"message": "PCR 是什么？"},
        )
        events = sse_events(response.text)
        assert events[-1]["type"] == "run_error"
        assert events[-1]["code"] == "AGENT_UNAVAILABLE"
        run = db.scalar(select(AgentRun).where(AgentRun.conversation_id == UUID(conversation_id)))
        assert run is not None and run.status == "failed"
    finally:
        app.dependency_overrides.pop(get_streaming_agent_runtime, None)


def test_cancel_is_idempotent_and_owner_safe(client: TestClient, db: Session) -> None:
    registry = RunRegistry()
    app.dependency_overrides[get_run_registry] = lambda: registry
    conversation_id = create_conversation(client)
    start = client.post(
        f"/api/conversations/{conversation_id}/messages:stream",
        json={"message": "PCR 是什么？"},
    )
    assert start.status_code == 200

    run = db.scalar(select(AgentRun).where(AgentRun.conversation_id == UUID(conversation_id)))
    assert run is not None
    run.status = "cancelled"
    db.commit()

    first = client.post(f"/api/runs/{run.id}/cancel")
    second = client.post(f"/api/runs/{run.id}/cancel")
    assert first.status_code == 202 and first.json()["accepted"] is False
    assert second.status_code == 202 and second.json()["status"] == "cancelled"

    app.dependency_overrides[get_current_user_id] = lambda: OTHER_OWNER_ID
    denied = client.post(f"/api/runs/{run.id}/cancel")
    assert denied.status_code == 404
    app.dependency_overrides[get_current_user_id] = lambda: OWNER_ID
    app.dependency_overrides.pop(get_run_registry, None)


def test_original_sync_endpoint_still_works(client: TestClient) -> None:
    app.dependency_overrides[get_agent_runtime] = lambda: FakeSyncRuntime()
    try:
        response = client.post("/api/chat", json={"message": "PCR"})
        assert response.status_code == 200
        assert response.json()["answer"] == "同步：PCR"
    finally:
        app.dependency_overrides.pop(get_agent_runtime, None)