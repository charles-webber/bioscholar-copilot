from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.api.routes import chat,conversations,streaming_chat

settings= get_settings()
app=FastAPI(title=settings.app_name,version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.web_origin],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-Request-ID"]
)

app.include_router(chat.router,prefix="/api",tags=["chat"])
app.include_router(conversations.router,prefix="/api",tags=["conversations"])
app.include_router(streaming_chat.router,prefix="/api",tags=["streaming_chat"])



@app.get("/health")
def health()->dict[str,str]:
    return {"status":"ok"}

