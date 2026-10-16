from functools import lru_cache

from collections.abc import AsyncIterator
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession


from app.agent.bioagent_adapter import BioAgentAdapter
from app.agent.demo_bioagent import DemoAgentRuntime
from app.agent.runtime import AgentRuntime
from app.core.config import get_settings
from app.db.session import AsyncSessionLocal
from app.services.chat_service import ChatService


DEV_USER_ID = UUID("00000000-0000-0000-0000-000000000001")

async def get_db()->AsyncIterator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        yield session

def get_current_user_id()->UUID:
    return DEV_USER_ID


def get_chat_service() -> ChatService:
    return ChatService()

@lru_cache
def get_agent_runtime()->AgentRuntime:
    settings = get_settings()

    if settings.agent_backend=="demo":
        return DemoAgentRuntime()

    return BioAgentAdapter()