# backend/core/config.py
from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict
import os


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    ENVIRONMENT: str = "development"
    PROJECT_NAME: str = "FastAPI MySQL Service"
    API_V1_STR: str = "/api/v1"

    # MySQL Configuration
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str = "app_user"
    DB_PASSWORD: str = "app_password"
    DB_NAME: str = "app_db"

    @computed_field
    @property
    def DATABASE_URL(self) -> str:
        return (
            f"mysql+asyncmy://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"
        )

    # Redis Configuration
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str | None = None
    REDIS_DB: int = 0
    REDIS_POOL_SIZE: int = 20
    REDIS_URL: str = (
        os.getenv("REDIS_URL") or "redis://localhost:6379/0"
    )  # Default value; will be overridden by computed property

    # @computed_field
    # @property
    # def REDIS_URL(self) -> str:
    #     auth = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
    #     return f"redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # Cookie & Session Security
    SESSION_COOKIE_NAME: str = "session_id"
    CSRF_COOKIE_NAME: str = "csrf_token"
    COOKIE_SECURE: bool = False  # Set to True in production (HTTPS)
    SESSION_TTL_SECONDS: int = 86400 * 7  # 7 days
    SESSION_COOKIE_SAMESITE: str = "lax"  # Options: 'strict', 'lax', 'none'

    # CORS (Must specify exact origins when allow_credentials=True)
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]


settings = Settings()
