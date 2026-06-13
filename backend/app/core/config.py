from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    database_url: str
    redis_url: str = "redis://localhost:6379/0"
    openai_api_key: str
    github_token: str = ""
    chroma_persist_dir: str = "./chroma_data"
    repos_dir: str = "./repos"
    secret_key: str = "dev_secret"

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
