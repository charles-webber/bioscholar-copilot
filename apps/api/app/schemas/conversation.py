from datetime import datetime
from  uuid import UUID

from pydantic import BaseModel,ConfigDict,Field


class ConversationCreate(BaseModel):
    title:str=Field(default="新对话",min_length=1,max_length=120)

class ConversationUpdate(BaseModel):
    title:str = Field(min_length=1,max_length=120)

class ConversationOut(BaseModel):
    model_config=ConfigDict(from_attributes=True)

    id:UUID
    title:str
    created_at:datetime
    updated_at:datetime

class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:UUID
    role:str
    content:str
    status:str
    created_at:datetime