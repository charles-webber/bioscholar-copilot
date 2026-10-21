from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models.conversation import Conversation
from app.db.models.message import Message
from app.db.models.run import AgentRun
from app.services.chat_service import (
    DEFAULT_CONVERSATION_TITLE,
    ChatService,
    title_from_first_message,
)

OWNER_ID = UUID("00000000-0000-0000-0000-000000000001")


def make_conversation(
    db: Session,
    title: str = DEFAULT_CONVERSATION_TITLE,
) -> Conversation:
    conversation = Conversation(owner_id=OWNER_ID, title=title)
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


def user_message_count(db: Session, conversation: Conversation) -> int:
    return db.scalar(
        select(func.count())
        .select_from(Message)
        .where(
            Message.conversation_id == conversation.id,
            Message.role == "user",
        )
    ) or 0


def test_first_short_message_becomes_title(db: Session) -> None:
    conversation = make_conversation(db)

    ChatService(db).start_run(conversation.id, OWNER_ID, "PCR 是什么？")

    db.refresh(conversation)
    assert conversation.title == "PCR 是什么？"
    assert user_message_count(db, conversation) == 1


def test_title_normalizes_space_and_truncates_to_24_chars(db: Session) -> None:
    text = "  请解释   CRISPR Cas9 的工作原理、局限性和常见应用场景  "

    title = title_from_first_message(text)

    assert "  " not in title
    assert len(title) <= 24
    assert title.endswith("…")


def test_second_message_does_not_overwrite_generated_title(db: Session) -> None:
    conversation = make_conversation(db)
    service = ChatService(db)

    service.start_run(conversation.id, OWNER_ID, "第一条问题")
    service.start_run(conversation.id, OWNER_ID, "第二条完全不同的问题")

    db.refresh(conversation)
    assert conversation.title == "第一条问题"
    assert user_message_count(db, conversation) == 2


def test_custom_title_is_preserved(db: Session) -> None:
    conversation = make_conversation(db, title="我的 PCR 复习")

    ChatService(db).start_run(conversation.id, OWNER_ID, "第一条问题")

    db.refresh(conversation)
    assert conversation.title == "我的 PCR 复习"


def test_failed_agent_keeps_first_message_and_title(db: Session) -> None:
    conversation = make_conversation(db)
    service = ChatService(db)
    run_id = service.start_run(conversation.id, OWNER_ID, "解释 DNA 复制")

    service.fail_run(run_id, "AGENT_UNAVAILABLE", 12)

    db.refresh(conversation)
    run = db.get(AgentRun, run_id)
    assert conversation.title == "解释 DNA 复制"
    assert user_message_count(db, conversation) == 1
    assert run is not None
    assert run.status == "failed"
    assert run.error_code == "AGENT_UNAVAILABLE"