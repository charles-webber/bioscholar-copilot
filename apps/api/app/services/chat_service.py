from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import exists,select

from app.db.models.conversation import Conversation
from app.db.models.message import Message
from app.agent.runtime import AgentAnswer
from app.db.models.run import AgentRun
from app.db.session import Session

DEFAULT_CONVERSATION_TITLE="新对话"
TITLE_MAX_CHARS=24

#!new-add
def title_from_first_message(
    text:str,
    max_chars:int=TITLE_MAX_CHARS
)->str:
    normalized = " ".join(text.split())
    if len(normalized)<=max_chars:
        return normalized or DEFAULT_CONVERSATION_TITLE
    prefix= normalized[:max_chars-1].rstrip("，。！？,.!?;；:： ")
    return f"{prefix}…"




class ConversationNotFoundError(Exception):
    pass

class ChatService:
    def __init__(self,db:Session)->None:
        self._db = db

    def start_run(
        self,
        conversation_id:UUID,
        owner_id:UUID,
        user_text:str
    )->UUID:
        try:
            conversation=self._db.scalar(
                select(Conversation).where(
                    Conversation.id == conversation_id,
                    Conversation.owner_id == owner_id,
                ).with_for_update()
            )
            if conversation is None:
                raise ConversationNotFoundError

            has_user_message = bool(
                self._db.scalar(
                    select(
                        exists().where(
                            Message.conversation_id==conversation_id,
                            Message.role=="user"
                        )
                    )
                )
            )
            if(
                conversation.title==DEFAULT_CONVERSATION_TITLE
                and not has_user_message
            ):
                conversation.title=title_from_first_message(user_text)
                conversation.updated_at=datetime.now(timezone.utc)
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

        except Exception:
            self._db_.rollback()
            raise

    def complete_run(
        self,
        run_id:UUID,
        conversation_id:UUID,
        answer:str,
        latency_ms:int
    )->None:
        try:
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
            run.error_code=None
            run.latency_ms=latency_ms
            run.finished_at=datetime.now(timezone.utc)
            conversation.updated_at = datetime.now(timezone.utc)
            self._db.commit()

        except Exception:
            self._db.rollback()
            raise
        
    
    def fail_run(
        self,run_id:UUID,
        code:str,
        latency_ms:int
        )->None:
        try:
            run = self._db.get(AgentRun,run_id)
            if run is None:
                return
            run.status="failed"
            run.error_code=code
            run.latency_ms=latency_ms
            run.finished_at=datetime.now(timezone.utc)
            self._db.commit()

        except Exception:
            self._db.rollback()
            raise