from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select

from app.db.models.conversation import Conversation
from app.db.models.message import Message
from app.db.models.run import AgentRun
from app.db.session import Session

class ConversationNotFoundError(Exception):
    pass

class ChatService:
    def __init__(self,db:Session)->None:
        self._db = db

    def start_run(
        self,conversation_id:UUID,owner_id:UUID,user_text:str
    )->UUID:
            conversation=self._db.scalar(
                select(Conversation).where(
                    Conversation.id == conversation_id,
                    Conversation.owner_id == owner_id,
                )
            )
            if conversation is None:
                raise ConversationNotFoundError
            self._db.add(
                Message(
                    conversation_id=conversation_id,
                    role="user",
                    content=user_text
                )
            )

            run = AgentRun(conversation_id=conversation_id,status="running")
            self._db.add(run)
            self._db.commit()
            self._db.refresh(run)
            return run.id


    def complete_run(
        self,run_id:UUID,conversation_id:UUID,answer:str,latency_ms:int
    )->None:
            run = self._db.get(AgentRun,run_id)
            conversation=self._db.get(Conversation,conversation_id)
            if run is None or conversation is None or run.conversation_id != conversation_id:
                raise RuntimeError("run or conversation disappeared")
            self._db.add(
                Message(
                    conversation_id=conversation_id,
                    role="assistant",
                    content=answer.text,
                )
            )
            run.status="completed"
            run.latency_ms=latency_ms
            run.finished_at=datetime.now(timezone.utc)
            conversation.updated_at = datetime.now(timezone.utc)
            self._db.commit()
    
    def fail_run(self,run_id:UUID,code:str,latency_ms:int)->None:
            run = self._db.get(AgentRun,run_id)
            if run is None:
                return
            run.status="failed"
            run.error_code=code
            run.latency_ms=latency_ms
            run.finished_at=datetime.now(timezone.utc)
            self._db.commit()