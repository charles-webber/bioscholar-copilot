from functools import lru_cache
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "BioScholar API"
    environment: str = "development"
    web_origin: str = "http://localhost:3000"
    agent_backend:Literal["demo","bioagent"]="demo"
    biomedical_llm_api_style:Literal["chat_completions","responses"]=(
        "chat_completions"
    )
    biomedical_llm_api_key: str = ""
    biomedical_llm_base_url: str = ""
    biomedical_llm_model: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()