from typing import Literal 
from pydantic import BaseModel,Field
from uuid import UUID

class ChatRequest(BaseModel):
    message:str=Field(min_length=1,max_length=4000)
    conversation_id:UUID|None=None
   
class Citation(BaseModel):
    document_id:UUID
    title:str
    page:int|None=None
    quote:str

class ChatResponse(BaseModel):
    conversation_id:UUID
    answer:str
    citations:list[Citation]=Field(default_factory=list)
    finish_reason:Literal["stop","length","error"]="stop"