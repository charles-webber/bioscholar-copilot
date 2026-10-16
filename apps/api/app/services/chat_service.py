from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select

from app.db.models.conversation import Conversation
from app.db.models.message import Message
from app.db.models.run import AgentRun
from app.db.session import SessionLocal

class ConversationNotFoundError(Exception):
    pass

class ChatService:
    async def start_run(
        self,conversation_id:UUID,owner_id:UUID,user_text:str
    )->UUID:
        async with AsyncSessionLocal() as db,db.begin():
            conversation=await db.scalar(
                select(Conversation).where(
                    Conversation.id == conversation_id,
                    Conversation.owner_id == owner_id,
                )
            )
            if conversation is None:
                raise ConversationNotFoundError
            
            db.add(
                Message(
                    conversation_id=conversation_id,
                    role="user",
                    content=user_text
                )
            )
            run = AgentRun(conversation_id=conversation_id,status="running")
            db.add(run)
            await db.flush()
            return run.id

    async def complete_run(
        self,run_id:UUID,conversation_id:UUID,answer:str,latency_ms:int
    )->None:
        async with AsyncSessionLocal() as db,db.begin():
            run = await db.get(AgentRun,run_id)
            conversation=await db.get(Conversation,conversation_id)
            if run is None or conversation is None:
                raise RuntimeError("run or conversation disappeared")
            db.add(
                Message(
                    conversation_id=conversation_id,
                    role="assistant",
                    content=answer,
                )
            )
            run.status="completed"
            run.latency_ms=latency_ms
            run.finished_at=datetime.now(timezone.utc)
            conversation.updated_at = datetime.now(timezone.utc)
    
    async def fail_run(self,run_id:UUID,code:str,latency_ms:int)->None:
        async with AsyncSessionLocal() as db,db.begin():
            run = await db.get(AgentRun,run_id)
            if run is None:
                return
            run.status="failed"
            run.error_code=code
            run.latency_ms=latency_ms
            run.finished_at=datetime.now(timezone.utc)
