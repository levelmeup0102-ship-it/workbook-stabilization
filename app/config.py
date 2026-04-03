from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    env: str = Field(default="dev")
    port: int = Field(default=8000)
    app_password: SecretStr
    anthropic_api_key: SecretStr
    supabase_url: str
    supabase_key: SecretStr


@lru_cache
def get_settings() -> Settings:
    return Settings()
