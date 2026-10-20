from typing import Annotated
from uuid import UUID
    
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user_id, get_db
from app.db.models.conversation import Conversation
from app.db.models.message import Message
from app.schemas.conversation import (
    ConversationCreate,
    ConversationOut,
    ConversationUpdate,
    MessageOut,
)

router = APIRouter(prefix="/conversations")

def require_owned_conversation(
    db:Session,conversation_id:UUID,owner_id:UUID
)-> Conversation:
    conversation=db.scalar(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.owner_id==owner_id
        )
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
        .order_by(Conversation.updated_at.desc())
    )
    return list(result)

@router.post("",response_model=ConversationOut,status_code=201)    
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
    db.commit()
    db.refresh(conversation)
    return conversation


@router.get("/{conversation_id}/messages",
response_model=list[MessageOut])
def list_messages(
    conversation_id:UUID,
    db:Annotated[Session,Depends(get_db)],
    owner_id:Annotated[UUID,Depends(get_current_user_id)]
):
    require_owned_conversation(db,conversation_id,owner_id)
    result=db.scalars(
        select(Message).
        where(Message.conversation_id==conversation_id)
        .order_by(Message.created_at)
    )
    return list(result)


@router.delete("/{conversation_id}",status_code=204)
def remove_conversation(
    conversation_id:UUID,
    db:Annotated[Session,Depends(get_db)],
    owner_id:Annotated[UUID,Depends(get_current_user_id)],
):
    result = db.execute(
        delete(Conversation).where(
            Conversation.id==conversation_id,
            Conversation.owner_id==owner_id
        )
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404,detail="会话不存在")
    
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)