from typing import Literal 
from pydantic import BaseModel,Field

class ChatRequest(BaseModel):
    message:str=Field(min_length=1,max_length=8000)
    conversation_id:str|None=None

class Citation(BaseModel):
    document_id:str
    title:str
    page:int|None=None
    quote:str

class ChatResponse(BaseModel):
    conversation_id:str
    answer:str
    citations:list[Citation]=Field(default_factory=list)
    finish_reason:Literal["stop","length","error"]="stop"