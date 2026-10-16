from functools import lru_cache
from collections.abc import Iterator
from uuid import UUID
from sqlalchemy.orm import Session
from fastapi import Depends
from typing import Annotated

from app.agent.bioagent_adapter import BioAgentAdapter
from app.agent.demo_bioagent import DemoAgentRuntime
from app.agent.runtime import AgentRuntime
from app.core.config import get_settings
from app.db.session import SessionLocal
from app.services.chat_service import ChatService


DEV_USER_ID = UUID("00000000-0000-0000-0000-000000000001")

def get_db()->Iterator[Session]:
    with SessionLocal() as session:
        yield session

def get_current_user_id()->UUID:
    return DEV_USER_ID


def get_chat_service(
    db:Annotated[Session,Depends(get_db)]
) -> ChatService:
    return ChatService(db)

@lru_cache
def get_agent_runtime()->AgentRuntime:
    settings = get_settings()

    if settings.agent_backend=="demo":
        return DemoAgentRuntime()

    return BioAgentAdapter()