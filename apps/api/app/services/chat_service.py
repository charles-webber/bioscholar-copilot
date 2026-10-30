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

class ConversationBusyError(Exception):
    pass

class RunNotFoundError(Exception):
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

            running=self._db.scalar(
                    select(
                        exists().where(
                            AgentRun.conversation_id == conversation_id,
                            AgentRun.status == "running",
                        )
                    )
                )
            if running:
                raise ConversationBusyError

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
                    content=user_text,
                    status="completed"
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


    def get_owned_run(self,run_id:UUID,owner_id:UUID)->AgentRun:
        run = self._db.scalar(
            select(AgentRun).join(Conversation,Conversation.id==AgentRun.conversation_id)
            .where(AgentRun.id==run_id,Conversation.owner_id==owner_id)
        )
        if run is None:
            raise RunNotFoundError
        return run


    def complete_run(
        self,
        run_id:UUID,
        conversation_id:UUID,
        answer:str,
        latency_ms:int
    )->bool:
        return self._finish_run(
            run_id,conversation_id,answer,"completed",None,latency_ms
        )

    def cancel_run(
        self,
        run_id:UUID,
        conversation_id:UUID,
        partial_answer:str,
        latency_ms:int
    )->bool:
        return self._finish_run(
            run_id,
            conversation_id,
            partial_answer,
            "cancelled",
            "CANCELLED_BY_USER",
            latency_ms,
        )

    def fail_run(
        self,
        run_id:UUID,
        code:str,
        latency_ms:int,
        partial_answer:str="",
    )->bool:
        run=self._db.get(AgentRun,run_id)
        if run is None:
            return False
        return self._finish_run(
            run_id,
            run.conversation_id,
            partial_answer,
            "failed",
            code,
            latency_ms,  
        )


    def _finish_run(
        self,
        run_id: UUID,
        conversation_id: UUID,
        answer: str,
        status: str,
        error_code: str | None,
        latency_ms: int,
    ) -> bool:
        try:
            conversation = self._db.scalar(
            select(Conversation)
            .where(Conversation.id == conversation_id)
            .with_for_update()
        )

            if conversation is None:
                self._db.rollback()
                return False

            run = self._db.scalar(
                select(AgentRun)
                .where(
                    AgentRun.id == run_id,
                    AgentRun.conversation_id == conversation_id,
                )
                .with_for_update()
            )

            if run is None or run.status != "running":
                self._db.rollback()
                return False

            if answer.strip():
                self._db.add(
                    Message(
                        conversation_id=conversation_id,
                        role="assistant",
                        content=answer,
                        status=status,
                    )
                )

            run.status = status
            run.error_code = error_code
            run.latency_ms = latency_ms
            run.finished_at = datetime.now(timezone.utc)

            conversation.updated_at = datetime.now(timezone.utc)

            self._db.commit()
            return True

        except Exception:
            self._db.rollback()
            raise

        
    