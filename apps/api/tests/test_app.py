from fastapi.testclient import TestClient

from app.agent.runtime import AgentRuntimeError
from app.api.dependencies import get_agent_runtime
from app.main import app


class FakeRuntime:
    async def invoke(self, message: str) -> str:
        return f"fake:{message}"


class FailingRuntime:
    async def invoke(self, message: str) -> str:
        raise RuntimeError("provider failed")


class RejectedRuntime:
    async def invoke(self, message: str) -> str:
        raise AgentRuntimeError(
            code="BIOMEDICAL_TOPIC_NOT_FOUND",
            message="没有识别出知识库中的主题。",
            next_action="请换一个知识库内的主题。",
        )


def test_health() -> None:
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_chat() -> None:
    app.dependency_overrides[get_agent_runtime] = lambda: FakeRuntime()
    try:
        with TestClient(app) as client:
            response = client.post("/api/chat", json={"message": "DNA 是什么？"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "fake:DNA 是什么？"
    assert body["conversation_id"]


def test_chat_rejects_empty_message() -> None:
    with TestClient(app) as client:
        response = client.post("/api/chat", json={"message": ""})

    assert response.status_code == 422


def test_chat_hides_internal_agent_error() -> None:
    app.dependency_overrides[get_agent_runtime] = lambda: FailingRuntime()
    try:
        with TestClient(app) as client:
            response = client.post("/api/chat", json={"message": "test"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 502
    assert response.json()["detail"] == "BioAgent 暂时不可用，请稍后重试"


def test_chat_preserves_safe_biomedical_rejection() -> None:
    app.dependency_overrides[get_agent_runtime] = lambda: RejectedRuntime()
    try:
        with TestClient(app) as client:
            response = client.post("/api/chat", json={"message": "量子纠缠是什么？"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    assert "没有识别出" in response.json()["detail"]