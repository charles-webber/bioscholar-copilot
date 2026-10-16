from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

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

async def require_owned_conversation(
    db:AsyncSession,conversation_id:UUID,owner_id:UUID
)-> Conversation:
    Conversation=await db.scalar(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.owner_id==owner_id
        )
    )
    if conversation is None:
        raise HTTPException(status_code=404,detail="会话不存在")
    return conversation

@router.get("",response_model=list[ConversationOut])
async def list_conversations(
    db:Annotated[AsyncSession,Depends(get_db)],
    owner_id:Annotated[UUID,Depends(get_current_user_id)],
):
    result=await db.scalars(
        select(Conversation)
        .where(Conversation.owner_id==owner_id)
        .order_by(Conversation.updated_at.desc())
    )
    return list(result)

@router.post("",response_model=ConversationOut,status_code=201)    
async def create_conversation(
    payload:ConversationCreate,
    ab:Annotated[AsyncSession,Depends(get_db)],
    owner_id:Annotated[UUID,Depends(get_current_user_id)]
):
    conversation=Conversation(owner_id=owner_id,title=payload.title)
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)
    return conversation

@router.patch("/{conversation_id}",response_model=ConversationOut)
async def rename_conversation(
    conversation_id:UUID,
    payload:ConversationUpdate,
    db:Annotated[AsyncSession,Depends(get_db)],
    owner_id:Annotated[UUID,Depends(get_current_user_id)]
):
    conversation=await require_owned_conversation(db,conversation_id,owner_id)
    conversation.title=payload.title
    await db.commit()
    await db.refresh(conversation)
    return conversation


@router.get("/{conversation_id}/messages",
response_model=list[MessageOut])
async def list_messages(
    conversation_id:UUID,
    db:Annotated[AsyncSession,Depends(get_db)],
    owner_id:Annotated[UUID,Depends(get_current_user_id)]
):
    await require_owned_conversation(db,conversation_id,owner_id)
    result=await db.scalars(
        select(Message).
        where(Message.conversation_id==conversation_id)
        .order_by(Message.created_at)
    )
    return list(result)


@router.delete("/{conversation_id}",status_code=204)
async def remove_conversation(
    conversation_id:UUID,
    db:Annotated[AsyncSession,Depends(get_db)],
    owner_id:Annotated[UUID,Depends(get_current_user_id)],
):
    result = await db.execute(
        delete(Conversation).where(
            Conversation.id==conversation_id,
            Conversation.owner_id==owner_id
        )
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404,detail="会话不存在")
        await db.commit()
        return Response(status_code=status.HTTP_204_NO_CONTENT)