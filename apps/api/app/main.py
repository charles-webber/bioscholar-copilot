from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import chat
from app.core.config import get_settings

settings= get_settings()
app=FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.web_origin],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"]
)

app.include_router(chat.router,prefix="/api",tags=["chat"])

@app.get("/health")
async def health()->dict[str,str]:
    return {"status":"ok"}

