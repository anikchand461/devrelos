from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # LLM
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"
    SMOLIFY_API_KEY: str = ""
    SMOLIFY_BASE_URL: str = "https://api.smolify.ai/v1"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://localhost/devrel"

    # Vector DB
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8001

    # Requestly
    REQUESTLY_API_KEY: str = ""
    REQUESTLY_WORKSPACE_ID: str = ""

    # App
    APP_ENV: str = "development"
    APP_SECRET_KEY: str = "dev-secret-change-in-prod"
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:8000"]

    # Telemetry
    ENABLE_TELEMETRY: bool = True

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
