from typing import Annotated
from uuid import UUID
from datetime import datetime,timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user_id, get_db
from app.db.models.conversation import Conversation
from app.db.models.message import Message
from app.db.models.run import AgentRun
from app.schemas.conversation import (
    ConversationCreate,
    ConversationOut,
    ConversationUpdate,
    MessageOut,
)

router = APIRouter(prefix="/conversations")

def require_owned_conversation(
    db:Session,
    conversation_id:UUID,
    owner_id:UUID,
    *,
    for_update:bool=False
)-> Conversation:
    statement = select(Conversation).where(
        Conversation.id==conversation_id,
        Conversation.owner_id==owner_id
    )
    if for_update:
        statement=statement.with_for_update()

    conversation=db.scalar(
        statement
    )
    if conversation is None:
        raise HTTPException(status_code=404,detail="会话不存在")
    return conversation




@router.get("",response_model=list[ConversationOut])
def list_conversations(
    db:Annotated[Session,Depends(get_db)],
    owner_id:Annotated[UUID,Depends(get_current_user_id)],
):
    result=db.scalars(
        select(Conversation)
        .where(Conversation.owner_id==owner_id)
        .order_by(Conversation.updated_at.desc(),Conversation.id.desc())
    )
    return list(result)

@router.post("",response_model=ConversationOut,status_code=status.HTTP_201_CREATED)    
def create_conversation(
    payload:ConversationCreate,
    db:Annotated[Session,Depends(get_db)],
    owner_id:Annotated[UUID,Depends(get_current_user_id)]
):
    conversation=Conversation(owner_id=owner_id,title=payload.title)
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation

@router.patch("/{conversation_id}",response_model=ConversationOut)
def rename_conversation(
    conversation_id:UUID,
    payload:ConversationUpdate,
    db:Annotated[Session,Depends(get_db)],
    owner_id:Annotated[UUID,Depends(get_current_user_id)]
):
    conversation=require_owned_conversation(db,conversation_id,owner_id)
    conversation.title=payload.title
    conversation.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(conversation)
    return conversation


@router.get("/{conversation_id}/messages",response_model=list[MessageOut])
def list_messages(
    conversation_id:UUID,
    db:Annotated[Session,Depends(get_db)],
    owner_id:Annotated[UUID,Depends(get_current_user_id)]
):
    require_owned_conversation(db,conversation_id,owner_id)
    result=db.scalars(
        select(Message).
        where(Message.conversation_id==conversation_id)
        .order_by(Message.created_at,Message.id)
    )
    return list(result)


@router.delete("/{conversation_id}",status_code=status.HTTP_204_NO_CONTENT)
def remove_conversation(
    conversation_id:UUID,
    db:Annotated[Session,Depends(get_db)],
    owner_id:Annotated[UUID,Depends(get_current_user_id)],
)->Response:
    conversation = require_owned_conversation(
        db,
        conversation_id,
        owner_id,
        for_update=True
    )
    running_run_id=db.scalar(
        select(AgentRun.id).
        where(
            AgentRun.conversation_id==conversation.id,
            AgentRun.status=="running",
        ).
        limit(1)
    )
    if running_run_id is not None:
        raise HTTPException(status_code=409, detail="会话仍在生成回答，请稍后再删除")


    db.delete(conversation)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)