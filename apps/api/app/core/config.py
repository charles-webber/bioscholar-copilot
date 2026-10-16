from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "BioScholar API"
    environment: str = "development"
    web_origin: str = "http://localhost:5173"
    database_url: str=(
        "postgresql+psycopg://bioscholar:local_only_change_me"
        "@localhost:5432/bioscholar"
    )

    agent_backend:Literal["demo","bioagent"]="demo"
    biomedical_llm_api_style:Literal["chat_completions","responses"]=(
        "chat_completions"
    )
    biomedical_llm_api_key: str = Field(default="",repr=False)
    biomedical_llm_base_url: str = ""
    biomedical_llm_model: str = ""
    upload_dir:str= "runtime/uploads"
    max_upload_bytes:int = 5*1024*1024
    session_cookie_secure:bool = False


    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )



@lru_cache
def get_settings() -> Settings:
    return Settings()