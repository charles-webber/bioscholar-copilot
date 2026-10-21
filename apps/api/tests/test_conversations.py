from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user_id
from app.db.models.conversation import Conversation
from app.db.models.message import Message
from app.db.models.run import AgentRun
from app.main import app

OWNER_ID = UUID("00000000-0000-0000-0000-000000000001")
OTHER_OWNER_ID = UUID("00000000-0000-0000-0000-000000000002")


def seed_conversation(
    db: Session,
    *,
    owner_id: UUID = OWNER_ID,
    title: str = "测试会话",
    run_status: str = "completed",
) -> Conversation:
    conversation = Conversation(owner_id=owner_id, title=title)
    db.add(conversation)
    db.flush()
    db.add_all(
        [
            Message(
                conversation_id=conversation.id,
                role="user",
                content="DNA 是什么？",
            ),
            AgentRun(
                conversation_id=conversation.id,
                status=run_status,
            ),
        ]
    )
    db.commit()
    db.refresh(conversation)
    return conversation


def row_count(db: Session, model: type[object], conversation_id: UUID) -> int:
    return db.scalar(
        select(func.count())
        .select_from(model)
        .where(model.conversation_id == conversation_id)
    ) or 0


def test_owner_delete_returns_empty_204_and_cascades(
    client: TestClient,
    db: Session,
) -> None:
    target = seed_conversation(db, title="删除我")
    survivor = seed_conversation(db, title="保留我")

    response = client.delete(f"/api/conversations/{target.id}")

    assert response.status_code == 204
    assert response.content == b""
    db.expire_all()
    assert db.get(Conversation, target.id) is None
    assert row_count(db, Message, target.id) == 0
    assert row_count(db, AgentRun, target.id) == 0
    assert db.get(Conversation, survivor.id) is not None
    assert row_count(db, Message, survivor.id) == 1
    assert row_count(db, AgentRun, survivor.id) == 1


def test_other_owner_cannot_delete_conversation(
    client: TestClient,
    db: Session,
) -> None:
    target = seed_conversation(db, owner_id=OTHER_OWNER_ID)

    response = client.delete(f"/api/conversations/{target.id}")

    assert response.status_code == 404
    db.expire_all()
    assert db.get(Conversation, target.id) is not None


def test_deleting_same_conversation_twice_returns_404(
    client: TestClient,
    db: Session,
) -> None:
    target = seed_conversation(db)

    first = client.delete(f"/api/conversations/{target.id}")
    second = client.delete(f"/api/conversations/{target.id}")

    assert first.status_code == 204
    assert second.status_code == 404


def test_running_run_blocks_delete(client: TestClient, db: Session) -> None:
    target = seed_conversation(db, run_status="running")

    response = client.delete(f"/api/conversations/{target.id}")

    assert response.status_code == 409
    assert response.json()["detail"] == "会话仍在生成回答，请稍后再删除"
    db.expire_all()
    assert db.get(Conversation, target.id) is not None
    assert row_count(db, Message, target.id) == 1
    assert row_count(db, AgentRun, target.id) == 1


def test_owner_dependency_still_hides_foreign_rows(
    client: TestClient,
    db: Session,
) -> None:
    target = seed_conversation(db, owner_id=OWNER_ID)
    app.dependency_overrides[get_current_user_id] = lambda: OTHER_OWNER_ID
    try:
        response = client.delete(f"/api/conversations/{target.id}")
    finally:
        app.dependency_overrides[get_current_user_id] = lambda: OWNER_ID

    assert response.status_code == 404
    assert db.get(Conversation, target.id) is not None